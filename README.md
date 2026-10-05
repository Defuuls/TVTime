# TVTime

Time for TV — an M3U playlist of free, publicly available internet TV channels in the USA.

## Use it

Add this URL to any IPTV player (VLC, Kodi, TiviMate, IPTV Smarters, Jellyfin, Plex via xTeVe, ...):

```
https://raw.githubusercontent.com/defuuls/tvtime/main/playlist.m3u
```

The program guide (EPG) is linked from the playlist header (`url-tvg`), so most players pick it up
automatically. If yours needs it entered separately:

```
https://raw.githubusercontent.com/defuuls/tvtime/main/epg.xml.gz
```

Guide data currently covers the Pluto TV channels (~185); other channels play without a guide.

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
Plex, local news stations, public broadcasters, etc.), deduplicates and sorts it, writes the
playlists, and builds `epg.xml.gz` from the Pluto TV guide published by [i.mjh.nz](https://i.mjh.nz). A GitHub Action (`.github/workflows/update-playlist.yml`) re-runs it daily and commits
any changes.

Run it locally with `python3 scripts/build_playlist.py` (Python 3, no dependencies).

## Disclaimer

This repo hosts no video — only links to streams their owners make freely available. Some links
may be geo-blocked or offline at any given time. Report broken or unwanted links upstream to iptv-org.

## CDNLiveTV channels

The playlist also pulls channels from the CDNLiveTV API
(`https://api.cdnlivetv.is/api/v1/channels/?user=cdnlivetv&plan=free`). They show up in the `CDNLive`
group and in `categories/cdnlive.m3u`. You can change this with environment variables, set in
`.github/workflows/update-playlist.yml` or when running `scripts/build_playlist.py` yourself:

| Variable | Default | Meaning |
|---|---|---|
| `CDNLIVE_ENABLED` | `1` | Set to `0` to leave CDNLiveTV out |
| `CDNLIVE_COUNTRIES` | `us` | Comma-separated country codes (`us,gb,ca`), or `all` |
| `CDNLIVE_ONLINE` | `1` | Set to `0` to also include channels the API reports offline |
| `CDNLIVE_GROUP` | `CDNLive` | Group name these channels get |
| `CDNLIVE_API` | the URL above | API endpoint |

The build pulls the direct HLS (`.m3u8`) link out of each CDNLiveTV player page. Those links expire
about 4 hours after they're made, so the workflow rebuilds the playlist every 2 hours. If a CDNLive
channel stops playing, reload the playlist in your player (or set it to refresh every hour or two).

## Dead channels

Each build tests every stream and drops the ones that are certainly gone: a 404/410 response
(including on the stream's first quality variant), a host that no longer exists, or a refused
connection. Timeouts, 403s and server errors are kept, because they're often temporary or only affect
GitHub's servers. If more than half the channels look dead at once, nothing is dropped, since that
points to a network problem. Set `CHECK_STREAMS=0` to turn the check off.
