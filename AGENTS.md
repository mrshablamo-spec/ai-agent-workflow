# Agent Roles: Mini-Palantir Supply Chain Intelligence Engine

## Overview

This project uses two AI agents in complementary roles. Claude acts as the Architect and Analyst; ChatGPT Codex acts as the Engineer. Clear role separation avoids duplication and keeps the system coherent.

---

## Agent 1: Claude (Architect & Intelligence Analyst)

**Primary Responsibilities:**

| Domain | Tasks |
|---|---|
| System Design | Define module structure, data flows, interfaces between layers |
| Prompt Engineering | Write extraction prompts for parsing Item 1 / Item 1A text |
| Intelligence Logic | Define risk scoring heuristics, dependency ranking rules |
| Graph Semantics | Define what nodes and edges represent, what edge weights mean |
| QA / Review | Review Codex-written code for correctness, security, and adherence to SEC Fair Access rules |
| Documentation | Maintain `PROJECT_STRUCTURE.md`, `AGENTS.md`, `PLAN.md` |

**What Claude Does NOT Do:**
- Write boilerplate file I/O, HTTP request handlers, or CLI wiring (delegated to Codex)
- Run code or execute scrapers directly

**Guiding Principles for Claude:**
1. Always check SEC EDGAR rate limits before designing scraper logic.
2. Design parsers to be resilient to inconsistent 10-K HTML formatting (filings vary by year and filer).
3. Keep the graph schema simple: do not add edges that cannot be justified by filing text.
4. Flag any data point that requires a paid API and propose a free alternative.

---

## Agent 2: ChatGPT Codex (Engineer)

**Primary Responsibilities:**

| Domain | Tasks |
|---|---|
| Scraper Implementation | Implement `sec_scraper.py` and `news_scraper.py` per Claude's spec |
| Parser Implementation | Implement `tenk_parser.py` and `entity_extractor.py` |
| Analyst Implementation | Implement `risk_scorer.py` and `dependency_mapper.py` |
| Graph Implementation | Implement `graph_generator.py` using NetworkX |
| CLI Wiring | Implement `main.py` entry point and `config.py` |
| Testing | Write unit tests for each module using `pytest` |
| Dependency Management | Maintain `requirements.txt`, handle library compatibility |

**What Codex Does NOT Do:**
- Redefine the system architecture without Claude's approval
- Add paid API integrations
- Modify `AGENTS.md`, `PROJECT_STRUCTURE.md`, or `PLAN.md` without review

**Guiding Principles for Codex:**
1. Follow the module interfaces defined by Claude exactly — do not rename functions.
2. Add a `User-Agent` header to every EDGAR HTTP request: `User-Agent: supply-chain-intel <your-email@example.com>`.
3. Cache raw EDGAR responses locally before parsing — never re-fetch if a cached file exists.
4. Raise descriptive exceptions; do not silently swallow errors.

---

## Collaboration Protocol

```
Claude defines interface/spec
        │
        ▼
Codex implements the module
        │
        ▼
Claude reviews output, checks logic + SEC compliance
        │
        ▼
Codex fixes flagged issues
        │
        ▼
Module marked complete → move to next phase
```

### Handoff Format

When Claude hands off a task to Codex, it provides:
- Module name and file path
- Function signatures (input types, return types)
- Behavioral spec (what it should do, edge cases to handle)
- Any relevant SEC EDGAR endpoint URLs or data format notes

When Codex hands back to Claude, it provides:
- Completed code
- Brief description of implementation choices
- Any assumptions made where the spec was ambiguous

---

## Escalation Rules

| Situation | Action |
|---|---|
| SEC rate limit risk detected | Claude re-specs the scraper before Codex writes any more code |
| Ambiguous 10-K section boundary | Claude provides updated regex/parsing rules |
| Missing free data source | Claude identifies alternative before Codex proceeds |
| Graph becomes unmaintainably complex | Claude simplifies schema; Codex refactors |
