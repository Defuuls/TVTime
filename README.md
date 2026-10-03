# TVTime

Time for TV — an M3U playlist of free, publicly available internet TV channels in the USA.

## Use it

Add this URL to any IPTV player (VLC, Kodi, TiviMate, IPTV Smarters, Jellyfin, Plex via xTeVe, ...):

```
https://raw.githubusercontent.com/defuuls/tvtime/main/playlist.m3u
```

The program guide (EPG) URL is embedded in the playlist header; if your player needs it separately:

```
https://iptv-org.github.io/epg/guides/us.xml
```

### Per-category playlists

Each category has its own playlist under `categories/`, e.g.

```
https://raw.githubusercontent.com/defuuls/tvtime/main/categories/news.m3u
https://raw.githubusercontent.com/defuuls/tvtime/main/categories/sports.m3u
https://raw.githubusercontent.com/defuuls/tvtime/main/categories/movies.m3u
```

`channels.json` contains the same list in machine-readable form.

## How it works

`scripts/build_playlist.py` pulls the US channel index from the community-maintained
[iptv-org](https://github.com/iptv-org/iptv) project (FAST services like Pluto TV, Samsung TV Plus,
Plex, local news stations, public broadcasters, etc.), deduplicates and sorts it, and writes the
playlists. A GitHub Action (`.github/workflows/update-playlist.yml`) re-runs it daily and commits
any changes.

Run it locally with `python3 scripts/build_playlist.py` (Python 3, no dependencies).

## Disclaimer

This repo hosts no video — only links to streams their owners make freely available. Some links
may be geo-blocked or offline at any given time. Report broken or unwanted links upstream to iptv-org.
