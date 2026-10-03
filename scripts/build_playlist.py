#!/usr/bin/env python3
"""Build USA internet TV playlists from the community-maintained iptv-org index.

Outputs:
  playlist.m3u             every US channel, deduplicated and sorted
  categories/<name>.m3u    one playlist per category (News, Sports, ...)
  channels.json            machine-readable channel list
  epg.xml.gz               XMLTV program guide, referenced from the playlist header

Stdlib only so it runs anywhere (locally or in GitHub Actions).
"""
import gzip
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = "https://iptv-org.github.io/iptv/countries/us.m3u"
# Where players fetch the guide from; the playlist header points here.
EPG = "https://raw.githubusercontent.com/defuuls/tvtime/main/epg.xml.gz"
# Pluto TV guide whose channel ids match the ids in jmp2.uk/plu-<id> stream URLs.
PLUTO_EPG = os.environ.get("PLUTO_EPG", "https://i.mjh.nz/PlutoTV/us.xml.gz")
PLUTO_URL_RE = re.compile(r"jmp2\.uk/plu-([0-9a-f]{24})")
ROOT = Path(__file__).resolve().parent.parent
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def fetch_bytes(src):
    if not src.startswith("http"):
        return Path(src).read_bytes()
    req = urllib.request.Request(src, headers={"User-Agent": "TVTime-playlist-builder"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch(url):
    return fetch_bytes(url).decode("utf-8", errors="replace")


def build_epg(channels):
    """Write epg.xml.gz with guide data for channels we can match by id.

    Source guide ids are rewritten to each channel's tvg-id so players match them.
    Returns the number of channels with guide data.
    """
    id_map = {}
    for ch in channels:
        m = PLUTO_URL_RE.search(ch["url"])
        tvg_id = ch["attrs"].get("tvg-id")
        if m and tvg_id:
            id_map.setdefault(m.group(1), tvg_id)

    try:
        raw = fetch_bytes(PLUTO_EPG)
    except OSError as e:
        print(f"warning: could not fetch Pluto guide ({e}); keeping existing epg.xml.gz")
        return None
    root = ET.fromstring(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)

    out = ET.Element("tv", {"generator-info-name": "TVTime"})
    matched = set()
    for el in root.findall("channel"):
        new_id = id_map.get(el.get("id"))
        if new_id and new_id not in matched:
            matched.add(new_id)
            el.set("id", new_id)
            out.append(el)
    for el in root.findall("programme"):
        new_id = id_map.get(el.get("channel"))
        if new_id:
            el.set("channel", new_id)
            out.append(el)

    data = ET.tostring(out, encoding="utf-8", xml_declaration=True)
    with gzip.GzipFile(ROOT / "epg.xml.gz", "wb", mtime=0) as f:
        f.write(data)
    return len(matched)


def parse(text):
    channels, info, extra = [], None, []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            meta, _, name = line.partition(",")
            info = {"name": name.strip(), "attrs": dict(ATTR_RE.findall(meta))}
            extra = []
        elif line.startswith("#EXTVLCOPT") or line.startswith("#KODIPROP"):
            extra.append(line)
        elif line and not line.startswith("#") and info:
            info["url"], info["extra"] = line, extra
            channels.append(info)
            info = None
    return channels


def dedupe(channels):
    seen, out = set(), []
    for ch in channels:
        if ch["url"] not in seen:
            seen.add(ch["url"])
            out.append(ch)
    return sorted(out, key=lambda c: c["name"].lower())


def groups(ch):
    g = ch["attrs"].get("group-title") or "Undefined"
    return [p.strip() for p in g.split(";") if p.strip()]


def render(channels):
    lines = [f'#EXTM3U url-tvg="{EPG}" x-tvg-url="{EPG}"']
    for ch in channels:
        attrs = " ".join(f'{k}="{v}"' for k, v in ch["attrs"].items())
        lines.append(f"#EXTINF:-1 {attrs},{ch['name']}")
        lines.extend(ch["extra"])
        lines.append(ch["url"])
    return "\n".join(lines) + "\n"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "undefined"


def main():
    channels = dedupe(parse(fetch(SOURCE)))
    if len(channels) < 100:
        sys.exit(f"Only {len(channels)} channels parsed; refusing to overwrite playlists.")

    (ROOT / "playlist.m3u").write_text(render(channels))

    cat_dir = ROOT / "categories"
    cat_dir.mkdir(exist_ok=True)
    for old in cat_dir.glob("*.m3u"):
        old.unlink()
    by_cat = {}
    for ch in channels:
        for g in groups(ch):
            by_cat.setdefault(g, []).append(ch)
    for name, chans in by_cat.items():
        (cat_dir / f"{slug(name)}.m3u").write_text(render(chans))

    (ROOT / "channels.json").write_text(json.dumps([
        {"name": c["name"], "id": c["attrs"].get("tvg-id", ""), "logo": c["attrs"].get("tvg-logo", ""),
         "categories": groups(c), "url": c["url"]}
        for c in channels
    ], indent=1) + "\n")

    guided = build_epg(channels)
    print(f"{len(channels)} channels across {len(by_cat)} categories; guide data for {guided} channels")


if __name__ == "__main__":
    main()
