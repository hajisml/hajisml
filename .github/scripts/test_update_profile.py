"""Offline privacy, rendering, API, and branch-safety regression tests."""

from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from datetime import date
from html import unescape
from html.parser import HTMLParser
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

import update_profile as profile


TODAY = date(2026, 11, 2)
OVERVIEW = [("Public repositories", 4), ("Stars received", 3), ("Forks received", 2), ("Followers", 1)]


def contrast(foreground, background):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        channels = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return sum(weight * value for weight, value in zip((0.2126, 0.7152, 0.0722), channels))
    light, dark = sorted([luminance(foreground), luminance(background)], reverse=True)
    return (light + 0.05) / (dark + 0.05)


class LanguagePrivacyTests(unittest.TestCase):
    def test_only_language_names_and_numeric_time_are_published(self):
        payload = {"data": {
            "languages": [
                {"name": "Go", "total_seconds": 5400, "text": "SECRET_TEXT", "percent": "SECRET_PERCENT"},
                {"name": "Java", "total_seconds": 1800},
            ],
            "projects": [{"name": "SECRET_PROJECT"}],
            "editors": [{"name": "SECRET_EDITOR"}],
            "machines": [{"name": "SECRET_MACHINE"}],
            "operating_systems": [{"name": "SECRET_OS"}],
            "timezone": "SECRET_TIMEZONE",
            "human_readable_total": "SECRET_TOTAL",
            "ai_model_breakdown": [{"name": "SECRET_MODEL"}],
        }}
        output = profile.render_wakatime(payload, TODAY)
        self.assertNotIn("SECRET", output)
        self.assertIn("Go", output)
        self.assertIn("1 hr 30 mins", output)
        self.assertIn("75.00 %", output)
        self.assertIn("25.00 %", output)
        self.assertNotIn("Projects:", output)

    def test_empty_activity_is_not_a_service_failure(self):
        output = profile.render_wakatime({"data": {"languages": []}}, TODAY)
        self.assertIn("No language activity tracked", output)

    def test_zero_activity_does_not_divide_by_zero(self):
        output = profile.render_wakatime({"data": {"languages": [{"name": "Go", "total_seconds": 0}]}}, TODAY)
        self.assertIn("No language activity tracked", output)

    def test_missing_or_stale_data_does_not_look_like_zero_activity(self):
        for payload in [{}, {"data": {}}, {"data": {"languages": [] , "is_up_to_date": False}}, {"data": {"languages": None}}]:
            with self.subTest(payload=payload), self.assertRaises(profile.StatsError):
                profile.render_wakatime(payload, TODAY)

    def test_untrusted_language_names_cannot_inject_markdown_or_paths(self):
        for name in ["Go\nSECRET_PROJECT", "```", "<script>", "Go|SECRET", "/home/user/secret\n", None]:
            with self.subTest(name=name), self.assertRaises(profile.StatsError):
                profile.render_wakatime({"data": {"languages": [{"name": name, "total_seconds": 60}]}}, TODAY)

    def test_invalid_durations_are_rejected(self):
        for value in [-1, float("nan"), float("inf"), "SECRET", True, None]:
            with self.subTest(value=value), self.assertRaises(profile.StatsError):
                profile.render_wakatime({"data": {"languages": [{"name": "Go", "total_seconds": value}]}}, TODAY)

    def test_language_order_and_duplicate_totals_are_deterministic(self):
        output = profile.render_wakatime({"data": {"languages": [
            {"name": "Python", "total_seconds": 60},
            {"name": "Go", "total_seconds": 60},
            {"name": "Go", "total_seconds": 60},
        ]}}, TODAY)
        self.assertLess(output.index("Go"), output.index("Python"))
        self.assertIn("66.67 %", output)


class MarkerTests(unittest.TestCase):
    def test_only_marked_section_changes(self):
        original = f"intro\n{profile.WAKA_START}\nold\n{profile.WAKA_END}\nfooter\n"
        expected = f"intro\n{profile.WAKA_START}\nnew\n{profile.WAKA_END}\nfooter\n"
        self.assertEqual(profile.replace_waka(original, "new"), expected)

    def test_invalid_markers_fail_closed(self):
        for text in ["no markers", profile.WAKA_START, profile.WAKA_END + profile.WAKA_START,
                     profile.WAKA_START * 2 + profile.WAKA_END]:
            with self.subTest(text=text), self.assertRaises(profile.StatsError):
                profile.replace_waka(text, "new")

    def test_only_excuse_section_changes(self):
        original = f"intro\n{profile.EXCUSE_START}\nold\n{profile.EXCUSE_END}\nsignature\n"
        expected = f"intro\n{profile.EXCUSE_START}\nnew\n{profile.EXCUSE_END}\nsignature\n"
        self.assertEqual(profile.replace_excuse(original, "new"), expected)

    def test_invalid_excuse_markers_fail_closed(self):
        for text in ["no markers", profile.EXCUSE_START, profile.EXCUSE_END + profile.EXCUSE_START,
                     profile.EXCUSE_START * 2 + profile.EXCUSE_END]:
            with self.subTest(text=text), self.assertRaises(profile.StatsError):
                profile.replace_excuse(text, "new")


def repo(name, *, private=False, fork=False, owner="hajisml", stars=0, forks=0):
    return {"name": name, "private": private, "fork": fork, "owner": {"login": owner},
            "stargazers_count": stars, "forks_count": forks}


class GitHubTests(unittest.TestCase):
    @patch.object(profile, "get_json")
    def test_private_external_and_fork_code_is_excluded(self, get_json):
        get_json.side_effect = [
            {"login": "hajisml", "followers": 7},
            [repo("original", stars=3, forks=2), repo("fork", fork=True, stars=99),
             repo("SECRET_PRIVATE", private=True), repo("external", owner="other")],
            {"Go": 200, "Python": 100},
        ]
        overview, languages = profile.github_stats("github-test-token")
        self.assertEqual(dict(overview), {"Public repositories": 2, "Stars received": 3, "Forks received": 2, "Followers": 7})
        self.assertEqual(languages, {"Go": 200, "Python": 100})
        calls = [call.args[0] for call in get_json.call_args_list]
        self.assertEqual(len(calls), 3)
        self.assertNotIn("SECRET_PRIVATE", " ".join(calls))
        self.assertTrue(all(url.startswith("https://api.github.com/") for url in calls))
        self.assertNotIn("/user/repos", " ".join(calls))

    @patch.object(profile, "get_json")
    def test_repositories_are_paginated(self, get_json):
        get_json.side_effect = [
            {"login": "hajisml", "followers": 1},
            [repo(f"fork-{index}", fork=True) for index in range(100)],
            [repo("last", fork=True)],
        ]
        overview, languages = profile.github_stats()
        self.assertEqual(dict(overview)["Public repositories"], 101)
        self.assertEqual(languages, {})
        self.assertIn("page=2", get_json.call_args_list[-1].args[0])

    @patch.object(profile, "get_json")
    def test_bad_api_shapes_are_rejected(self, get_json):
        for result in [[], {"login": "other"}, {"login": None}]:
            get_json.return_value = result
            with self.subTest(result=result), self.assertRaises(profile.StatsError):
                profile.github_stats()


class RenderingTests(unittest.TestCase):
    def test_both_themes_are_valid_accessible_svg(self):
        for theme in profile.THEMES:
            for content in [profile.render_overview(OVERVIEW, theme, TODAY),
                            profile.render_languages({"Go": 3, "C++": 1}, theme, TODAY)]:
                with self.subTest(theme=theme):
                    root = ET.fromstring(content)
                    self.assertEqual(root.attrib["viewBox"], "0 0 420 250")
                    self.assertEqual(root.attrib["role"], "img")
                    self.assertIn("2026-11-02", content)
                    self.assertIn(profile.THEMES[theme]["text"], content)
                    self.assertNotIn("<script", content)

    def test_small_languages_are_combined_without_losing_percentages(self):
        totals = {f"Language {index}": index for index in range(1, 8)}
        svg = profile.render_languages(totals, "light", TODAY)
        self.assertIn("Other languages", svg)
        self.assertIn("Other languages: 10.7%", svg)
        self.assertNotIn(">Language 1<", svg)

    def test_empty_language_card_is_honest(self):
        self.assertIn("No public language data", profile.render_languages({}, "light", TODAY))

    def test_svg_labels_are_escaped(self):
        svg = profile.render_languages({"A&B": 1}, "light", TODAY)
        ET.fromstring(svg)
        self.assertIn("A&amp;B", svg)

    def test_long_labels_do_not_overlap_bars_but_keep_accessible_names(self):
        name = "A long programming language name"
        svg = profile.render_languages({name: 100}, "light", TODAY)
        self.assertIn(f"{name}: 100.0%", svg)
        self.assertIn(f">{name[:18]}…</text>", svg)

    def test_text_has_wcag_aa_contrast_in_both_themes(self):
        for theme, colors in profile.THEMES.items():
            for role in ["text", "muted", "accent"]:
                with self.subTest(theme=theme, role=role):
                    self.assertGreaterEqual(contrast(colors[role], colors["bg"]), 4.5)


class ExcuseTests(unittest.TestCase):
    @patch.object(profile, "get_json")
    def test_only_a_public_developer_excuse_is_requested(self, get_json):
        get_json.return_value = [{"id": 705, "category": "developers", "excuse": "It  works on my machine."}]
        self.assertEqual(profile.fetch_excuse(), "It works on my machine.")
        get_json.assert_called_once_with(profile.EXCUSE_URL)

    @patch.object(profile, "get_json")
    def test_unexpected_responses_are_rejected(self, get_json):
        invalid = [None, {}, [], [None], [{}, {}], {"excuse": "Not a list"}]
        for text in [None, "", "   ", "x" * 301, "Text\nwith controls", "Text\u202ewith bidi"]:
            invalid.append([{"category": "developers", "excuse": text}])
        invalid.append([{"category": "office", "excuse": "Wrong category"}])
        for payload in invalid:
            get_json.return_value = payload
            with self.subTest(payload=payload), self.assertRaises(profile.StatsError):
                profile.fetch_excuse()

    def test_quote_uses_the_signature_lettering(self):
        output = profile.render_excuse("It works on my machine.")
        self.assertEqual(
            output,
            '<p align="center">\n'
            '    <em>“It workϟ oη my mαchiηe.”</em><br>\n'
            '    <sub>— <a href="https://excuser-three.vercel.app">Excuser</a></sub>\n'
            '</p>',
        )
        self.assertEqual("Martians VS Goblins".translate(profile.MARTIAN_LETTERS), "Mαrtiαηϟ VϞ Gobliηϟ")

    def test_quote_escapes_html_markdown_links_and_mentions(self):
        text = '<script> **code** ![image](https://example.test) @user `code` & $math$ \\ _text_ ~~text~~'
        output = profile.render_excuse(text)
        body = output.splitlines()[1].strip().removeprefix("<em>“").removesuffix("”</em><br>")
        self.assertEqual(unescape(body), text.translate(profile.MARTIAN_LETTERS))
        for forbidden in ["<", ">", "*", "`", "[", "]", "@", "$", "_", "~", "\\", ":"]:
            self.assertNotIn(forbidden, body)
        self.assertEqual(output.count('<a href="https://excuser-three.vercel.app">Excuser</a>'), 1)
        self.assertNotIn("<svg", output)

    def test_long_quotes_remain_native_text_without_fixed_dimensions(self):
        text = "W" * 300
        output = profile.render_excuse(text)
        self.assertIn(text, output)
        for forbidden in ["<img", "<svg", "width=", "height=", "style="]:
            self.assertNotIn(forbidden, output)


class NetworkTests(unittest.TestCase):
    def test_only_intended_https_api_hosts_are_allowed(self):
        for url in ["http://api.github.com/users/hajisml", "https://evil.test/", "https://api.github.com@evil.test/", "https://api.github.com:444/"]:
            with self.subTest(url=url), self.assertRaises(profile.StatsError):
                profile.get_json(url, "SECRET_TOKEN")

    def test_redirects_are_refused(self):
        self.assertIsNone(profile.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test"))

    @patch.object(profile, "build_opener")
    def test_authentication_stays_in_header_not_url(self, build_opener):
        response = MagicMock(status=200)
        response.read.return_value = b'{"data": {"languages": []}}'
        build_opener.return_value.open.return_value.__enter__.return_value = response
        profile.get_json(profile.WAKATIME_URL, "SECRET_TOKEN")
        request = build_opener.return_value.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer SECRET_TOKEN")
        self.assertNotIn("SECRET_TOKEN", request.full_url)

    @patch.object(profile, "build_opener")
    def test_http_errors_never_include_response_body_or_credentials(self, build_opener):
        build_opener.return_value.open.side_effect = HTTPError("SECRET_URL", 401, "SECRET_BODY", {}, None)
        with self.assertRaises(profile.StatsError) as raised:
            profile.get_json(profile.WAKATIME_URL, "SECRET_TOKEN")
        self.assertNotIn("SECRET", str(raised.exception))
        self.assertIn("401", str(raised.exception))

    @patch.object(profile.time, "sleep")
    @patch.object(profile, "build_opener")
    def test_transient_errors_have_bounded_retries(self, build_opener, sleep):
        build_opener.return_value.open.side_effect = URLError("SECRET_ERROR")
        with self.assertRaises(profile.StatsError) as raised:
            profile.get_json("https://api.github.com/users/hajisml")
        self.assertEqual(build_opener.return_value.open.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertNotIn("SECRET", str(raised.exception))

    @patch.object(profile, "build_opener")
    def test_pending_stats_are_not_published_as_zero_activity(self, build_opener):
        response = MagicMock(status=202)
        build_opener.return_value.open.return_value.__enter__.return_value = response
        with self.assertRaises(profile.StatsError):
            profile.get_json(profile.WAKATIME_URL)

    @patch.object(profile, "build_opener")
    def test_malformed_json_fails_safely(self, build_opener):
        response = MagicMock(status=200)
        response.read.return_value = b'SECRET_NOT_JSON'
        build_opener.return_value.open.return_value.__enter__.return_value = response
        with self.assertRaises(profile.StatsError) as raised:
            profile.get_json("https://api.github.com/users/hajisml")
        self.assertNotIn("SECRET", str(raised.exception))

    @patch.object(profile, "build_opener")
    def test_wakatime_requests_are_limited_to_standard_weekly_stats(self, build_opener):
        self.assertEqual(
            profile.WAKATIME_URL,
            "https://api.wakatime.com/api/v1/users/current/stats/last_7_days",
        )
        for path in ["stats/all_time", "projects", "heartbeats", "insights/projects/last_7_days", "insights/languages/last_7_days"]:
            with self.subTest(path=path), self.assertRaises(profile.StatsError):
                profile.get_json(f"https://api.wakatime.com/api/v1/users/current/{path}", "SECRET_TOKEN")
        build_opener.assert_not_called()

    @patch.object(profile, "build_opener")
    def test_excuser_refuses_credentials_and_other_categories(self, build_opener):
        with self.assertRaises(profile.StatsError) as raised:
            profile.get_json(profile.EXCUSE_URL, "SECRET_TOKEN")
        self.assertNotIn("SECRET_TOKEN", str(raised.exception))
        with self.assertRaises(profile.StatsError):
            profile.get_json("https://excuser-three.vercel.app/v1/excuse/office/1")
        build_opener.assert_not_called()

    @patch.object(profile, "build_opener")
    def test_excuser_requests_have_no_authorization_header(self, build_opener):
        response = MagicMock(status=200)
        response.read.return_value = b'[{"excuse": "It works on my machine.", "category": "developers"}]'
        build_opener.return_value.open.return_value.__enter__.return_value = response
        profile.fetch_excuse()
        request = build_opener.return_value.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.full_url, profile.EXCUSE_URL)

    @patch.object(profile, "build_opener")
    def test_oversized_responses_are_rejected(self, build_opener):
        response = MagicMock(status=200)
        response.read.return_value = b" " * 5_000_001
        build_opener.return_value.open.return_value.__enter__.return_value = response
        with self.assertRaises(profile.StatsError):
            profile.get_json("https://api.github.com/users/hajisml")

    @patch.object(profile.time, "sleep")
    @patch.object(profile, "build_opener")
    def test_connection_reset_during_read_is_retried_without_leaking_details(self, build_opener, sleep):
        response = MagicMock(status=200)
        response.read.side_effect = ConnectionResetError("SECRET_ERROR")
        build_opener.return_value.open.return_value.__enter__.return_value = response
        with self.assertRaises(profile.StatsError) as raised:
            profile.get_json("https://api.github.com/users/hajisml")
        self.assertEqual(build_opener.return_value.open.call_count, 3)
        self.assertNotIn("SECRET", str(raised.exception))


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=profile.ROOT)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.readme = self.root / "README.md"
        self.original = (
            f"intro\n{profile.WAKA_START}\nprevious statistics\n{profile.WAKA_END}\nfooter\n"
            f"{profile.EXCUSE_START}\nprevious excuse\n{profile.EXCUSE_END}\nsignature\n"
        )
        self.readme.write_text(self.original, encoding="utf-8")
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.excuse_patch = patch.object(profile, "fetch_excuse", return_value="It works on my machine.")
        self.fetch_excuse = self.excuse_patch.start()
        self.addCleanup(self.excuse_patch.stop)
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.out = redirect_stdout(self.stdout)
        self.err = redirect_stderr(self.stderr)
        self.out.__enter__()
        self.err.__enter__()
        self.addCleanup(self.out.__exit__, None, None, None)
        self.addCleanup(self.err.__exit__, None, None, None)

    @patch.object(profile, "get_json")
    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_missing_waka_secret_preserves_waka_and_updates_the_quote(self, github_stats, get_json):
        self.assertFalse(profile.update(self.root, today=TODAY))
        get_json.assert_not_called()
        output = self.readme.read_text(encoding="utf-8")
        self.assertIn("previous statistics", output)
        self.assertIn("It workϟ oη my mαchiηe.", output)
        self.assertEqual(len(list((self.root / "assets").glob("*.svg"))), 4)

    @patch.object(profile, "get_json")
    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_github_only_does_not_access_waka_even_with_a_token(self, github_stats, get_json):
        os.environ["WAKATIME_TOKEN"] = "SECRET_TOKEN"
        self.assertFalse(profile.update(self.root, github_only=True, today=TODAY))
        get_json.assert_not_called()
        self.fetch_excuse.assert_not_called()

    @patch.object(profile, "get_json", side_effect=profile.StatsError("Service unavailable"))
    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_waka_failure_preserves_previous_section_and_refreshes_github(self, github_stats, get_json):
        os.environ["WAKATIME_TOKEN"] = "SECRET_TOKEN"
        self.assertTrue(profile.update(self.root, today=TODAY))
        output = self.readme.read_text(encoding="utf-8")
        self.assertIn("previous statistics", output)
        self.assertIn("It workϟ oη my mαchiηe.", output)
        self.assertTrue((self.root / "assets" / "overview-light.svg").exists())
        self.assertNotIn("SECRET", self.stdout.getvalue() + self.stderr.getvalue())

    @patch.object(profile, "get_json", return_value={"data": {"languages": [{"name": "Go", "total_seconds": 60}], "projects": [{"name": "SECRET_PROJECT"}]}})
    @patch.object(profile, "github_stats", side_effect=profile.StatsError("Service unavailable"))
    def test_github_failure_does_not_block_waka_or_write_partial_cards(self, github_stats, get_json):
        os.environ["WAKATIME_TOKEN"] = "SECRET_TOKEN"
        self.assertTrue(profile.update(self.root, today=TODAY))
        output = self.readme.read_text(encoding="utf-8")
        self.assertIn("Go", output)
        self.assertTrue(output.startswith("intro\n"))
        self.assertTrue(output.endswith("signature\n"))
        self.assertNotIn("SECRET", output + self.stdout.getvalue() + self.stderr.getvalue())
        self.assertFalse((self.root / "assets").exists())
        self.assertIn("It workϟ oη my mαchiηe.", output)
        get_json.assert_called_once_with(profile.WAKATIME_URL, "SECRET_TOKEN")

    @patch.object(profile, "get_json")
    @patch.object(profile, "github_stats")
    def test_excuses_only_never_accesses_github_or_wakatime(self, github_stats, get_json):
        os.environ["GITHUB_TOKEN"] = "SECRET_GITHUB_TOKEN"
        os.environ["WAKATIME_TOKEN"] = "SECRET_WAKA_TOKEN"
        self.assertFalse(profile.update(self.root, excuses_only=True, today=TODAY))
        github_stats.assert_not_called()
        get_json.assert_not_called()
        self.fetch_excuse.assert_called_once_with()
        output = self.readme.read_text(encoding="utf-8")
        self.assertEqual(profile.replace_excuse(output, "previous excuse"), self.original)
        self.assertIn("It workϟ oη my mαchiηe.", output)
        self.assertFalse((self.root / "assets").exists())
        self.assertNotIn("SECRET", self.stdout.getvalue() + self.stderr.getvalue())

    @patch.object(profile, "get_json", return_value={"data": {"languages": [{"name": "Go", "total_seconds": 60}]}})
    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_excuse_failure_keeps_previous_quote_and_refreshes_other_services(self, github_stats, get_json):
        self.assertFalse(profile.update(self.root, excuses_only=True, today=TODAY))
        previous = self.readme.read_text(encoding="utf-8")
        os.environ["WAKATIME_TOKEN"] = "SECRET_TOKEN"
        self.fetch_excuse.side_effect = profile.StatsError("Service unavailable")
        self.assertTrue(profile.update(self.root, today=date(2026, 11, 3)))
        output = self.readme.read_text(encoding="utf-8")
        self.assertEqual(profile.replace_waka(output, "previous statistics"), previous)
        self.assertIn("Go", output)
        self.assertTrue((self.root / "assets" / "overview-light.svg").exists())
        self.assertIn("Dev Excuses:", self.stderr.getvalue())

    def test_initial_excuse_failure_leaves_readme_unchanged(self):
        self.fetch_excuse.side_effect = profile.StatsError("Invalid response")
        self.assertTrue(profile.update(self.root, excuses_only=True, today=TODAY))
        self.assertFalse((self.root / "assets").exists())
        self.assertEqual(self.readme.read_text(encoding="utf-8"), self.original)

    @patch.object(profile, "get_json", return_value={"data": {"languages": [{"name": "Go", "total_seconds": 60}]}})
    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_waka_and_excuse_updates_are_both_retained(self, github_stats, get_json):
        os.environ["WAKATIME_TOKEN"] = "SECRET_TOKEN"
        self.assertFalse(profile.update(self.root, today=TODAY))
        output = self.readme.read_text(encoding="utf-8")
        self.assertIn("Go", output)
        self.assertIn("It workϟ oη my mαchiηe.", output)
        self.assertNotIn("previous statistics", output)
        self.assertNotIn("previous excuse", output)
        self.assertEqual(
            profile.replace_excuse(profile.replace_waka(output, "previous statistics"), "previous excuse"),
            self.original,
        )

    @patch.object(profile, "get_json", return_value={"data": {
        "languages": [{"name": "Go", "total_seconds": 3600}],
        "projects": [{"name": "SECRET_PROJECT", "repository": "SECRET_REPOSITORY"}],
        "editors": [{"name": "SECRET_EDITOR"}],
        "machines": [{"name": "SECRET_MACHINE"}],
        "timezone": "SECRET_TIMEZONE",
    }})
    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_weekly_stats_metadata_is_never_persisted_or_logged(self, github_stats, get_json):
        os.environ["WAKATIME_TOKEN"] = "SECRET_TOKEN"
        self.assertFalse(profile.update(self.root, today=TODAY))
        output = self.readme.read_text(encoding="utf-8")
        self.assertIn("Go", output)
        self.assertIn("1 hr 0 mins", output)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn("SECRET", path.read_text(encoding="utf-8"))
        self.assertNotIn("SECRET", self.stdout.getvalue() + self.stderr.getvalue())
        get_json.assert_called_once_with(profile.WAKATIME_URL, "SECRET_TOKEN")

    def test_missing_excuse_markers_fail_without_overwriting_the_readme(self):
        original = "An unrelated README without generated sections.\n"
        self.readme.write_text(original, encoding="utf-8")
        self.assertTrue(profile.update(self.root, excuses_only=True, today=TODAY))
        self.assertEqual(self.readme.read_text(encoding="utf-8"), original)

    @patch.object(profile, "github_stats", return_value=(OVERVIEW, Counter(Go=100)))
    def test_identical_refresh_does_not_rewrite_files(self, github_stats):
        profile.update(self.root, today=TODAY)
        path = self.root / "assets" / "overview-light.svg"
        original_time = path.stat().st_mtime_ns
        profile.update(self.root, today=TODAY)
        self.assertEqual(path.stat().st_mtime_ns, original_time)
        self.assertFalse(list(self.root.rglob("*.tmp")))


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.readme = (profile.ROOT / "README.md").read_text(encoding="utf-8")
        parser = ImageParser()
        parser.feed(self.readme)
        self.images = parser.images

    def test_all_image_paths_exist_and_have_alt_text(self):
        for image in self.images:
            src = image["src"]
            with self.subTest(src=src):
                self.assertTrue(image.get("alt"))
                parsed = urlsplit(src)
                if not parsed.scheme:
                    self.assertTrue((profile.ROOT / parsed.path).is_file())

    def test_dynamic_images_have_exactly_one_variant_per_theme(self):
        for host in ["readme-typing-svg.demolab.com"]:
            images = [urlsplit(image["src"]) for image in self.images if urlsplit(image["src"]).netloc == host]
            self.assertEqual(len(images), 2)
            self.assertEqual({image.fragment for image in images}, {"gh-light-mode-only", "gh-dark-mode-only"})
            self.assertNotEqual(images[0].query, images[1].query)

    def test_quote_is_centered_and_signature_remains_in_footer(self):
        before, remainder = self.readme.split(profile.EXCUSE_START)
        quote, after = remainder.split(profile.EXCUSE_END)
        self.assertTrue(quote.strip().startswith('<p align="center">'))
        self.assertIn("<em>“", quote)
        self.assertIn('<a href="https://excuser-three.vercel.app">Excuser</a>', quote)
        self.assertNotIn("<img", quote)
        self.assertNotIn("<svg", quote)
        self.assertNotIn("assets/dev-excuse-", self.readme)
        self.assertNotIn("hajiibrahim-readme-dev-48.deno.dev", self.readme)
        self.assertIn("- Mαrtiαηϟ VϞ Gobliηϟ -", after)
        self.assertLess(after.index("<!-- Footer -->"), after.index("- Mαrtiαηϟ VϞ Gobliηϟ -"))

    def test_quote_is_immediately_below_streak_and_above_wakatime(self):
        streak = self.readme.rindex('src="assets/streak-')
        streak_end = self.readme.index("</div><br>", streak) + len("</div><br>")
        quote_start = self.readme.index(profile.EXCUSE_START)
        quote_end = self.readme.index(profile.EXCUSE_END)
        self.assertEqual(self.readme[streak_end:quote_start].strip(), "")
        self.assertLess(quote_end, self.readme.index("View my WakaTime Statistics"))

    def test_mastodon_badge_is_in_the_socials_section(self):
        socials = self.readme.split("<!-- Socials-->")[1].split("<!-- Donations-->")[0]
        self.assertIn('href="https://mastodon.social/@hajisml"', socials)
        self.assertIn('alt="Mastodon"', socials)
        self.assertIn("logo=mastodon", socials)

    def test_unused_footer_cards_are_removed(self):
        self.assertFalse(list((profile.ROOT / "assets").glob("dev-excuse-*.svg")))
        profile.replace_excuse(self.readme, "test")

    def test_weekly_streak_and_typing_content_are_preserved(self):
        workflow = (profile.ROOT / ".github/workflows/profile-stats.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("user=hajisml&mode=weekly&"), 2)
        self.assertEqual(workflow.count("date_format=j%20M%5B%20Y%5D"), 2)
        for image in self.images:
            parsed = urlsplit(image["src"])
            query = parse_qs(parsed.query)
            if parsed.netloc == "readme-typing-svg.demolab.com":
                self.assertEqual(query["font"], ["Fira Sans"])
                self.assertEqual(query["width"], ["410"])
                self.assertIn("lil W", query["lines"][0])

    def test_typing_and_streak_text_has_aa_contrast(self):
        for image in self.images:
            parsed = urlsplit(image["src"])
            fields = []
            if parsed.netloc == "readme-typing-svg.demolab.com":
                fields = ["color"]
            if not fields:
                continue
            theme = "light" if parsed.fragment == "gh-light-mode-only" else "dark"
            query = parse_qs(parsed.query)
            for field in fields:
                with self.subTest(host=parsed.netloc, theme=theme, field=field):
                    self.assertGreaterEqual(contrast("#" + query[field][0], profile.THEMES[theme]["bg"]), 4.5)
        for theme in profile.THEMES:
            root = ET.parse(profile.ROOT / "assets" / f"streak-{theme}.svg").getroot()
            texts = root.findall(".//{http://www.w3.org/2000/svg}text")
            self.assertTrue(texts)
            for text in texts:
                color = text.attrib.get("fill")
                if color and color.startswith("#"):
                    with self.subTest(theme=theme, text=text.text):
                        self.assertGreaterEqual(contrast(color, profile.THEMES[theme]["bg"]), 4.5)

    def test_streaks_are_repository_hosted_and_valid_svg(self):
        images = [urlsplit(image["src"]) for image in self.images if image["src"].startswith("assets/streak-")]
        self.assertEqual(len(images), 2)
        self.assertEqual({image.fragment for image in images}, {"gh-light-mode-only", "gh-dark-mode-only"})
        self.assertNotIn("streak-stats.demolab.com?", self.readme)
        for theme in profile.THEMES:
            content = (profile.ROOT / "assets" / f"streak-{theme}.svg").read_text(encoding="utf-8")
            root = ET.fromstring(content)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertNotIn("<script", content)
            self.assertNotIn("<foreignObject", content)
            self.assertNotIn("href=", content)
            labels = " ".join(root.itertext())
            self.assertTrue("Week Streak" in labels or "Awaiting first refresh" in labels)

    def test_existing_content_and_user_preferences_are_retained(self):
        for content in ["bc1q9vyjnvxjkk40mjqf6cgkadklfxrug5ez6kzpxx", "middleamber84@walletofsatoshi.com",
                        "server.ListenAndServe()", "github.com/hajisml/kamugram", "zone01kisumu.ke",
                        "Figma", "GIMP", "Inkscape", "Brand identity", "UI/UX", "Spring Boot",
                        "halim-c4x.pages.dev", "wakatime.com/badge/user/00a59a24-7f70-4add-abf2-ff361b4693fc.svg"]:
            with self.subTest(content=content):
                self.assertIn(content, self.readme)
        self.assertNotIn("Photoshop", self.readme)
        self.assertNotIn("Illustrator", self.readme)
        self.assertIn("https://substack.com/@hajisml", self.readme)

    def test_go_snippet_is_a_complete_about_me_server(self):
        snippet = self.readme.split("```go\n")[1].split("```")[0]
        for content in ["package main", "type Profile struct", '`json:"name"`', '`json:"location"`',
                        '`json:"focus"`', '`json:"portfolio"`', '"encoding/json"', '"net/http"',
                        'mux.HandleFunc("GET /about", aboutMe)', 'w.Header().Set("Content-Type", "application/json")',
                        "json.NewEncoder(w).Encode(me)", "ReadHeaderTimeout:", "5 * time.Second",
                        "server.ListenAndServe()", "log.Printf(", "Lakecity"]:
            with self.subTest(content=content):
                self.assertIn(content, snippet)
        self.assertNotIn("Hello", snippet)
        self.assertNotIn("panic(", snippet)

    def test_profile_snippet_avoids_time_sensitive_status(self):
        snippet = self.readme.split("```go\n")[1].split("```")[0]
        for word in ["zone01", "kisumu", "apprentice", "student", "learning", "age", "employer"]:
            with self.subTest(word=word):
                self.assertNotRegex(snippet.lower(), rf"\b{word}\b")

    def test_visible_location_is_lakecity_and_education_is_preserved(self):
        self.assertIn("a software engineer based in Lakecity.", self.readme)
        self.assertNotIn("based in Kisumu", self.readme)
        self.assertIn("Software Engineering Apprentice at", self.readme)
        self.assertIn("Zone01 Kisumu", self.readme)
        self.assertIn("B.Sc. Software Development, KCA University", self.readme)

    def test_waka_markers_are_unambiguous(self):
        profile.replace_waka(self.readme, "test")

    def test_generated_cards_are_valid_svg_without_scripts_or_external_links(self):
        for theme in profile.THEMES:
            for kind in ["overview", "languages"]:
                path = profile.ROOT / "assets" / f"{kind}-{theme}.svg"
                content = path.read_text(encoding="utf-8")
                root = ET.fromstring(content)
                self.assertEqual(root.attrib["role"], "img")
                self.assertNotIn("<script", content)
                self.assertNotIn("href=", content)

    def test_workflow_has_branch_guards_and_a_pinned_action(self):
        workflow = (profile.ROOT / ".github" / "workflows" / "profile-stats.yml").read_text(encoding="utf-8")
        for guard in ["github.event_name != 'pull_request'", "github.repository == 'hajisml/hajisml'",
                      "github.ref == 'refs/heads/dev'", "github.ref == 'refs/heads/main'",
                      'git push origin "HEAD:refs/heads/$TARGET_BRANCH"', "secrets.WAKATIME_TOKEN"]:
            self.assertIn(guard, workflow)
        self.assertNotIn("--force", workflow)
        self.assertNotIn("git merge", workflow)
        self.assertNotIn("git add -A", workflow)
        self.assertIn("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", workflow)
        self.assertNotIn("dev-excuse-", workflow)

    def test_streak_renderer_is_pinned_and_isolated_from_write_access_and_wakatime(self):
        workflow = (profile.ROOT / ".github/workflows/profile-stats.yml").read_text(encoding="utf-8")
        job = workflow.split("  generate-streaks:\n")[1].split("  update:\n")[0]
        self.assertIn("contents: read", job)
        self.assertNotIn("contents: write", job)
        self.assertNotIn("WAKATIME_TOKEN", job)
        self.assertIn("persist-credentials: false", job)
        self.assertIn("github.event_name != 'pull_request'", job)
        self.assertEqual(job.count("DenverCoder1/github-readme-streak-stats@adbd07609bb771d3510a15ee2f3b31d5fbe5201d"), 2)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", job)
        self.assertIn("actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093", workflow)
        self.assertIn("needs: [validate, generate-streaks]", workflow)


if __name__ == "__main__":
    unittest.main()
