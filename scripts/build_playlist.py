#!/usr/bin/env python3
"""Build USA internet TV playlists from the community-maintained iptv-org index.

Outputs:
  playlist.m3u             every US channel, deduplicated and sorted
  categories/<name>.m3u    one playlist per category (News, Sports, ...)
  channels.json            machine-readable channel list

Stdlib only so it runs anywhere (locally or in GitHub Actions).
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE = "https://iptv-org.github.io/iptv/countries/us.m3u"
EPG = "https://iptv-org.github.io/epg/guides/us.xml"
ROOT = Path(__file__).resolve().parent.parent
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "TVTime-playlist-builder"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


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

    print(f"{len(channels)} channels across {len(by_cat)} categories")


if __name__ == "__main__":
    main()
