# Feasibility survey — calc-engine MCP wrapper

Author: solomon (review/architecture) · Date: 2026-09-29
Scope: survey only — no code changed, nothing committed to calc-engine.
Inputs read: `~/house-conventions/CONVENTIONS.md`, `AGENT.md`, `SKILL.md`,
`pyproject.toml`, source skeleton via code-indexer (watcher live, state=idle).

## 0. Verdict (up front)

**FEASIBLE-WITH-CAVEATS.** The CLI's discipline (byte-exact stdout, typed
single-line stderr, exit-code taxonomy, pure ops layer) maps cleanly onto an
MCP stdio server — but `eval`/`batch` are stateful-within-invocation, `@file`
resolution is a CLI-layer concern that must NOT leak into MCP tool args, and
the four annotations can be declared honestly only per-tool after a small
number of semantic decisions the owner must ratify (§4).

## 1. Subcommand → MCP tool mapping

Current surface: 22 subcommands declared in SKILL.md front matter (guarded by
the doc-drift contract test, so the list is trustworthy). Proposed mapping:

### 1.1 Clean 1:1 wrappers (stateless, pure functions of args)

| CLI | Candidate MCP tool | Notes |
|---|---|---|
| `convert-base`, `convert-unit` | `convert_base`, `convert_unit` | pure; args map directly |
| `stat <op>` | `stat` with `op` enum arg | one tool, `op` as enum — better than 12 tools |
| `matrix <op>`, `vector <op>` | `matrix`, `vector` | same pattern; strict-JSON strings pass through as-is |
| `finance <op>` | `finance` | strict exact arg sets preserved by arg schema |
| `distribution <op> <family>` | `distribution` | flags-as-args; note abbreviations disabled → tool schema must use exact names |
| `gof <op>` | `gof` | `--field` required → schema-required field |
| `physics-constant`, `physics <domain>`, `calculus`, `sym` | direct | `sym`/`calculus` need `--var` list → array arg |
| `bits <op>`, `endian <op>` | `bits`, `endian` | `--width` enum (8/16/32/64) → schema enum; float ops restricted to 32/64 |
| `hash <alg>`, `crc <alg>`, `base64 <op>` | direct | data arg as string; see resolver note below |
| `datetime <op>`, `regex <op>` | direct | regex 2 s timeout semantics carry over |
| `assert <op>` | `assert` | failure is domain failure (exit 1), not usage — see annotations §2 |

### 1.2 Where 1:1 breaks down

- **`eval` compound statements.** `eval` accepts multiple statements with a
  shared names dict, indexed rendering on multi-expression results, and
  per-statement error slots (`N: ErrorType: ...`) that do not abort the run.
  This is stateful *within one invocation* but stateless *across* invocations —
  so a single `eval` MCP tool taking a `statements: string[]` (or a newline
  string) preserves the semantics honestly. What is NOT available: cross-call
  variable persistence. An MCP session could fake it with a server-side names
  dict keyed per session, but that would (a) break the determinism/no-hidden
  state contract, (b) make `idempotentHint` false, (c) complicate multi-client
  stdio usage. Recommendation: expose `eval` as stateless-per-call only.
  `--let` becomes a `bindings: {name, literal}[]` arg (numeric literals only —
  enforce in schema); `--exact` and `--precision` become tool args.
- **`batch` stdin mode.** Batch is stdin-driven with the 16 MiB resolver cap.
  MCP tools take structured args, not raw stdin. Two honest options:
  (a) fold batch into `eval` (a compound statement list IS a batch — the
  semantics are nearly identical: newline-separated, blank/`#` ignored);
  (b) a `batch` tool taking `statements: string`. Recommend (a): fewer tools,
  one code path. The only delta is error-slot indexing output, which both
  paths already share.
- **`@file` / `@-` resolution.** The resolver (`input_resolver.py`) is
  deliberately CLI-layer-only and ops never touch fs/stdin (statically
  enforced). In an MCP server the client supplies data as an argument value —
  file paths in tool args are a footgun (path traversal, surprise fs reads by
  a "calculator"). Recommendation: **do not replicate `@file` in MCP**; data
  arguments arrive as plain strings/bytes in the tool call. If large payloads
  matter, document the 16 MiB cap as a validation error (`ArgumentError`
  equivalent). `@@escape` disappears entirely (no `@` convention in args).
  This is the cleanest boundary the existing architecture offers: the resolver
  never has to exist in the MCP layer.
- **Exit codes / stderr → MCP errors.** MCP tools signal failure via
  `isError: true` results, not exit codes. The typed stderr line
  (`ErrorType: description`) maps to the tool's text content verbatim — it is
  already machine-parseable, which is precisely what the CLI was built for.
  Keep the taxonomy as the content; do not invent a second error format.

### 1.3 Tool-count question

22 subcommands → is that 22 tools or ~12 grouped tools (op/family as enum
args)? Grouping matches the CLI's own internal structure (`_handlers` map) and
keeps the client's tool list manageable. This is a design choice, flagged for
owner ratification (§4).

## 2. Four annotations — proposal and honesty check

MCP defines tool annotations as advisory hints for client UX. The house set
proposed:

| Annotation | Value per tool | Honesty check |
|---|---|---|
| `readOnlyHint` | `true` for all 22 | Every subcommand is read-only w.r.t. the world: no fs writes, no network, no env mutation. `hash`/`crc`/`base64` read files via resolver only in CLI mode — MCP mode reads no fs at all. **Honest.** |
| `idempotentHint` | `true` for all tools EXCEPT `distribution sample` | Everything is a pure function of args — repeated calls give byte-identical output. `distribution sample` with `--seed` is deterministic too; if `--seed` is schema-required, `idempotentHint=true` holds there as well. If a future sample-without-seed mode appears, this flips. **Honest, conditional on seed-required.** |
| `openWorldHint` | `false` for all | No network, no external service, no dynamic lookups beyond pinned libs (scipy constants table is local and pinned in `uv.lock`). **Honest.** |
| `destructiveHint` | `false` for all | Nothing is destroyed; `assert` failing is a *domain result*, not destruction. (destructiveHint is only meaningful when readOnlyHint=false anyway; included for the four-slot requirement.) **Honest.** |

The house-chosen set (`readOnlyHint`, `idempotentHint`, `openWorldHint`,
`destructiveHint`) is exactly the standard MCP core annotation set and every
slot can be declared truthfully *because* the CLI already pins determinism
(seed-required sampling, no implicit RNG), purity (ops never touch fs/stdin),
and closed-world behavior. No tool needs a dishonest annotation — this is
unusual and is a direct dividend of the existing contract tests. `assert`
returning `false` is a normal success (exit 0), so it too stays
read-only/idempotent.

Caveat: annotations are advisory in the spec and must not be relied on for
security decisions — worth stating in the server's tool descriptions too.

## 3. Transport / architecture options

### Option A — stdio server wrapping the installed `calc` console script

The MCP server (e.g. `mcp` python SDK, not currently a dependency — would be
added) spawns `calc <sub> ...` per tool call, parses stdout/stderr/exit code,
and converts to MCP results.

- Pros: zero coupling — the CLI contract (byte-exact stdout, one typed stderr
  line, exit codes) is *already* the interface and is contract-tested via
  subprocess; process isolation gives the regex 2 s timeout a hard kill
  boundary; no import of the package means no accidental state sharing.
- Cons: process spawn per call (~50–150 ms + interpreter startup with
  numpy/scipy/sympy imports — the heavy deps make this the dominant cost,
  plausibly 0.5–2 s per call); stdout parsing is stringly-typed (render layer
  output, not values); a second dependency surface (`mcp` SDK) in a server
  process that duplicates argument parsing (must re-declare 22 subcommands'
  arg schemas in MCP terms, then hand-serialize to argv — a genuine drift risk
  against `_handlers`, mitigated only by the doc-drift test pattern extended
  to the MCP layer).

### Option B — stdio server importing calc ops in-process

The MCP server imports `calc.ops.*` (and the render layer for formatting)
directly; tool handlers call op functions with typed values, catch `CalcError`
subclasses, and render via `render.py`.

- Pros: **the ops-purity guarantee (ops never touch fs/stdin, statically
  enforced) is exactly the precondition for safe in-process reuse** — no
  surprises from hidden I/O; typed errors (`CalcError` taxonomy) become
  structured MCP error results without string parsing; no argv serialization
  → no schema/argv drift; far faster (no per-call interpreter + numpy import);
  `render.py` gives byte-identical formatting so MCP text output matches CLI
  output exactly.
- Cons: the CLI layer (argparse glue, resolver, `_handlers`) is bypassed, so
  validation logic that lives in `cli.py` (dynamic kwargs parsing, physics
  kwargs extraction, datetime handler glue) must be re-exercised or refactored
  down into ops; the regex 2 s timeout — implemented where? If it lives in the
  CLI layer as a subprocess guard, in-process needs its own guard
  (concurrent.futures timeout is not preemptive for pure-Python regex; the
  CLI's subprocess kill actually is). This is the one real semantic gap.

### Recommendation

**Option B, with one refactor precondition**: the validation/timeout glue in
`cli.py` must be a thin skin over ops (it largely already is, per
AGENT.md's stated principle); anything needed by MCP (validation order, regex
timeout) belongs in ops or a shared layer, not argparse callbacks. The
ops-purity static test gives high confidence this is already true. Option A
remains the correct *fallback* if the refactor turns out to touch more than
expected — it is cheap, honest, and contract-tested today. Both options need
the `mcp` SDK added via uv (PEP 668 rules apply; project venv only).

Transport: stdio is the obvious first transport (local agents); HTTP/SSE adds
nothing for this house and is out of scope.

## 4. Risks and open questions for owner ratification

1. **Tool granularity**: 22 flat tools vs ~12 grouped (op-as-enum). Affects
   client ergonomics and schema size. Recommend grouped; needs owner sign-off.
2. **Stateless `eval` only**: no cross-call variable persistence in MCP mode.
   Confirm acceptable (recommended) or explicitly want session-scoped state.
3. **No `@file`/`@-` in MCP**: data via tool args only. The 16 MiB cap becomes
   an arg-validation error. Confirm.
4. **`batch` folded into `eval`** vs separate `batch` tool. Recommend fold.
5. **Dependency**: adding the `mcp` python SDK to calc-engine's dependencies
   (or as an optional extra — recommended: `mcp = ["mcp>=1.x"]` extra so the
   CLI install stays lean).
6. **Packaging boundary**: does the MCP server live in the same repo/package
   (`calc_mcp` module) or a sibling? Same repo recommended (contract tests and
   doc-drift guard can span both); athena owns that decision with this survey
   as input.
7. **Regex timeout in-process** (Option B): needs a real mechanism decided by
   the implementer; the CLI's subprocess-kill approach does not port directly.
8. **Contract-test extension**: the byte-exact stdout contract should be
   extended so MCP tool output must byte-match `calc` CLI output for the same
   input — prevents two divergent truths. Strongly recommended as an
   acceptance criterion before any merge.
9. **Annotations are advisory** — if any client treats `readOnlyHint=true` as
   a security guarantee, the description text should restate actual behavior.

## 5. Reasoning for the verdict

Feasible-with-caveats, not plain feasible, because: (a) three genuine
impedance mismatches exist (eval compound semantics, batch stdin, file
resolver) and each has a defensible answer that still narrows the interface
relative to the CLI — narrowing needs owner ratification, not dev discretion;
(b) the four annotations are declarable honestly today, but two of them
(`idempotentHint` on sample, `openWorldHint` globally) are conditional on
policies that a careless future change could silently invalidate — the
doc-drift test should grow annotation-drift checks; (c) Option B depends on
one refactor fact (validation/timeout in ops layer) that I verified by
skeleton reading and AGENT.md's stated principle but not by line-level audit —
that audit is athena's first implementation step, with Option A as the
pre-priced fallback.

What makes this unusually tractable: the CLI was already designed to an
agent-machine contract (byte-exact, typed, deterministic, closed-world,
pure ops). MCP is, in effect, a second client of the same contract. Most
wrappers fail because the underlying tool was built for humans first; this
one was not.