#!/usr/bin/env python3
"""Generate public GitHub cards, language-only WakaTime stats, and Dev Excuses.

Python 3.10+; standard library only. Raw API responses are never saved or logged.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
USERNAME = "hajisml"
WAKA_START = "<!--START_SECTION:waka-->"
WAKA_END = "<!--END_SECTION:waka-->"
EXCUSE_START = "<!--START_SECTION:dev-excuse-->"
EXCUSE_END = "<!--END_SECTION:dev-excuse-->"
MARTIAN_LETTERS = str.maketrans({"a": "α", "n": "η", "s": "ϟ", "A": "Δ", "N": "Ͷ", "S": "Ϟ"})
WAKATIME_URL = "https://api.wakatime.com/api/v1/users/current/stats/last_7_days"
EXCUSE_URL = "https://excuser-three.vercel.app/v1/excuse/developers/1"
THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d1d9e0",
        "text": "#1f2328",
        "muted": "#59636e",
        "accent": "#0969da",
        "track": "#e6edf3",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#3d444d",
        "text": "#f0f6fc",
        "muted": "#9198a1",
        "accent": "#79c0ff",
        "track": "#212830",
    },
}


class StatsError(Exception):
    """A safe, human-readable error without response bodies or credentials."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an Authorization header to another location.
        return None


def get_json(url, token=""):
    """GET JSON from intended endpoints; never authenticate to the excuse service."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in {
        "api.github.com", "api.wakatime.com", "excuser-three.vercel.app"
    }:
        raise StatsError("Refusing a request outside the supported HTTPS APIs.")
    if parsed.netloc == "api.wakatime.com" and url != WAKATIME_URL:
        raise StatsError("Only the weekly-statistics WakaTime endpoint is allowed.")
    if parsed.netloc == "excuser-three.vercel.app" and (url != EXCUSE_URL or token):
        raise StatsError("Excuser requests must use the public developers endpoint without credentials.")
    headers = {"Accept": "application/json", "User-Agent": "hajisml-profile-stats"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if parsed.netloc == "api.github.com":
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = Request(url, headers=headers)
    opener = build_opener(NoRedirect())
    for attempt in range(3):
        try:
            with opener.open(request, timeout=30) as response:
                if response.status == 202:
                    raise StatsError("Statistics are still being calculated; keeping the previous output.")
                raw = response.read(5_000_001)
                if len(raw) > 5_000_000:
                    raise StatsError("API response exceeds the expected size.")
                return json.loads(raw)
        except HTTPError as error:
            error.close()
            if error.code >= 500 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise StatsError(f"{parsed.netloc} returned HTTP {error.code}; keeping the previous output.") from None
        except (OSError, HTTPException):
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise StatsError(f"Could not reach {parsed.netloc}; keeping the previous output.") from None
        except (ValueError, UnicodeError):
            raise StatsError(f"{parsed.netloc} returned invalid JSON.") from None


def number(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise StatsError("An API returned an invalid numeric statistic.")
    return value


def language_name(value):
    # Names are plain text, not arbitrary Markdown, paths, or API-provided HTML.
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9 .+#()/_-]{1,40}", value):
        raise StatsError("An API returned an invalid language name.")
    return value


def github_stats(token=""):
    """Count only public, owned repositories; forks do not affect language totals."""
    profile = get_json(f"https://api.github.com/users/{USERNAME}", token)
    if not isinstance(profile, dict) or str(profile.get("login", "")).lower() != USERNAME:
        raise StatsError("Unexpected GitHub profile response.")
    repositories = []
    page = 1
    while True:
        batch = get_json(
            f"https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}",
            token,
        )
        if not isinstance(batch, list):
            raise StatsError("Unexpected GitHub repository response.")
        for repo in batch:
            if not isinstance(repo, dict):
                raise StatsError("Unexpected GitHub repository entry.")
            owner = repo.get("owner")
            if not isinstance(owner, dict):
                raise StatsError("Unexpected GitHub repository owner.")
            if repo.get("private") is False and str(owner.get("login", "")).lower() == USERNAME:
                repositories.append(repo)
        if len(batch) < 100:
            break
        page += 1

    totals = Counter()
    originals = [repo for repo in repositories if repo.get("fork") is False]
    for repo in originals:
        name = repo.get("name")
        if not isinstance(name, str) or not name:
            raise StatsError("Unexpected GitHub repository name.")
        languages = get_json(f"https://api.github.com/repos/{USERNAME}/{quote(name, safe='')}/languages", token)
        if not isinstance(languages, dict):
            raise StatsError("Unexpected GitHub language response.")
        for language, size in languages.items():
            totals[language_name(language)] += number(size)

    overview = [
        ("Public repositories", len(repositories)),
        ("Stars received", sum(number(repo.get("stargazers_count")) for repo in originals)),
        ("Forks received", sum(number(repo.get("forks_count")) for repo in originals)),
        ("Followers", number(profile.get("followers"))),
    ]
    return overview, totals


def svg_card(title, description, body, theme, updated):
    colors = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="250" viewBox="0 0 420 250" role="img" aria-labelledby="title description">
  <title id="title">{escape(title)}</title>
  <desc id="description">{escape(description)}</desc>
  <rect x="0.5" y="0.5" width="419" height="249" rx="8" fill="{colors['bg']}" stroke="{colors['border']}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" fill="{colors['text']}">
    <text x="24" y="34" font-size="17" font-weight="600">{escape(title)}</text>
{body}
    <text x="24" y="230" font-size="11" fill="{colors['muted']}">Public data · Updated {updated.isoformat()} UTC</text>
  </g>
</svg>
'''


def render_overview(overview, theme, updated):
    colors = THEMES[theme]
    rows = []
    for index, (label, value) in enumerate(overview):
        y = 76 + index * 35
        rows.append(f'    <text x="24" y="{y}" font-size="14">{escape(label)}</text>')
        rows.append(f'    <text x="396" y="{y}" text-anchor="end" font-size="17" font-weight="600" fill="{colors["accent"]}">{int(value):,}</text>')
    rows.append(f'    <text x="24" y="207" font-size="11" fill="{colors["muted"]}">Stars and forks: owned, non-fork repositories</text>')
    description = "; ".join(f"{label}: {int(value):,}" for label, value in overview)
    return svg_card("GitHub Overview", description, "\n".join(rows), theme, updated)


def render_languages(totals, theme, updated):
    colors = THEMES[theme]
    ordered = sorted(
        ((name, size) for name, size in totals.items() if size > 0),
        key=lambda item: (-item[1], item[0]),
    )
    total = sum(size for _, size in ordered)
    visible = ordered[:5]
    if len(ordered) > 5:
        visible.append(("Other languages", sum(size for _, size in ordered[5:])))
    rows = []
    descriptions = []
    if not total:
        rows.append('    <text x="24" y="95" font-size="14">No public language data available.</text>')
    for index, (name, size) in enumerate(visible):
        percent = size / total * 100
        y = 65 + index * 25
        label = name if len(name) <= 19 else name[:18] + "…"
        rows.append(f'    <text x="24" y="{y}" font-size="12">{escape(label)}</text>')
        rows.append(f'    <rect x="173" y="{y - 8}" width="157" height="7" rx="3" fill="{colors["track"]}"/>')
        rows.append(f'    <rect x="173" y="{y - 8}" width="{157 * percent / 100:.2f}" height="7" rx="3" fill="{colors["accent"]}"/>')
        rows.append(f'    <text x="396" y="{y}" text-anchor="end" font-size="12">{percent:.1f}%</text>')
        descriptions.append(f"{name}: {percent:.1f}%")
    rows.append(f'    <text x="24" y="207" font-size="11" fill="{colors["muted"]}">Code bytes · public, owned, non-fork repositories</text>')
    return svg_card("Languages", "; ".join(descriptions) or "No language data", "\n".join(rows), theme, updated)


def duration(seconds):
    minutes = int(seconds) // 60
    hours, minutes = divmod(minutes, 60)
    if hours:
        unit = "hr" if hours == 1 else "hrs"
        return f"{hours} {unit} {minutes} mins"
    return f"{minutes} mins"


def render_wakatime(payload, updated):
    """Allowlist language names and numeric durations; ignore all other fields."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not isinstance(data.get("languages"), list):
        raise StatsError("WakaTime returned no language statistics; keeping the previous output.")
    if data.get("is_up_to_date") is False:
        raise StatsError("WakaTime is still calculating statistics; keeping the previous output.")
    totals = Counter()
    for item in data["languages"]:
        if not isinstance(item, dict):
            raise StatsError("WakaTime returned an invalid language entry.")
        totals[language_name(item.get("name"))] += number(item.get("total_seconds"))
    ordered = sorted(
        ((name, seconds) for name, seconds in totals.items() if seconds > 0),
        key=lambda item: (-item[1], item[0]),
    )
    total = sum(seconds for _, seconds in ordered)
    lines = ["**📊 This Week I Spent My Time On**", "", "```text", "Programming Languages:"]
    if not total:
        lines.append("No language activity tracked in the last 7 days.")
    for name, seconds in ordered:
        percent = seconds / total * 100
        filled = min(20, round(percent / 5))
        bar = "█" * filled + "░" * (20 - filled)
        lines.append(f"{name:<24} {duration(seconds):<17} {bar} {percent:6.2f} %")
    lines.extend([
        "```",
        "",
        f"Last 7 days · Updated {updated.isoformat()} UTC · "
        "Source: [WakaTime](https://wakatime.com/@00a59a24-7f70-4add-abf2-ff361b4693fc)",
    ])
    return "\n".join(lines)


def fetch_excuse():
    """Fetch a single public developer excuse, rejecting unexpected responses."""
    payload = get_json(EXCUSE_URL)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise StatsError("Excuser returned an unexpected response; keeping the previous quote.")
    item = payload[0]
    text = item.get("excuse")
    if (
        item.get("category") != "developers"
        or not isinstance(text, str)
        or not 1 <= len(text) <= 300
        or not text.isprintable()
        or not text.strip()
    ):
        raise StatsError("Excuser returned an invalid developer excuse; keeping the previous quote.")
    return " ".join(text.split())


def render_excuse(text):
    """Render a centered text quote using the signature's Unicode lettering."""
    styled = escape(text.translate(MARTIAN_LETTERS), quote=False)
    # Encode inline Markdown syntax, mentions, and URL separators as literal text.
    # Escaping HTML first also prevents responses from injecting section markers.
    styled = re.sub(
        r"[\\`*_\[\]~$:@]",
        lambda match: f"&#{ord(match[0])};",
        styled,
    )
    return (
        '<p align="center">\n'
        f'    <em>“{styled}”</em><br>\n'
        '    <sub>— <a href="https://excuser-three.vercel.app">Excuser</a></sub>\n'
        '</p>'
    )


def replace_section(readme, content, start, end, label):
    if readme.count(start) != 1 or readme.count(end) != 1:
        raise StatsError(f"README must have exactly one pair of {label} markers.")
    before, remainder = readme.split(start)
    if end not in remainder:
        raise StatsError(f"{label} markers are out of order.")
    _, after = remainder.split(end)
    return f"{before}{start}\n{content}\n{end}{after}"


def replace_waka(readme, content):
    return replace_section(readme, content, WAKA_START, WAKA_END, "WakaTime")


def replace_excuse(readme, content):
    return replace_section(readme, content, EXCUSE_START, EXCUSE_END, "Dev Excuses")


def update(root, *, github_only=False, excuses_only=False, today=None):
    """Prepare each service's complete output before writing; retain old data on errors."""
    today = today or datetime.now(timezone.utc).date()
    failures = []
    outputs = {}
    if not excuses_only:
        try:
            overview, languages = github_stats(os.environ.get("GITHUB_TOKEN", ""))
            for theme in THEMES:
                outputs[root / "assets" / f"overview-{theme}.svg"] = render_overview(overview, theme, today)
                outputs[root / "assets" / f"languages-{theme}.svg"] = render_languages(languages, theme, today)
        except StatsError as error:
            failures.append(f"GitHub: {error}")

    if not github_only and not excuses_only:
        token = os.environ.get("WAKATIME_TOKEN", "")
        if token:
            try:
                payload = get_json(WAKATIME_URL, token)
                content = render_wakatime(payload, today)
                readme = root / "README.md"
                outputs[readme] = replace_waka(readme.read_text(encoding="utf-8"), content)
            except StatsError as error:
                failures.append(f"WakaTime: {error}")
        else:
            print("WAKATIME_TOKEN is not configured; leaving the WakaTime section unchanged.")

    if not github_only:
        try:
            excuse = fetch_excuse()
            readme = root / "README.md"
            current = outputs[readme] if readme in outputs else readme.read_text(encoding="utf-8")
            outputs[readme] = replace_excuse(current, render_excuse(excuse))
        except StatsError as error:
            failures.append(f"Dev Excuses: {error}")

    for path, content in outputs.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        # A same-directory replace avoids partially written cards or README content.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        print(f"Updated {path.relative_to(root)}")
    for message in failures:
        print(message, file=sys.stderr)
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    services = parser.add_mutually_exclusive_group()
    services.add_argument(
        "--github-only",
        action="store_true",
        help="Refresh only public GitHub cards, without accessing WakaTime or Excuser.",
    )
    services.add_argument(
        "--excuses-only",
        action="store_true",
        help="Refresh only the public Dev Excuses quote, without accessing GitHub or WakaTime.",
    )
    arguments = parser.parse_args()
    return int(update(ROOT, github_only=arguments.github_only, excuses_only=arguments.excuses_only))


if __name__ == "__main__":
    sys.exit(main())
