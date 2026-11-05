# Profile statistics

The profile keeps its existing content and adds theme-aware cards, a collapsible
WakaTime language breakdown, and a cached Dev Excuses quote. All generation uses Python
3.10+ and its standard library for overview/language cards and quote updates.
Weekly streaks use the upstream project's pinned action in GitHub's runner; no
local package installation is required.

## Theme handling

Each themed image uses one HTML `<picture>` with a dark-mode `<source>` and one
light-mode fallback `<img>`. This prevents the duplicate light/dark images seen
in GitHub's rendered branch README. The media query follows the browser's
`prefers-color-scheme` setting; if the GitHub theme is manually set differently
from the browser/OS preference, colors may not match that GitHub setting.
No custom README CSS or JavaScript is required.

The typing quote, its animation settings, and the weekly streak mode are
preserved. Text, dates, numbers, and accents have explicit colors for each theme.
Generated cards have matching light/dark backgrounds and accessible SVG titles.

## Weekly streaks

The README uses repository-hosted `assets/streak-light.svg` and
`assets/streak-dark.svg`, not the public streak endpoint. During shipping, both
the public service and GitHub's image proxy timed out, so relying on that service
at profile-view time was removed.

The pinned `DenverCoder1/github-readme-streak-stats` action renders both variants
from GitHub contribution calendars in a separate **read-only job**. It uses the
short-lived repository `GITHUB_TOKEN`, with no private-repository PAT and no
WakaTime secret. The job installs PHP and the renderer's Composer dependencies
only on the ephemeral GitHub runner, not on your machine. It uploads only the
two SVGs; the publishing job downloads and validates them before committing.

Weekly Sun–Sat mode, date format, and explicit light/dark text colors are
preserved. Animations are disabled for predictable static rendering. Cards
refresh with the workflow, normally daily after merging to `main`. If generation
fails, the publishing job does not run and the previous cards remain unchanged.
The initial files are honest pending-refresh placeholders, replaced by real
cards after the first successful generation; no streak counts are fabricated.

## GitHub overview and languages

The generator requests only the public `/users/hajisml` and
`/users/hajisml/repos` endpoints and language totals for public, owned, non-fork
repositories. It does not enumerate private repositories or use private
contributions. The overview shows public repository count, stars and forks
received by original repositories, and followers.

Language percentages represent **code bytes**, not coding time or proficiency.
The five largest languages are listed individually; the rest are combined as
"Other languages". Archived original repositories are included. Forks are excluded
from language totals, stars, and forks received, but included in the public
repository count.

GitHub Actions uses its short-lived `GITHUB_TOKEN`. Do not create a personal access
token with broad repository access for this workflow.

## Connect WakaTime when ready

No WakaTime account settings or repository secrets have been changed as part of
this build. Until connected, the README has an honest setup message; the existing
public total-coding-time badge continues to work independently.

1. Read [WakaTime's authentication documentation](https://wakatime.com/developers#authentication).
   Follow its personal OAuth-token link for scripts and README statistics.
2. Generate a personal OAuth token that can read weekly statistics (documented as
   requiring `read_stats`). No language-only token setting is required.
   Do not assume the token itself is restricted to languages; keep it secret.
   WakaTime currently documents API keys as write-only; use an OAuth token, not
   your editor's API key.
3. In `hajisml/hajisml`, open **Settings → Secrets and variables → Actions**.
   Add a repository secret called **`WAKATIME_TOKEN`** with that token.
   Never put the token in a URL, README, source file, issue, or chat message.
4. Push the approved changes to `dev` to run the initial workflow. The build itself
   does not push or trigger it. After the workflow is on the default branch,
   **Actions → Profile statistics → Run workflow** also allows a branch selection.

The generator uses **only `/users/current/stats/last_7_days`** for WakaTime,
with an Authorization header and an allowlist of
**language name + numeric duration**. It computes its own
percentages, progress bars, and time strings instead of embedding arbitrary API
text. The presentation follows Jandrana's collapsible statistics section.

Only languages, durations, percentages, the seven-day period, and refresh date
are published. Project names, repository names, paths, branches, editors,
machines, operating systems, timezones, daily schedules, AI usage, and raw API
responses are never written to files or logs. The standard weekly response may
include project names and other metadata in memory; only its language names and
numeric language durations are consumed. Extra fields are never copied into the
README, SVGs, artifacts, or logs. The token itself is not restricted to languages.
The HTTP client refuses other WakaTime endpoints, including project, heartbeat,
all-time statistics, and insights endpoints.

The language-specific Insights endpoint was tried during the first live run, but
returned HTTP 402 (Payment Required). The standard weekly endpoint is the approved
fallback; the output allowlist, rather than a paid endpoint or token setting,
enforces the public language-only presentation.

Language totals still reveal how much time you spend in particular languages;
that is the intended public information. The existing badge also exposes total
coding time. Revoking the token stops future refreshes, but does not remove data
already published in Git history.

## Dev Excuses

The quote below the streak uses [Excuser](https://excuser-three.vercel.app)'s public
`/v1/excuse/developers/1` endpoint. No account or credentials are required, and the
HTTP client refuses to send credentials to this service. The old Deno service is
no longer referenced by the README.

Each refresh fetches one developer excuse and updates only the
`<!--START_SECTION:dev-excuse-->` / `<!--END_SECTION:dev-excuse-->` block in
`README.md`. It is a simple italicized quote in a centered HTML paragraph, with a
small Excuser source link underneath, not a card or image. It sits immediately
below the streak and above the WakaTime section. Native GitHub text automatically
follows light/dark themes and wraps at mobile widths without separate image variants.

The lettering matches `Mαrtiαηϟ VϞ Gobliηϟ` using Unicode substitutions
(`a → α`, `n → η`, `s → ϟ`, with uppercase counterparts), rather than loading a
custom font. Other letters, capitalization, and punctuation are preserved. The
text is length-checked and escaped to prevent HTML, Markdown, link, or mention
injection. There are no footer SVG assets or external fonts to load. Stylized
Unicode may be pronounced differently by screen readers than ordinary English.

The quote updates with the profile workflow, normally daily after merging to `main`,
not on every profile view. If Excuser is unavailable or returns invalid data, the
previous quote remains visible in the README. The upstream service has no uptime
guarantee, but its outages do not turn the footer into a broken external image.
Your original signature remains in the footer at the bottom of the profile.

## Branch and publishing behavior

- Tests run on relevant `dev`/`main` pushes and pull requests, without secrets.
- The updater runs only in `hajisml/hajisml`, on `dev` or `main`, and never on a
  pull-request event. It writes only to the branch that triggered it.
- While these changes exist only on `dev`, a `dev` push tests the updater without
  touching `main`. Daily scheduling starts **after you manually merge to `main`**,
  because GitHub schedules run only from the default branch. The schedule is
  04:23 UTC; GitHub may delay scheduled runs.
- Generated refreshes use `github-actions[bot]` with the message
  `Update profile statistics`, no attribution trailers, and real timestamps.
  Automated updates are honestly bot-authored; development commits use your Git
  identity and will be organized separately when you request shipping.
- Commits made with the workflow's `GITHUB_TOKEN` do not trigger another `push`
  workflow, preventing update loops. Writes are serialized per branch.
- Only `README.md` and the six named GitHub SVGs are staged. No force-push, branch
  creation, merge, release, or deployment is performed. If branch protection
  rejects an automated push, the workflow fails without bypassing it.
- Missing WakaTime credentials leave that section unchanged. An upstream error
  preserves that service's previous output, publishes any successful independent
  refresh, and marks the run failed. Empty activity is distinct from an error.
  A failure in the separate streak-generation job blocks publishing entirely.

## Local checks

Run offline tests from the repository root:

```sh
python3 -B -m unittest discover -s .github/scripts -p 'test_*.py' -v
```

Refresh just the public GitHub cards without accessing WakaTime or Excuser:

```sh
python3 -B .github/scripts/update_profile.py --github-only
```

Refresh just the public Dev Excuses quote without accessing GitHub or WakaTime:

```sh
python3 -B .github/scripts/update_profile.py --excuses-only
```

Authenticated full refreshes read `GITHUB_TOKEN` (optional for public GitHub
data) and `WAKATIME_TOKEN` from the environment. Raw responses and credentials
are never persisted; authenticated redirects are refused. API timeouts and
server retries are bounded. Unauthenticated GitHub calls are rate limited, so
avoid repeated local refreshes.

Before merging, review the `dev` README on GitHub in both light and dark browser
preferences, including when GitHub's theme differs from your system setting,
and at a narrow mobile width, including the cached Dev Excuses quote.
