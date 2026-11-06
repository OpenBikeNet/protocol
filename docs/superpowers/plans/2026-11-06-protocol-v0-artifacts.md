# Protocol v0 Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the machine-readable parts of the v0 spec to the protocol repo: JSON Schemas, the `velodrome-250` route, example messages, `apps.md`, and CI that checks them.

**Architecture:** Schemas in `schemas/`, the route in `routes/`, examples in `examples/`. One Python script `tools/validate.py` checks everything and is the single CI step. The examples are the shared test data: the reference server's tests read them through a git submodule.

**Tech Stack:** JSON Schema draft 2020-12, Python 3 with `jsonschema` (pinned in `tools/requirements.txt`), GitHub Actions.

**Spec:** `spec/v0.md` (branch `spec-v0-draft`). Server design: `server/docs/design.md`.

## Global Constraints

- Work on the branch `spec-v0-draft`. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push.
- Schemas use `"$schema": "https://json-schema.org/draft/2020-12/schema"`, with `"$id"` set to `https://github.com/OpenBikeNet/protocol/schemas/<file>`.
- **Unknown fields are allowed everywhere** (spec 3.2): never set `additionalProperties: false`.
- Formats, copied from the spec: app ID `^[a-z0-9][a-z0-9-]{1,31}$`, route ID `^[a-z0-9][a-z0-9-]{1,63}$`, room `^[a-z0-9][a-z0-9-]{0,31}$`, `ref` at most 64 characters, `rider` 1 to 64 characters, `name` 1 to 32 characters with no control characters (in the schema file: `"pattern": "^[^\\u0000-\\u001f\\u007f]+$"`), `app.version` 1 to 32 characters, `app.name` up to 32, `app.url` up to 200, server rider ID and connection ID up to 16 characters.
- Value ranges (spec 6.4): `lap` integer ≥ 0, `distance` number ≥ 0 (the upper bound depends on the route, so the schema can't check it), `speed` 0 to 30, `power` integer 0 to 3000, `cadence` integer 0 to 250, `heart_rate` integer 20 to 250.
- Every example JSON in the spec MUST exist as a file in `examples/` with the same content, so spec and examples can't drift.
- Licenses: the schemas, examples and tools are MIT (`LICENSE-CODE`); spec text and `apps.md` are CC BY 4.0. No license headers in files.
- Pinned CI action SHAs (same as OpenRadlr): `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`.

## Review Focus

1. **An app adds a field we don't know yet**, e.g. `hello` with `"platform": "web"`. It must still validate. Pinned by `examples/app/hello-extra-field.json` (Task 2).
2. **A loop route whose start and end elevation differ** would give a step at the start line. It must be rejected. Pinned by `tools/fixtures/invalid-routes/loop-elevation-mismatch.json` (Task 1).
3. **Route file name and `id` differ** (`routes/velodrome.json` with `id: velodrome-250`). Servers load by file, apps refer by ID. It must be rejected. Pinned by a check in `validate.py` plus the fixture `tools/fixtures/misnamed-route/velodrome.json` (Task 1).
4. **A JSON example in the spec doesn't match the file in `examples/`.** `validate.py` extracts every ```` ```json ```` block of `spec/v0.md` and checks that each object appears in `examples/` (Task 2).
5. **An `update` with a non-integer `lap` (1.5) or `power` (245.5)** must fail, not be rounded. Pinned by `examples/invalid/app/invalid_value--fractional-lap.json` (Task 2).

---

### Task 1: Route schema, velodrome route, validator and CI

**Files:**
- Create: `schemas/route.schema.json`
- Create: `routes/velodrome-250.json`
- Create: `tools/validate.py`, `tools/requirements.txt` (`jsonschema==4.23.0`)
- Create: `tools/fixtures/invalid-routes/{last-point-not-length,distances-not-increasing,first-point-not-zero,loop-elevation-mismatch,bad-id}.json`
- Create: `tools/fixtures/misnamed-route/velodrome.json`
- Create: `apps.md`
- Create: `.github/workflows/validate.yml`
- Modify: `README.md` ("What will live here" becomes a "Contents" list with links)

**Interfaces:**
- Produces: `routes/<id>.json` files (read by the server's `routes` module), and `python3 tools/validate.py`, which exits 0 when everything is valid and otherwise prints one line per problem (`<path>: <reason>`) and exits 1. Task 2 adds checks to it.

- [ ] **Step 1: Write the invalid route fixtures**

Each fixture is a velodrome-like route with exactly one defect:
- `last-point-not-length.json`: `length` 250, profile `[[0,0],[200,0]]`
- `distances-not-increasing.json`: profile `[[0,0],[100,0],[100,1],[250,0]]`
- `first-point-not-zero.json`: profile `[[10,0],[250,0]]`
- `loop-elevation-mismatch.json`: `loop` true, profile `[[0,0],[250,5]]`
- `bad-id.json`: `id` `"Velodrome_250"`

Plus `tools/fixtures/misnamed-route/velodrome.json`: a valid route with `id` `velodrome-250`.

- [ ] **Step 2: Write `tools/validate.py` with the route checks**

`check_route(path: Path, route: dict) -> list[str]` returns the problems:
- schema errors from `route.schema.json`,
- first distance ≠ 0, last distance ≠ `length`, distances not strictly increasing, and on a loop, first elevation ≠ last elevation,
- the file name stem ≠ `id`.

`main()` runs `check_route` on every file in `routes/`, plus a duplicate-ID check. It then asserts that every file in `tools/fixtures/invalid-routes/` and `tools/fixtures/misnamed-route/` gives **at least one** problem, and reports `"<path>: expected invalid, but passed"` if one doesn't. Use `jsonschema.Draft202012Validator`. Paths are relative to the repo root, found via `Path(__file__).resolve().parent.parent`.

- [ ] **Step 3: Run the validator before the schema and route exist**

Run: `python3 tools/validate.py`
Expected: exit 1, and it says the route schema is missing. It does not crash with a traceback.

- [ ] **Step 4: Write `schemas/route.schema.json` and `routes/velodrome-250.json`**

Schema: required `id` (pattern), `name` (string, 1 to 64 characters), `length` (number, `exclusiveMinimum: 0`), `loop` (boolean), `profile` (array, `minItems` 2, items are arrays of exactly 2 numbers). The route file is the one in spec 4.1, verbatim.

- [ ] **Step 5: Run the validator**

Run: `python3 tools/validate.py`
Expected: exit 0, no output. Then temporarily set `"loop": false` in `tools/fixtures/invalid-routes/loop-elevation-mismatch.json`, and expect exit 1 with `expected invalid, but passed`. Restore the file.

- [ ] **Step 6: Write `apps.md`, `README.md` and the CI workflow**

`apps.md`: one paragraph saying the list is optional and only for discovery, that servers don't check it (spec 5), and that you add your app by PR. Then a table `| App ID | App | Website | Contact |` with one row: `openradlr | OpenRadlr | https://openradlr.com | GitHub @RalfLeonFasler`.

`README.md`: replace the "What will live here" section with "Contents": links to `spec/v0.md`, `routes/`, `schemas/`, `examples/`, `apps.md`, and the line "Run `python3 tools/validate.py` to check routes, schemas and examples." Keep the rest unchanged.

`.github/workflows/validate.yml`: runs on `push` to main and on `pull_request`, with `permissions: contents: read`. One job on `ubuntu-latest`: checkout (pinned SHA), `python3 -m venv .venv`, `.venv/bin/pip install -r tools/requirements.txt`, `.venv/bin/python tools/validate.py`.

- [ ] **Step 7: Commit**

```bash
git add schemas routes tools apps.md README.md .github
git commit -m "Add route schema, velodrome-250 route and validation"
```

### Task 2: Message and stats schemas with examples

**Files:**
- Create: `schemas/app-message.schema.json`, `schemas/server-message.schema.json`, `schemas/stats.schema.json`
- Create: `examples/app/{hello,hello-extra-field,subscribe,unsubscribe,join,update,leave}.json`
- Create: `examples/server/{welcome,snapshot,joined,updated,left,error}.json`
- Create: `examples/stats.json`
- Create: `examples/invalid/app/<code>--<description>.json` (list in Step 1)
- Modify: `tools/validate.py`

**Interfaces:**
- Consumes: `tools/validate.py` from Task 1.
- Produces: `examples/app/*.json` (valid messages from apps) and `examples/invalid/app/<code>--<description>.json`, where the part before `--` is the exact error code a server MUST answer with. The server's protocol tests rely on this naming.

- [ ] **Step 1: Write the examples**

`examples/app/*`, `examples/server/*` and `examples/stats.json` are the spec's JSON blocks, verbatim (spec 6.1–7.6 and 8). The two objects in the spec 6.2 block become `subscribe.json` and `unsubscribe.json`. `hello-extra-field.json` is `hello.json` with `"platform": "web"` added.

`examples/invalid/app/` (each with one defect, otherwise like the valid example):
- `invalid_app_id--uppercase.json`: hello with `app.id` `"OpenRadlr"`
- `invalid_message--hello-without-version.json`
- `invalid_message--missing-type.json`: `{"route": "velodrome-250"}`
- `unknown_type--ride.json`: `{"type": "ride"}`
- `invalid_room--uppercase.json`: subscribe with room `"Public"`
- `invalid_value--speed-too-high.json`: update with one rider, speed 45
- `invalid_value--negative-lap.json`: update with one rider, lap −1
- `invalid_value--fractional-lap.json`: update with one rider, lap 1.5
- `invalid_value--name-too-long.json`: join with a 33-character name

- [ ] **Step 2: Extend `tools/validate.py` and run it before the schemas exist**

Add these checks:
- `examples/app/*` are valid against `app-message.schema.json`, and `examples/server/*` against `server-message.schema.json`.
- `examples/stats.json` is valid against `stats.schema.json`.
- Every file in `examples/invalid/app/` is **invalid** against `app-message.schema.json`, and its code prefix is one of the 14 codes in spec 7.6.
- Every ```` ```json ```` block in `spec/v0.md` is read as JSON (a block may hold several objects, one per line or spread over lines; use `json.JSONDecoder.raw_decode` in a loop). Each object must equal (`==` after parsing) the content of some file under `examples/` or `routes/`.

Run: `python3 tools/validate.py`
Expected: exit 1, saying the message schemas are missing.

- [ ] **Step 3: Write the three schemas**

`app-message.schema.json`: `$defs` for `riderState` (the ranges from Global Constraints; `lap`, `distance`, `speed` required) and `ref`. The top level is a `oneOf` with one branch per `type` (`const`), so an unknown `type` matches no branch. Branches:
- `hello`: required `app`, with required `id` and `version`
- `subscribe` / `unsubscribe`: required `route`; optional `room`
- `join`: required `rider`, `route`, `name`, plus the state; optional `room`
- `update`: required `riders`, an array of objects with `rider` plus the state
- `leave`: required `rider`

`server-message.schema.json`: `welcome`, `snapshot`, `joined`, `updated`, `left`, `error` as in spec 7. `left.reason` is an enum of `leave`, `timeout`, `disconnect`, and `error.code` is an enum of the 14 codes. A rider view is `id` + `app` + `name` + the state, and an updated entry is `id` + the state. `welcome.limits` requires all five limits as integers ≥ 1.

`stats.schema.json`: `apps` is an array of objects with all seven fields from spec 8. Dates use the pattern `^\d{4}-\d{2}-\d{2}$`.

- [ ] **Step 4: Run the validator**

Run: `python3 tools/validate.py`
Expected: exit 0. Then temporarily change `"speed": 11.8` to `"speed": 12` in `examples/app/update.json`, and expect exit 1 with a spec-mismatch line for that block. Restore the file.

- [ ] **Step 5: Commit**

```bash
git add schemas examples tools
git commit -m "Add message and stats schemas with examples"
```
