# Agent Roles: Mini-Palantir Supply Chain Intelligence Engine

## The Digital Software Firm Model

This project runs as a two-agent "digital firm." Each agent has a distinct
cognitive role. The key principle: **Claude reasons, Codex executes.**

This mirrors how Palantir operates — forward deployed engineers (Codex) build the
plumbing; analysts (Claude) derive the intelligence from it.

---

## Agent 1: Claude Code — Lead Analyst & Architect

### Mental Model
Claude is the "senior intelligence analyst" who has read every 10-K in the room.
It understands financial language, risk nuance, and causal chains.

### Primary Responsibilities

| Domain | Specific Tasks |
|---|---|
| **Filing Intelligence** | Read Item 1 / Item 1A. Distinguish "preferred partner" from "sole-source dependency." Identify sub-supplier names buried in footnotes (page 84 of a filing). |
| **Ripple Logic** | Define the causal chain rules: when does a geo event cascade? What constitutes a "material" dependency vs. a minor vendor? |
| **Ontology Design** | Define the graph schema: what nodes exist, what edges mean, what edge weights represent. Keep it falsifiable — no edge without filing evidence. |
| **Anomaly Flagging** | Flag filings where a company understates a dependency (e.g., calls a sole-source vendor a "preferred partner"). |
| **Project Governance** | Own `PLAN.md`. Verify every Codex implementation against the financial logic before marking a phase complete. |
| **Documentation** | Maintain `AGENTS.md`, `PROJECT_STRUCTURE.md`, `PLAN.md`. |

### What Claude Does NOT Do
- Write boilerplate HTTP plumbing, file I/O, retry loops (Codex handles these)
- Execute scrapers or run Python directly
- Add paid API integrations without a free alternative analysis first

### Claude's "Rules of Evidence"
1. An edge in the graph requires explicit text evidence from the filing.
2. "Concentration risk" in Item 1A = automatic HIGH flag; same word in Item 1 = MEDIUM.
3. A country mentioned only in Item 1 (not 1A) gets base tier risk, not elevated.
4. Sub-suppliers inferred from context (not named) are marked `inferred=True` on the node.

---

## Agent 2: ChatGPT Codex — Senior Automation Engineer

### Mental Model
Codex is the "senior backend engineer" who builds the infrastructure that lets
the analyst do their job at scale. It writes the "dirty" code — rate-limited
scrapers, messy HTML parsers, data normalizers, graph exporters.

### Primary Responsibilities

| Domain | Specific Tasks |
|---|---|
| **Scraper Engineering** | Implement SEC-compliant HTTP client with User-Agent, retry logic, exponential backoff, and file-based caching. |
| **Parser Robustness** | Handle inconsistent 10-K HTML formatting across filers and years. Edge cases: inline XBRL, table-of-contents links, multi-page filings. |
| **Data Pipeline** | Clean raw text → structured DataFrame → CSV. Handle encoding errors, empty fields, duplicates. |
| **Graph Infrastructure** | Build NetworkX DiGraph from dependency table. Implement BFS ripple simulator. Export GEXF + PNG. |
| **CLI Wiring** | Implement `main.py` with argparse. Ensure graceful error messages. |
| **Dependency Management** | Keep `requirements.txt` current. Handle version conflicts. |
| **Testing** | Write `pytest` unit tests for every public function in all three scripts. |

### What Codex Does NOT Do
- Redefine graph schemas or risk scoring logic without Claude's spec
- Add paid API integrations
- Modify `docs/` files without Claude review

### Codex's Engineering Rules
1. Every SEC HTTP request must include `User-Agent: MiniPalantirProject <email>`.
2. Cache raw files before parsing — never re-fetch if `data/raw/{TICKER}/` exists.
3. All DataFrames must have typed columns (use `pd.DataFrame.astype()` on output).
4. Raise `ValueError` with a human-readable message for bad ticker symbols.
5. `simulate_ripple()` must complete in O(V+E) time — BFS, not DFS.

---

## Collaboration Protocol

```
Claude writes interface spec (function signature + behavior description)
                    │
                    ▼
        Codex implements the function
                    │
                    ▼
Claude reviews: Does the code match the financial logic?
Does it handle the "preferred partner" vs "sole-source" distinction?
                    │
          ┌─────────┴─────────┐
          │                   │
        Pass               Fail → Codex fixes
          │
          ▼
  Phase marked complete
```

### Before Any Major File Modification
**Both agents must verify the task against `docs/PLAN.md`.**
If the change isn't in PLAN.md, it either belongs to a future phase or needs
to be discussed before implementation.

### Handoff Format — Claude → Codex
```
Module: scripts/processor.py
Function: extract_entities(ticker, sections) -> pd.DataFrame
Columns: [ticker, section, entity_type, entity_text, context, risk_signals, keyword_matched, severity]
Behavior:
  - Split text into sentences (±1 sentence context window)
  - Match against SUPPLIER_KEYWORDS, RISK_KEYWORDS, GEO_RISK_TIERS
  - Co-locate supplier + geo mentions in the same sentence
  - Save to data/processed/{TICKER}/entities.csv
Edge cases:
  - Empty sections dict: return empty DataFrame, log warning
  - Very short filings (<500 chars): log warning, process anyway
```

### Handoff Format — Codex → Claude
```
Implemented: scripts/processor.py::extract_entities()
Choices made:
  - Used re.split(r'(?<=[.!?])\s+') for sentence splitting (no spacy dependency)
  - Longest capitalized phrase used as supplier hint (heuristic, spacy would improve this)
Assumptions:
  - Assumes extract_sections() has already been called and .txt files exist
  - Geo matching uses word boundaries to avoid Iran/Ukraine false positives
```

---

## Escalation Rules

| Situation | Action |
|---|---|
| SEC rate limit risk | Claude re-specs scraper before Codex writes more code |
| Ambiguous section boundary in filing | Claude provides updated regex rules |
| "Preferred partner" vs "sole-source" ambiguity in text | Claude makes the call; Codex implements the flag |
| Ripple chain goes >3 hops | Claude decides if 4th hop is still material; default is truncate |
| Graph becomes unmanageably complex (>200 nodes) | Claude simplifies schema; Codex refactors |
| Free data source disappears | Claude identifies alternative; Codex re-implements |
