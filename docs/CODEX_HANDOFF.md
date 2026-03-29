# CODEX_HANDOFF

## Status
- Review findings from the last cycle: resolved.
- Codex validation target status:
  - Backend unit tests: passing.
  - Frontend production build: passing.
  - SEC User-Agent warning: implemented in config, API health, and workflow notes.
  - iXBRL/table-of-contents section parsing edge case: covered with candidate ranking and tests.
  - Country list expansion: completed with alias-aware geography mapping.

## Next Task Queue
- Mocked SEC integration coverage: completed with FilingIndex and router health tests.
- Frontend SEC warning surfacing: completed in mission control.
- CLI export artifacts: completed for JSON, CSV, and GEXF output.
- Push the local commit once GitHub auth is available on this machine.
- Optionally export graph JSON/GEXF artifacts from the UI or CLI.

## Architecture Decisions
- The SEC client now retries `429` responses with exponential backoff instead of failing immediately.
- Section extraction chooses the longest plausible `Item 1` -> `Item 1A` span to avoid table-of-contents false positives common in iXBRL-heavy filings.
- Geography detection uses canonical-country aliases rather than a short flat list so downstream graph nodes remain normalized.
- Placeholder SEC identity values are allowed for local development but reported explicitly in API health and workflow notes to keep Fair Access requirements visible.

## Publish Blocker
- Local branch is ahead by one commit and ready to push.
- Current blocker: local git HTTPS auth is not configured, so `git push` fails with `could not read Username for 'https://github.com': Device not configured`.
