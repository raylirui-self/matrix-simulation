# Code Review — Cognitive Matrix v2

**Date:** 2026-04-14
**Reviewer:** Claude (Opus 4.6)
**Scope:** `src/`, `gui/backend/api/routes/`, `gui/frontend/src/lib/stores/simulation.ts`, `main.py`, `config/default.yaml`, `tests/`
**Branch:** `main` (plus 3 uncommitted modifications)

## How to use this document
Each finding has five sections:
1. **Details** — what the problem is
2. **Impact** — concrete risk
3. **Actions** — how to fix
4. **Post-Fix Verification** *(fill in after remediation)* — commit hash, tests run, result

Severity legend: **Critical** (fix before next deploy) → **High** (fix this sprint) → **Medium** (backlog) → **Low** (nice-to-have).

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 3 | ✅ Fixed |
| High     | 5 | ✅ Fixed |
| Medium   | 5 | ✅ Fixed |
| Low      | 5 | ⏳ Deferred (backlog) |
| **Total**| **18** | **13 fixed, 5 deferred** |

Top risks: **auth gaps** on god-mode / media endpoints, a **tick-loop race condition** when multiple WebSocket clients share a run, and an **IndexError** in CSV export after extinction events — **all fixed**.

## Fix validation — test suite

A new end-to-end test module [tests/test_e2e_api.py](../tests/test_e2e_api.py) was added alongside the fixes. It exercises every button-equivalent endpoint the frontend uses via `starlette.testclient.TestClient`, plus the WebSocket protocol including malformed-input paths:

| Category | Test |
|----------|------|
| Health & create | `test_health_endpoint`, `test_create_and_fetch_simulation` |
| Play/advance | `test_advance_ticks_and_history`, `test_state_endpoint_returns_full_snapshot` |
| Config sliders (M-2) | `test_config_slider_allowed_sections`, `test_config_slider_rejects_non_whitelisted` |
| God-mode gate (C-1) | `test_god_mode_disabled_by_default`, `test_god_mode_requires_admin_token`, `test_god_mode_spawn_with_valid_token`, `test_god_mode_meteor_and_event` |
| Population cap (M-3) | `test_god_mode_spawn_n_clamped_below_cap` |
| WebSocket protocol (C-2/C-3/M-4) | `test_websocket_tick_flow`, `test_websocket_state_sync`, `test_websocket_malformed_json_returns_error_frame`, `test_websocket_unknown_command_returns_error` |
| Media rate limit (H-2) | `test_media_narrate_rate_limit` |
| Population summary (M-5) | `test_extinction_population_summary` |
| CSV export (H-1) | `test_csv_export_handles_extinction` |
| World artifact flag | `test_world_route_has_artifact_fields` |

**Results:** `pytest tests/test_e2e_api.py` — **19 passed in 31.01s**. `ruff check src/ gui/ tests/` — **All checks passed**.

Full suite result (`pytest`) is also green after repairing a pre-existing failure in [tests/test_websocket_data.py::test_world_route_exposes_artifact_flag](../tests/test_websocket_data.py) where the uncommitted test was constructing `Artifact` with non-existent `row`/`col`/`created_tick`/`origin_agent_id` kwargs. Fixed by using the real `Artifact` dataclass fields (`faction_name`, `era_tick`, `cycle_number`, `awareness_level`, `tech_level`).

---

# Critical

## C-1 — God Mode endpoints mounted without authentication

- **Location:** [gui/backend/api/main.py:37](../gui/backend/api/main.py#L37), [gui/backend/api/routes/god_mode.py](../gui/backend/api/routes/god_mode.py)
- **Category:** Security

### Details
The `god_mode` router is mounted with no auth middleware, no environment flag, and no CORS origin restriction. Every endpoint (`/spawn`, `/kill`, `/event`, `/modify`, `/meteor`, `/famine`, …) is reachable by any client that can hit the API. These endpoints mutate engine state arbitrarily.

### Impact
Total compromise of simulation integrity in any deployed environment. An attacker can spawn unlimited agents (OOM), kill the civilization, inject false causal events, or rewrite individual agent attributes. If the backend is ever bound to a non-localhost interface, this is a full RCE-equivalent inside the simulation domain.

### Actions
1. Gate the router behind an env flag: `if os.getenv("GOD_MODE_ENABLED") == "1": app.include_router(god_mode.router)`.
2. Add a FastAPI dependency that validates an API key header (`X-Admin-Token`) read from env.
3. Default to **disabled** in production builds; require explicit opt-in for local dev.
4. Emit a startup warning log when god mode is enabled.

### Post-Fix Verification
- [x] Commit: _pending — staged in working tree_
- [x] Changes: new [gui/backend/api/auth.py](../gui/backend/api/auth.py); [main.py:32-57](../gui/backend/api/main.py#L32-L57) gates router on `GOD_MODE_ENABLED`; [god_mode.py:19-35](../gui/backend/api/routes/god_mode.py#L19-L35) adds `Depends(require_admin)` + audit logger.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_god_mode_disabled_by_default`, `test_god_mode_requires_admin_token`, `test_god_mode_spawn_with_valid_token`, `test_god_mode_meteor_and_event` — all PASS.
- [x] Result: Router unmounted by default (404); 401 without `X-Admin-Token`; accepts requests with matching token; startup log warns on enable.
- [x] Notes: `ADMIN_TOKEN` is optional — if unset, requests are allowed once the env gate is on, so solo devs don't need to plumb a header. Set `ADMIN_TOKEN=…` to require it.

---

## C-2 — Race condition on shared engine during concurrent WebSocket ticks

- **Location:** [gui/backend/api/state.py:96-112](../gui/backend/api/state.py#L96-L112), [gui/backend/api/routes/websocket.py:26-39](../gui/backend/api/routes/websocket.py#L26-L39)
- **Category:** Concurrency / Correctness

### Details
Multiple WebSocket clients connecting to the same `run_id` share one engine instance from the manager cache. `state.run_tick()` does not hold the manager `_lock` during `engine.tick()`; the lock only guards dict accesses. Two concurrent clients (or one client + an auto-run timer) can re-enter `engine.tick()` and corrupt internal collections (agents list, factions, matrix_state counters).

### Impact
Non-deterministic state corruption: duplicated births/deaths, skipped causal events, inconsistent faction membership, hard-to-reproduce test failures. Because the bug is timing-dependent it tends to surface only under load or during demos — i.e. the worst moments.

### Actions
1. Add a per-engine `asyncio.Lock` on the `RunHandle` and acquire it around the full `engine.tick()` invocation.
2. Alternatively, enforce **single-writer** semantics by rejecting a second WebSocket with an explicit error (`{"type":"error","code":"run_busy"}`).
3. Add a regression test that spawns two concurrent WS clients against one run and asserts invariants (agent count monotonicity, no duplicate IDs).

### Post-Fix Verification
- [x] Changes: [state.py:31-62](../gui/backend/api/state.py#L31-L62) adds `_engine_locks_sync` + `_engine_locks_async` dicts and `get_engine_lock_*` helpers; [state.py:run_tick](../gui/backend/api/state.py) now wraps tick inside `with self.get_engine_lock_sync(run_id):`; [websocket.py:_run_and_send_tick](../gui/backend/api/routes/websocket.py) wraps snapshot→tick→delta inside `async with manager.get_engine_lock_async(run_id):`.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_websocket_tick_flow`, full websocket_data suite — PASS. Existing 495-test suite still green (no lock-related deadlocks).
- [x] Result: REST `/tick` and WebSocket ticks share an engine-scoped async lock chained to the sync lock via `manager.run_tick()`, so a REST caller and a WS client on the same run cannot re-enter `engine.tick()`.
- [x] Notes: Did not add a two-client race regression test — starlette `TestClient` runs a single loop and would not exercise true parallelism. A true race test would need two separate event loops or threads; deferred.

---

## C-3 — Unchecked `json.loads` on WebSocket input

- **Location:** [gui/backend/api/routes/websocket.py:50](../gui/backend/api/routes/websocket.py#L50), [gui/backend/api/routes/websocket.py:61](../gui/backend/api/routes/websocket.py#L61)
- **Category:** Error Handling / Robustness

### Details
Client frames are parsed with bare `json.loads(data)` and only caught by an outer `except Exception`. On malformed input the handler attempts to send an error message over a possibly-broken socket, which can raise a secondary exception that is silently swallowed or kills the connection mid-auto-run.

### Actions
1. Wrap each `json.loads` in its own `try/except json.JSONDecodeError`.
2. Log the raw frame at `warning` level (truncated, PII-safe).
3. Respond with a structured `{"type":"error","code":"invalid_json"}` and continue the recv loop instead of aborting.

### Impact
Malformed frames (from a buggy client, mid-stream network corruption, or a fuzzer) can drop an entire session — potentially during a long simulation run, losing client-visible state.

### Post-Fix Verification
- [x] Changes: [websocket.py:_parse_command](../gui/backend/api/routes/websocket.py) new helper that catches `json.JSONDecodeError`, logs the offending frame (truncated), and returns `None`; loops in the main handler call `_safe_send_error(ws, "invalid_json")` and `continue` on parse failure. Unknown commands now also return `{"type":"error","code":"unknown_command"}`.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_websocket_malformed_json_returns_error_frame`, `test_websocket_unknown_command_returns_error` — PASS. Tests verify that after sending garbage, the socket remains open and subsequent `tick` commands still succeed.
- [x] Result: Socket is now resilient to malformed input; logs include `run_id` for debugging.
- [x] Notes: Also resolves M-4 (structured logging) — `logger.exception(...)` on unhandled errors in the receive loop.

---

# High

## H-1 — `IndexError` in CSV export when population is zero

- **Location:** [src/persistence.py:421](../src/persistence.py#L421)
- **Category:** Bug

### Details
`export_run_csv()` builds `flat_agents` then accesses `flat_agents[0]` to build header fields, with no empty-list guard. Runs that end in extinction (a common and intentional outcome of the sim) have zero agents in the final snapshot.

### Impact
Users exporting extinct runs get an `IndexError` and no CSV — exactly for the runs that are most research-interesting (sentinel purges, soul-trap collapses).

### Actions
1. Guard with `if not flat_agents: write header-only CSV and return`.
2. Derive header from a canonical `Agent` schema rather than from the first row.
3. Add a pytest case `test_export_csv_handles_extinction`.

### Post-Fix Verification
- [x] Changes: [persistence.py:export_run_csv](../src/persistence.py) now derives a `canonical_header` list, builds `flat_agents` (possibly empty), and falls back to the canonical header when no rows exist. `DictWriter(extrasaction="ignore")` prevents stray-key failures.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_csv_export_handles_extinction` — PASS. Forces all agents dead, saves a snapshot, exports CSV; asserts the header row is present and no IndexError is raised.
- [x] Result: Extinction runs now produce a header-only CSV instead of crashing.
- [x] Notes: Header is frozen to the 16 baseline fields — skill/trait/emotion/belief columns still flow through when agents exist.

---

## H-2 — Media endpoints unauthenticated and unbounded

- **Location:** [gui/backend/api/routes/media.py:14-47](../gui/backend/api/routes/media.py#L14-L47), [gui/backend/api/routes/media.py:65-105](../gui/backend/api/routes/media.py#L65-L105), [gui/backend/api/routes/media.py:123-143](../gui/backend/api/routes/media.py#L123-L143)
- **Category:** Security / Cost

### Details
Portrait, landscape, and narration endpoints call into `src/narrator.py` (and downstream HF / Ollama providers). No auth, no rate limit, no cost ceiling.

### Impact
Trivial DoS and bill-inflation vector. A single attacker can exhaust HF inference quota or fill the output directory.

### Actions
1. Add per-IP token bucket (e.g. `slowapi`) — default 10/min for media routes.
2. Require auth header when `MEDIA_AUTH_REQUIRED=1`.
3. Enforce a monthly spend cap in `narrator.py` (counter in SQLite, reject beyond limit).

### Post-Fix Verification
- [x] Changes: [auth.py](../gui/backend/api/auth.py) provides `rate_limit()` (per-IP deque token bucket) and `require_admin_if_media()` dependency. [media.py](../gui/backend/api/routes/media.py) applies `Depends(require_admin_if_media)` to the whole router and calls `rate_limit(..., 10, 60.0)` at the top of each mutation endpoint (portrait, landscape, narrate, monologue).
- [x] Tests run: `pytest tests/test_e2e_api.py::test_media_narrate_rate_limit` — PASS. Hammers `/media/narrate` 15 times and asserts that at least one returns 429.
- [x] Result: Unauthenticated clients can make ≤10 calls/minute/IP per endpoint; `MEDIA_AUTH_REQUIRED=1` additionally requires `X-Admin-Token`. Monthly spend cap deferred (would require DB counter in narrator.py).
- [x] Notes: In-process rate limiter — sufficient for single-backend deploy, not for horizontal scale.

---

## H-3 — Hardcoded simulation tunables scattered across engine

- **Location:** [src/engine.py:290](../src/engine.py#L290), [src/engine.py:309](../src/engine.py#L309), [src/engine.py:325](../src/engine.py#L325), [src/engine.py:387-405](../src/engine.py#L387-L405), [src/engine.py:494](../src/engine.py#L494), [src/engine.py:703-704](../src/engine.py#L703-L704)
- **Category:** Maintainability / Architecture

### Details
Core knobs — cycle-reset awareness preservation (0.5 / 0.35 / 0.2), soul-trap recycling (0.4 / 0.5 / 0.7), artifact awareness multiplier (0.15), grief learning penalty (0.3) — are literal constants. Violates the project rule: "Never hardcode tunables — add to `config/default.yaml`" (CLAUDE.md).

### Impact
Researchers cannot sweep parameter space via `config/scenarios/*.yaml`. Every experiment requires a code edit + restart, which defeats the whole scenario system.

### Actions
1. Add `config/default.yaml` keys under `matrix.awareness_preservation`, `soul_trap.recycle_rates`, `world.artifact_awareness_boost`, `emotions.grief_learning_penalty`.
2. Replace inline literals with `config.get("matrix.awareness_preservation.high", 0.5)` style lookups.
3. Document in README what each new key controls.

### Post-Fix Verification
- [x] Changes: [config/default.yaml](../config/default.yaml) new sections `matrix.awareness_preservation`, `matrix.soul_trap`, `matrix.artifact_awareness_multiplier`, `emotions.grief_learning_penalty`. [engine.py:_perform_cycle_reset](../src/engine.py) and [engine.py:_apply_soul_to_newborn](../src/engine.py) now read these values via `getattr(...)` fallbacks so older scenario YAMLs keep working. Artifact-discovery (line 494 region) and grief-learning penalty (line 704 region) also read from config.
- [x] Tests run: Full suite of 495 pre-existing tests covering cycle reset and soul recycling remains green under the new keys; defaults preserve prior literal behavior.
- [x] Result: All six literals identified in the review are now config-driven with defaults matching the pre-refactor numbers. Researchers can override them via `config/scenarios/*.yaml`.
- [x] Notes: README documentation of new keys is out of scope for this fix pass — deferred.

---

## H-4 — No schema validation on persisted agent JSON

- **Location:** [src/persistence.py:163](../src/persistence.py#L163), [src/persistence.py:389-446](../src/persistence.py#L389-L446)
- **Category:** Security / Robustness

### Details
`Agent.from_dict()` consumes deserialized JSON without validating shape, types, or field bounds. A corrupted snapshot (disk bit-rot, interrupted write, older schema version) raises a bare `KeyError`/`TypeError` deep in reconstruction.

### Impact
Snapshot loads crash the whole run instead of degrading gracefully. No forward/backward compat story for schema changes between versions.

### Actions
1. Introduce a dataclass or `pydantic` validator wrapping `Agent.from_dict`.
2. On validation failure, log+skip the offending agent (keep the run) rather than hard-fail.
3. Add a `schema_version` field to snapshots for future migrations.

### Post-Fix Verification
- [x] Changes: [persistence.py:load_latest_snapshot](../src/persistence.py) now iterates raw agent dicts, skips any entry that isn't a dict or lacks `id`, and wraps `Agent.from_dict(d)` in a `try/except (KeyError, TypeError, ValueError)` that logs and drops corrupt rows. Import of `logging` added at top of file.
- [x] Tests run: Full suite — PASS. Snapshot load path exercised by `test_create_and_fetch_simulation`, `test_advance_ticks_and_history`.
- [x] Result: Corrupted or schema-drifted snapshots now degrade gracefully — the run loads with fewer agents and a warning log — instead of raising.
- [x] Notes: Pydantic-style strict schema + `schema_version` field deferred; the current fix is the cheap-and-correct version.

---

## H-5 — Missing `getattr` defaults in agent summary serializer

- **Location:** [gui/backend/api/routes/simulation.py:154-178](../gui/backend/api/routes/simulation.py#L154-L178)
- **Category:** Correctness

### Details
`_agent_summary()` reads `a.dominant_emotion`, `a.trauma`, etc. directly. Agents loaded from pre-Phase-6 snapshots won't have these fields and will raise `AttributeError`.

### Impact
The `/state` endpoint 500s whenever a historical snapshot is loaded, breaking replay of earlier runs.

### Actions
1. Replace direct attribute reads with `getattr(a, "dominant_emotion", "neutral")`.
2. Add a migration helper in `persistence.py` that backfills defaults at load time.
3. Regression test with a fixture snapshot from an older schema.

### Post-Fix Verification
- [x] Changes: [simulation.py:_agent_summary](../gui/backend/api/routes/simulation.py) now reads every field via `getattr(a, "name", default)` so agents loaded from old snapshots (missing `trauma`, `dominant_emotion`, `protagonist_name`, etc.) serialize cleanly.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_state_endpoint_returns_full_snapshot` — PASS. Full suite of 495 still green.
- [x] Result: `/state` tolerates agents without Phase 6/7 fields.
- [x] Notes: Combined with H-4's snapshot skip-on-corrupt path, the API is now robust against schema drift in both directions.

---

# Medium

## M-1 — CORS allows `*` with no prod guard

- **Location:** [gui/backend/api/main.py:24-31](../gui/backend/api/main.py#L24-L31)
- **Category:** Security

### Details
`allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. Acceptable for localhost dev, dangerous if the same image is ever deployed.

### Impact
CSRF and unauthorized cross-origin access from any browser tab once the API is internet-reachable.

### Actions
1. Read allowed origins from `CORS_ORIGINS` env var, default `["http://localhost:5173"]`.
2. Fail startup if `ENV=production` and origins contain `*`.

### Post-Fix Verification
- [x] Changes: [main.py:30-45](../gui/backend/api/main.py#L30-L45) reads `CORS_ORIGINS` from env (comma-separated), defaults to the three local dev hosts. If `ENV=production` and `*` appears in the list, startup raises `RuntimeError`. `allow_methods`/`allow_headers` now enumerate the exact verbs/headers used instead of `*`.
- [x] Tests run: All 19 E2E tests still pass, which exercise the CORS middleware path implicitly via TestClient.
- [x] Result: Default behavior unchanged for local dev; prod wildcard is a hard startup failure.
- [x] Notes: `Accept` and `X-Admin-Token` headers are explicitly allowed so the frontend can still authenticate to god-mode endpoints.

---

## M-2 — `update_config` mutates engine mid-run without re-initialization

- **Location:** [gui/backend/api/routes/simulation.py:135-151](../gui/backend/api/routes/simulation.py#L135-L151)
- **Category:** Correctness

### Details
Endpoint shallow-merges new config into `engine.cfg`. Derived state (population floor, phase thresholds, tech tree gating) is computed once at engine construction and is not recomputed on update.

### Impact
Sliders appear to work but leave the engine in a half-updated state. Bugs here will look like non-reproducible "why didn't my tweak take effect" reports.

### Actions
1. Add an `engine.reconfigure(new_cfg)` method that explicitly re-derives cached state.
2. OR: restrict `update_config` to a whitelist of keys known to be safe to mutate at any tick (narration cadence, log verbosity, cinematic toggles).

### Post-Fix Verification
- [x] Changes: [simulation.py:RUNTIME_CONFIG_WHITELIST](../gui/backend/api/routes/simulation.py) lists the eight sections safe to mutate mid-run (narrator, emotions, beliefs, environment, matrix, dreams, observer_effect, archaeology). `update_config` now returns 400 with a helpful `detail` for any key outside the whitelist, and includes `updated_sections` in the success response.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_config_slider_allowed_sections`, `test_config_slider_rejects_non_whitelisted` — both PASS.
- [x] Result: Attempts to mutate `population.max_size` now return 400 with an explicit list of disallowed keys.
- [x] Notes: A proper `engine.reconfigure()` that re-derives cached state is still the ideal solution; the whitelist is the pragmatic bridge.

---

## M-3 — No rate limiting on god-mode spawn

- **Location:** [gui/backend/api/routes/god_mode.py:43-53](../gui/backend/api/routes/god_mode.py#L43-L53)
- **Category:** Availability

### Details
`spawn_n` caps at 50 per request but has no cross-request limit. A loop calling it spawns thousands of agents in seconds.

### Impact
OOM on the backend, runaway tick times. (Partially mitigated once C-1 lands, but still worth its own cap.)

### Actions
1. Add a global cap: reject spawn requests once `len(agents) > config.population.hard_cap`.
2. Per-IP token bucket (shared with H-2 solution).

### Post-Fix Verification
- [x] Changes: [god_mode.py:26](../gui/backend/api/routes/god_mode.py#L26) defines `POPULATION_HARD_CAP = 2000`. `spawn` returns 429 once `len(engine.agents) >= POPULATION_HARD_CAP`; `spawn_n` clamps the requested count to `POPULATION_HARD_CAP - len(engine.agents)` and returns 429 if zero. Additionally, every god-mode request passes through `rate_limit(..., 60 calls / 60s)` from auth.py.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_god_mode_spawn_n_clamped_below_cap` — PASS (requests 500, clamped to ≤50). `test_god_mode_spawn_with_valid_token` — PASS.
- [x] Result: Runaway spawn is now bounded by both the 50-per-call soft cap, the 2000 hard population cap, and the 60-call/min rate limiter.
- [x] Notes: The hard cap intentionally uses `len(engine.agents)` rather than alive count to prevent spam accumulating dead-agent memory pressure.

---

## M-4 — Silent error recovery in WebSocket receive loop

- **Location:** [gui/backend/api/routes/websocket.py:85-90](../gui/backend/api/routes/websocket.py#L85-L90)
- **Category:** Observability

### Details
The outer `except Exception` catches everything, tries to send an error frame, and continues. No structured logging, no counter, no telemetry.

### Impact
Impossible to diagnose client bugs or mid-stream corruption from production logs.

### Actions
1. Log with `logger.exception(...)` including `run_id` and frame type.
2. Increment a `websocket_errors_total` counter (prom or in-memory).

### Post-Fix Verification
- [x] Changes: [websocket.py](../gui/backend/api/routes/websocket.py) now owns a module-level `logger = logging.getLogger("nexus.websocket")`. `WebSocketDisconnect` logs at `info`, unhandled exceptions use `logger.exception(...)` with `run_id` context, and `_parse_command` logs malformed frames at `warning` with a 200-char truncated preview. `_safe_send_error(ws, code, detail)` centralizes best-effort error frame emission.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_websocket_malformed_json_returns_error_frame` — PASS (verified log output in captured stderr).
- [x] Result: Every error path now produces a structured log line with `run_id`, making production debugging tractable.
- [x] Notes: Metric counter deferred — a follow-up can wire this into Prometheus once the metrics endpoint exists.

---

## M-5 — Fragile early-return invariant in population summary

- **Location:** [src/engine.py:1348-1405](../src/engine.py#L1348-L1405)
- **Category:** Correctness (latent)

### Details
The "only sentinels alive" case is handled by a single early return. Below that, `max(a.generation for a in non_sentinels)` and division by `n` assume non-emptiness. Any future refactor that tweaks the early return will silently reintroduce a crash.

### Impact
Currently safe, but one sloppy edit from a regression.

### Actions
1. Add `assert non_sentinels, "population summary unreachable with empty list"` immediately after the guard.
2. Convert the ad-hoc guard into a helper `_empty_population_summary()` so the invariant is named.

### Post-Fix Verification
- [x] Changes: [engine.py:get_population_summary](../src/engine.py) now asserts `n > 0` immediately after computing `len(non_sentinels)` in the main branch, with a comment explaining the dependency on the early-return guard. A future edit that accidentally removes the early return will fail-fast instead of silently dividing by zero.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_extinction_population_summary` — PASS (forces extinction via god-mode kill, asserts `/state.summary.alive == 0`).
- [x] Result: Population summary is now documented-safe; extinction handling unchanged.
- [x] Notes: Left as an assertion rather than a named helper because the early-return block is short and visible; a helper would add indirection.

---

# Low

## L-1 — No unit tests for knowledge, mate_selection, social, portrait

- **Location:** [src/knowledge.py](../src/knowledge.py), [src/mate_selection.py](../src/mate_selection.py), [src/social.py](../src/social.py), [src/portrait.py](../src/portrait.py)
- **Category:** Testing

### Details
Four systems have no dedicated `tests/test_*.py` file. They're covered only transitively via engine integration tests.

### Impact
Regressions here are detected late, often via behavioral drift in long simulation runs rather than clean CI failures.

### Actions
1. Add `tests/test_knowledge.py`, `tests/test_mate_selection.py`, `tests/test_social.py`, `tests/test_portrait.py` (mock LLM).
2. Target ≥70% branch coverage per module.

### Post-Fix Verification
- [ ] Commit: _TBD_
- [ ] Tests run: _TBD_
- [ ] Result: _TBD_
- [ ] Notes: _TBD_

---

## L-2 — Hardcoded 4700ms animation timeout in frontend store

- **Location:** [gui/frontend/src/lib/stores/simulation.ts:95](../gui/frontend/src/lib/stores/simulation.ts#L95)
- **Category:** Maintainability

### Details
`triggerCycleResetAnimation` uses a literal `4700` to match the backend cycle-reset cinematic. Any backend tweak desyncs silently.

### Actions
1. Either emit `cinematic_duration_ms` in the backend's cycle-reset WS frame and let the frontend use it, or expose a shared `CINEMATIC_DURATIONS` constants file.

### Post-Fix Verification
- [ ] Commit: _TBD_
- [ ] Tests run: _TBD_
- [ ] Result: _TBD_
- [ ] Notes: _TBD_

---

## L-3 — No audit log for god-mode actions ✅ (bundled with C-1)

- **Location:** [gui/backend/api/routes/god_mode.py](../gui/backend/api/routes/god_mode.py)
- **Category:** Operations

### Details
God-mode mutations produce no log records.

### Actions
1. Log every action with `(timestamp, client_ip, run_id, action, payload)` to `output/audit.log`.
2. Include the log path in README under "Debugging".

### Post-Fix Verification
- [x] Changes: [god_mode.py:_audit](../gui/backend/api/routes/god_mode.py) logs every action at `warning` level via `logging.getLogger("nexus.god_mode")` including `action`, `run_id`, client IP, and payload. Called unconditionally at the top of the `god_mode` handler.
- [x] Tests run: `pytest tests/test_e2e_api.py::test_god_mode_meteor_and_event` — PASS with audit lines visible in captured log output.
- [x] Result: Every god-mode mutation now produces a structured log line. Routing to `output/audit.log` (separate handler) is deferred — current lines flow through the standard logger config.
- [x] Notes: Bundled with the C-1 fix since auth + audit shared the same code path.

---

## L-4 — `Date.now()` used for animation timing

- **Location:** [gui/frontend/src/lib/stores/simulation.ts:90-96](../gui/frontend/src/lib/stores/simulation.ts#L90-L96)
- **Category:** Correctness (edge)

### Details
`Date.now()` is wall-clock and susceptible to NTP jumps / manual clock changes. The polling check `started_at + 4500 <= Date.now()` can hang if the clock jumps backward.

### Actions
1. Replace with `performance.now()` for all relative-time logic.

### Post-Fix Verification
- [ ] Commit: _TBD_
- [ ] Tests run: _TBD_
- [ ] Result: _TBD_
- [ ] Notes: _TBD_

---

## L-5 — Uncommitted changes review

- **Files:** [gui/backend/api/routes/world.py](../gui/backend/api/routes/world.py), [gui/frontend/src/lib/stores/simulation.ts](../gui/frontend/src/lib/stores/simulation.ts), [tests/test_websocket_data.py](../tests/test_websocket_data.py)
- **Category:** Review

### Details
- `world.py`: adds `has_artifact` / `artifact_count` to the cell payload. Safe, minimal, correct.
- `simulation.ts`: adds `DemiurgeMood` type and the cycle-reset animation store. Fine apart from L-2 / L-4 above.
- `test_websocket_data.py`: adds `test_world_route_exposes_artifact_flag`. Good coverage of the new field.

### Impact
Uncommitted diff is net-positive. No blockers — just inherit the L-2 / L-4 follow-ups.

### Actions
1. Commit once L-2 is decided (inline constant vs. backend-provided duration).

### Post-Fix Verification
- [ ] Commit: _TBD_
- [ ] Tests run: _TBD_
- [ ] Result: _TBD_
- [ ] Notes: _TBD_

---

## Suggested remediation order

1. **C-1** (god-mode auth) — blocks any non-localhost deployment.
2. **C-3** (WS JSON handling) — cheap, big robustness win.
3. **H-1** (CSV IndexError) — small diff, fixes a user-visible crash.
4. **C-2** (tick-loop race) — larger change, schedule after C-1/C-3.
5. **H-2 / H-3 / H-4 / H-5** — can be parallelized across contributors.
6. Mediums and lows — backlog.

## Remediation outcome (2026-04-14)

All Critical, High, and Medium findings (13 total) have been addressed in a single fix pass. Files touched:

- **New:** [gui/backend/api/auth.py](../gui/backend/api/auth.py), [tests/test_e2e_api.py](../tests/test_e2e_api.py)
- **Modified:**
  - [gui/backend/api/main.py](../gui/backend/api/main.py) — CORS env + god-mode gate (M-1, C-1)
  - [gui/backend/api/state.py](../gui/backend/api/state.py) — per-run sync/async locks (C-2)
  - [gui/backend/api/routes/websocket.py](../gui/backend/api/routes/websocket.py) — JSON parse hardening + logging + lock (C-2, C-3, M-4)
  - [gui/backend/api/routes/god_mode.py](../gui/backend/api/routes/god_mode.py) — auth dep + audit + hard cap (C-1, M-3, L-3)
  - [gui/backend/api/routes/media.py](../gui/backend/api/routes/media.py) — rate limit + optional auth (H-2)
  - [gui/backend/api/routes/simulation.py](../gui/backend/api/routes/simulation.py) — whitelist + getattr defaults (M-2, H-5)
  - [src/persistence.py](../src/persistence.py) — CSV extinction guard + snapshot schema validation (H-1, H-4)
  - [src/engine.py](../src/engine.py) — tunables → config + population summary assert (H-3, M-5)
  - [config/default.yaml](../config/default.yaml) — new tunable sections (H-3)
  - [tests/test_websocket_data.py](../tests/test_websocket_data.py) — pre-existing Artifact kwargs bug repaired

Five Low findings remain on the backlog (L-1 through L-5, minus L-3 which was bundled with C-1).
