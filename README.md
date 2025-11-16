# NewsNow Neon Desktop

NewsNow Neon is a Tkinter desktop dashboard that surfaces curated NewsNow
headlines, enriched with cached summaries and live configuration controls. It is
part of a wider experiments workspace but can be run on its own via
`scripts/newsnow_neon/legacy_app.py`.

## Feature Highlights

- **Headline aggregation** – Scrapes multiple NewsNow sections and interleaves
  them in a scrolling ticker plus sortable list.
- **Offline-aware summaries** – Article text is fetched with resilient retry
  logic, summarised through LiteLLM, and cached (alongside fallbacks) for
  offline reuse.
- **Redis-backed caching** – Optional Redis storage keeps headlines, ticker
  text, and summaries warm between sessions.
- **Redis diagnostics** – Use the “Redis Stats” button to review cache TTL, payload
  size, snapshot counts, and server health details sourced directly from Redis.
- **Historical snapshots** – Keep a rolling 24-hour Redis history (keys such as
  `news:YYYY-MM-DD:*`) to replay recent headline states; toggle it from the
  settings panel.
- **Configurable auto-refresh** – Headlines refresh automatically every five
  minutes by default; toggle or adjust the interval directly from the settings
  panel, complete with a live countdown to the next refresh.
- **Background watch counter** – Enable the new checkbox in the Behavior &
  Timing panel to poll for unseen headlines in the background and surface how
  many fresh articles are waiting outside the current list.
- **User preferences** – Colour profiles, ticker speed, window geometry,
  logging visibility, and LiteLLM debug flags persist in
  `%LOCALAPPDATA%/NewsNowNeon/ainews_settings.json` (override with
  `NEWS_APP_SETTINGS`).
- **Observability controls** – Separate checkboxes let you toggle Python debug
  logging and LiteLLM verbose output while the app is running.
- **Keyword heatmap** – Launch the “Keyword Heatmap” window to compare how often
  highlighted terms appear across sections; intensity is scaled to per-section
  headline density.
- **Info dialog** – Tap the “Info” button for a quick snapshot of version,
  system details, author attribution (defaults to `https://github.com/voytas75`),
  and the support link (defaults to `https://ko-fi.com/voytas`).
- **Keyword exclusions** – Enter comma-separated terms to hide matching
  headlines across tickers and list views without mutating cached data.

## Running the App

```bash
python scripts/newsnow_neon/legacy_app.py
```

Ensure dependencies from `pyproject.toml`/`requirements.txt` are installed. The
module auto-loads a `.env` file (if `python-dotenv` is available) so you can set
environment variables there.

## Optional Environment Variables

| Variable | Purpose |
| --- | --- |
| `NEWS_SUMMARY_TIMEOUT` | Seconds before LiteLLM article summarisation aborts (min 5, default 15). |
| `NEWS_TICKER_TIMEOUT` | Legacy ticker LLM timeout; kept for backwards compatibility (min 3, default 8). |
| `NEWS_CACHE_KEY` / `NEWS_CACHE_TTL` | Redis key name and TTL (defaults: `ainews:headlines:v1`, 900s). |
| `NEWS_HISTORY_PREFIX` / `NEWS_HISTORY_TTL` | Redis prefix and TTL for historical snapshots (defaults: `news`, 86400s). |
| `REDIS_URL` | Enables Redis caching when set (e.g. `redis://localhost:6379/0`). |
| `NEWS_APP_SETTINGS` | Custom path for the persisted settings JSON. |
| `NEWS_SUMMARY_MODEL` / `NEWS_SUMMARY_PROVIDER` / `NEWS_SUMMARY_API_*` | Override the LiteLLM model/provider/base/key used exclusively for article summaries. Secrets are masked in startup logs. |
| `NEWS_SUMMARY_AZURE_*` | Azure-specific overrides for summaries (deployment, API version, AD token). |
| `LITELLM_MODEL` / `LITELLM_PROVIDER` / `LITELLM_API_BASE` / `LITELLM_API_KEY` | Default LiteLLM configuration when summary-specific overrides are absent (e.g. set `LITELLM_PROVIDER=azure` with related Azure credentials). |
| `AZURE_OPENAI_*` | Generic Azure OpenAI deployment/API/key overrides shared across LiteLLM calls. |
| `LOCALAPPDATA` | Must be set on non-Windows systems so the app can locate its settings directory. |
| `NEWSNOW_APP_AUTHOR` | Overrides the author string surfaced by the Info dialog (defaults to `https://github.com/voytas75`). |
| `NEWSNOW_DONATE_URL` | URL opened from the Info dialog “Support” link (defaults to `https://ko-fi.com/voytas`). |

> ⚠️ Keys or tokens are never emitted to logs. The app masks any variable whose
> name ends in `KEY`, `TOKEN`, `SECRET`, or `PASSWORD` (as well as known Azure
> variants) when printing the startup configuration report.

## Development Notes

- Code style follows `black` and `ruff`; type hints target `mypy --strict`.
- Tests are organised under `tests/` (none exist for the Tk app yet – consider
  adding integration tests with `pytest` + `pytest-tkinter`).
- Whenever you change user-visible behaviour, update both this README and the
  change log in `scripts/newsnow_neon/legacy_app.py` (see the `Updates:`
  section at the top of the module).

## Troubleshooting

- **403/429 summaries** – Retry logic automatically cycles through alternate
  headers and fallback user agents; final errors surface as cached or headline
  snippets instead of raising.
- **No Redis** – Leave `REDIS_URL` unset to run in purely in-memory mode; the
  UI will display “Redis: OFF”.
- **Verbose LLM traces** – Tick “LiteLLM Debug” in the settings panel to enable
  provider-specific logging without restarting the app.
- **Auto refresh timing** – Use the “Auto Refresh” checkbox and interval spinbox
  to tweak how often headlines update (minimum 1 minute) and watch the
  countdown for the next update.
