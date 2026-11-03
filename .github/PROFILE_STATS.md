# Profile statistics

The profile keeps its existing content and adds theme-aware cards, a collapsible
WakaTime language breakdown, and a cached Dev Excuses quote. All generation uses Python
3.10+ and its standard library; there are no packages to install or third-party
stats actions to run.

## Theme handling

Each themed image has a `#gh-light-mode-only` or `#gh-dark-mode-only` fragment.
GitHub selects the variant using the viewer's GitHub theme, including when it
differs from the operating system's theme. No custom README CSS or JavaScript is
required. Both image variants may appear in Markdown viewers that do not support
GitHub's theme fragments.

The typing quote, its animation settings, and the weekly streak mode are
preserved. Text, dates, numbers, and accents have explicit colors for each theme.
Generated cards have matching light/dark backgrounds and accessible SVG titles.

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
2. Generate a personal OAuth token that can read the Insights API (documented as
   requiring `read_summaries`). No language-only token setting is required.
   Do not assume the token itself is restricted to languages; keep it secret.
   WakaTime currently documents API keys as write-only; use an OAuth token, not
   your editor's API key.
3. In `hajisml/hajisml`, open **Settings → Secrets and variables → Actions**.
   Add a repository secret called **`WAKATIME_TOKEN`** with that token.
   Never put the token in a URL, README, source file, issue, or chat message.
4. Push the approved changes to `dev` to run the initial workflow. The build itself
   does not push or trigger it. After the workflow is on the default branch,
   **Actions → Profile statistics → Run workflow** also allows a branch selection.

The generator uses **only `/users/current/insights/languages/last_7_days`** for
WakaTime, with an Authorization header and an allowlist of
**language name + numeric duration**. It computes its own
percentages, progress bars, and time strings instead of embedding arbitrary API
text. The presentation follows Jandrana's collapsible statistics section.

Only languages, durations, percentages, the seven-day period, and refresh date
are published. Project names, repository names, paths, branches, editors,
machines, operating systems, timezones, daily schedules, AI usage, and raw API
responses are never written to files or logs. Other WakaTime endpoints, including
the broad statistics and project endpoints, are refused by the HTTP client.
The targeted endpoint and output allowlist enforce what the integration requests
and publishes; they do not change the underlying token's permissions. Any extra
response fields are ignored rather than copied into the README.

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
- Only `README.md` and the four named GitHub SVGs are staged. No force-push, branch
  creation, merge, release, or deployment is performed. If branch protection
  rejects an automated push, the workflow fails without bypassing it.
- Missing WakaTime credentials leave that section unchanged. An upstream error
  preserves that service's previous output, publishes any successful independent
  refresh, and marks the run failed. Empty activity is distinct from an error.

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

Before merging, review the `dev` README on GitHub in both light and dark themes,
including when GitHub's theme differs from your system setting, and at a narrow
mobile width, including the cached Dev Excuses quote.
