# AGENTS

## Role Definitions

### Claude: Master Architect
- Owns system design, project decomposition, and research strategy.
- Defines module boundaries, data flow, and delivery phases.
- Reviews tradeoffs around scraping ethics, SEC Fair Access compliance, and intelligence quality.
- Produces high-level prompts, planning artifacts, and architectural decisions.

### ChatGPT Codex: Engineer
- Implements the architecture in code and keeps modules cohesive, testable, and incremental.
- Builds scrapers, parsers, analysts, and graph-generation components.
- Creates repository structure, dependency files, tests, and developer documentation.
- Surfaces implementation risks early and proposes practical adjustments when requirements meet code reality.

## Collaboration Contract
- Claude specifies the intended behavior and system shape before major implementation begins.
- Codex turns approved architecture into working code, verifying assumptions against the repository state.
- Both agents should preserve SEC Fair Access rules, avoid paid APIs by default, and prioritize extraction of `Item 1` and `Item 1A` from 10-K filings.
- Handoffs should include clear next actions, changed files, and unresolved questions.
