import base64
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch


spec = importlib.util.spec_from_file_location(
    "build_playlist", Path(__file__).resolve().parents[1] / "scripts/build_playlist.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CDNLiveTests(unittest.TestCase):
    def test_country_metadata_and_conservative_fallback(self):
        cases = [
            ({"code": " US ", "name": "Example"}, "us"),
            ({"code": "ca", "name": "Example US"}, "ca"),
            ({"code": "", "name": "BET UHD US"}, "us"),
            ({"name": "Example US  "}, "us"),
            ({"code": None, "name": "Example US"}, "us"),
            ({"code": " ", "name": "Example US"}, "us"),
            ({"name": "Example UK"}, ""),
            ({"name": "US News"}, ""),
            ({"name": "Example RUS"}, ""),
            ({"name": "Example us"}, ""),
            ({"name": "MLB | Toronto Blue Jays"}, ""),
            ({}, ""),
        ]
        for channel, expected in cases:
            with self.subTest(channel=channel):
                self.assertEqual(builder.cdnlive_country(channel), expected)

    def collect(self, channels, countries="us", online=True):
        output = io.StringIO()
        with patch.multiple(builder, CDNLIVE_ENABLED=True,
                            CDNLIVE_COUNTRIES=countries, CDNLIVE_ONLINE=online), \
             patch.object(builder, "fetch", return_value=json.dumps({"channels": channels})), \
             patch.object(builder, "resolve_cdnlive", side_effect=lambda url: {
                 "known": "https://example.test/known.m3u8",
                 "inferred": "https://example.test/inferred.m3u8",
                 "offline": "https://example.test/offline.m3u8",
                 "foreign": "https://example.test/foreign.m3u8",
                 "unknown": "https://example.test/unknown.m3u8",
             }.get(url)) as resolver, redirect_stdout(output):
            result = builder.fetch_cdnlive()
        return result, resolver, output.getvalue()

    def test_filter_order_resolution_and_diagnostics(self):
        channels = [
            {"name": "Known", "code": "us", "status": "online", "url": "known"},
            {"name": "BET UHD US", "code": "", "status": "online", "url": "inferred"},
            {"name": "Offline US", "code": "", "status": "offline", "url": "offline"},
            {"name": "Foreign US", "code": "ca", "status": "online", "url": "foreign"},
            {"name": "Unknown", "code": "", "status": "online", "url": "unknown"},
            {"name": "Broken US", "code": "", "status": "online", "url": "broken"},
            {"name": "No URL US", "code": "", "status": "online"},
        ]
        result, resolver, output = self.collect(channels)
        self.assertEqual([c["name"] for c in result], ["Known", "BET UHD US"])
        self.assertEqual([c.args[0] for c in resolver.call_args_list],
                         ["known", "inferred", "broken"])
        self.assertEqual(result[1]["attrs"]["tvg-country"], "US")
        self.assertIn("total=7, missing_code=5, inferred_us=3, invalid=1, "
                      "country_skipped=2, offline_skipped=1, unresolved=1", output)
        self.assertIn("warning:", output)
        self.assertIn("2 channels from CDNLiveTV", output)

    def test_all_and_offline_settings_still_work(self):
        channels = [
            {"name": "Unknown", "code": "", "status": "online", "url": "unknown"},
            {"name": "Offline US", "status": "offline", "url": "offline"},
            {"name": "Foreign US", "code": "ca", "status": "online", "url": "foreign"},
        ]
        self.assertEqual(len(self.collect(channels, "all", False)[0]), 3)
        self.assertEqual(len(self.collect(channels, "us,ca", False)[0]), 2)

    def test_disabled_and_api_failure_skip_safely(self):
        with patch.object(builder, "CDNLIVE_ENABLED", False), \
             patch.object(builder, "fetch") as fetch:
            self.assertEqual(builder.fetch_cdnlive(), [])
            fetch.assert_not_called()
        for failure in (OSError("unavailable"), ValueError("invalid JSON")):
            with self.subTest(failure=failure), \
                 patch.object(builder, "CDNLIVE_ENABLED", True), \
                 patch.object(builder, "fetch", side_effect=failure), \
                 patch.object(builder, "resolve_cdnlive") as resolver, \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(builder.fetch_cdnlive(), [])
                resolver.assert_not_called()

    def test_resolver_decodes_without_executing_javascript(self):
        url = "https://example.test/live.m3u8?token=test"
        encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            f"var part='{encoded}';var stream=decode(part);"
        ).encode()
        with patch.object(builder.urllib.request, "urlopen", return_value=response):
            self.assertEqual(builder.resolve_cdnlive("https://example.test/player"), url)
        response.__enter__.return_value.read.return_value = b"<html>Unavailable</html>"
        with patch.object(builder.urllib.request, "urlopen", return_value=response):
            self.assertIsNone(builder.resolve_cdnlive("https://example.test/player"))
        with patch.object(builder.urllib.request, "urlopen", side_effect=OSError("timeout")):
            self.assertIsNone(builder.resolve_cdnlive("https://example.test/player"))


if __name__ == "__main__":
    unittest.main()
