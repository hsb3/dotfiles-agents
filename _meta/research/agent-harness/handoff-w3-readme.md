# Wave-3 handoff — readme-value-and-proof case authoring

_Agent-harness build (`feat/agent-harness`), Wave 3 (battle-test cases). Candidate:
`primitives-core/skills/readme-value-and-proof/SKILL.md`. Scope: `harness/cases/readme-value-and-proof/**`
and this file only._

Status: delivered — 1 case authored (`local-bookmark-vault`), self-verified with no live agent runs
per the brief. `check.py` behaves correctly against both a passing and a failing mock workspace
(pasted below); the case loads cleanly via `agent_harness.cases.load_cases`.

---

## 1 · Why one case, not two

The brief allowed 1–2. I built one case that exercises the skill's **full doctrine** (both Part A
value-prop/honesty and Part B visual-proof) end-to-end against a real, working fixture, rather than
splitting into two thinner cases. Reasoning: the skill's "proof" concept is specifically visual
(screenshots of a running app — SKILL.md L48 "Part B — visual proof (screenshots from the running
app)"), not test-suite output in general. A second case without a UI to screenshot would have made
Part B vacuous for that case (nothing to screenshot ⇒ baseline and skill-following runs would look
identical on that axis), which would weaken traceability rather than add coverage. One well-built
case with a real UI, a real test suite, and a real server tests every doctrine line I could find
concrete evidence for. A second case (e.g. sharpening the hype-language ban on a project tempting an
LLM toward "blazing fast" claims) is a reasonable follow-up but was deferred to keep this slice
tight and fully self-verified. Flagging as deferred, not silently dropped.

## 2 · The case

`harness/cases/readme-value-and-proof/local-bookmark-vault/`:

```
case.json
check.py
fixture/
  Makefile              # `make test`, `make serve` — both real, both verified working
  server.py             # stdlib-only http.server REST API (no deps)
  lib.py                # pure functions (validate_bookmark, next_id, filter_by_tag, remove_by_id)
  bookmarks.json         # seed data, 2 bookmarks (non-empty state to screenshot)
  static/{index.html,app.js,style.css}   # vanilla-JS frontend, no build step
  tests/test_lib.py      # 9 unittest cases, all passing (verified below)
```

Fixture = "Local Bookmark Vault": a small, real, self-hosted bookmark manager (add/list/filter/
delete via a REST API, a tiny frontend). No README.md present. Genuine value to articulate (why a
zero-dependency local bookmark manager vs. a browser-account-locked one) and genuine proof available
(a passing unit-test suite via `make test`, and a live app via `make serve` that can be screenshotted
in a populated state).

**Prompt** (`case.json`): "This project (Local Bookmark Vault, a small self-hosted bookmark
manager) doesn't have a README yet. Write one. Explain what it is and why someone would want it, and
back up your claims with real proof that it works — not just an assertion. Feel free to run the test
suite (`make test`) and start the app (`make serve`) to check it actually works before you write
anything." Realistic, open-ended, does not spell out "screenshot" or "honesty" or "roadmap" —
those come only from the skill. A baseline agent (no skill loaded) plausibly produces a generic
templated README (Features/Installation/Usage/License, no gaps section, no roadmap, no screenshot,
and — commonly for toy/demo projects — reflexive hype language like "production-ready" or "blazing
fast"). My `ws-fail` mock below is exactly that shape and fails 3 of 4 deterministic checks.

## 3 · Skill-rule → assertion/check mapping (with line citations)

Skill source: `primitives-core/skills/readme-value-and-proof/SKILL.md` (as read this session).

| Skill rule | Line(s) | Encoded as |
|---|---|---|
| "Avoid 'production-ready', 'seamless', 'blazing-fast', 'MISSION ACCOMPLISHED', and similar" | L20–21 | `check.py` **c3** (deterministic, exact banned-phrase regex match, case-insensitive) |
| "Why this exists — the problem/motivation in a few sentences" | L38–39 | assertion **a1-why-this-exists** (LLM-graded: needs judgment on whether a section is genuinely motivational vs. a feature list) |
| "...and a plain 'what it is not (yet)' paragraph (gaps, untested areas, who it's not for)" | L41 (also L19–20: "State what's near-turnkey AND what it is *not* yet") | assertion **a2-honest-gap-statement** (LLM-graded: needs judgment on whether the gap is concrete, not boilerplate) |
| "Roadmap — planned enhancements as bullets" | L42–43 | assertion **a3-roadmap-as-bullets** (LLM-graded: needs judgment on list vs. prose) |
| "Save committed to `docs/images/`..., reference with `![alt](docs/images/x.png)`, and verify every ref resolves" | L87–89 | `check.py` **c4** (deterministic: any local image ref resolves to a real file) supporting assertion **a4-real-screenshot-of-running-app** (LLM-graded: needs to *view* the image and judge it shows the real populated UI, not a placeholder/mockup — ties to L23–27 "Proof must be real... never a mockup, never a staged/edited shot") |
| README.md must exist at all | (implicit — the skill's whole subject) | `check.py` **c1** (deterministic) |
| "back up your claims with real proof" / runnable proof | prompt-level, generalizing L28–29 "Verify before you commit. Confirm image paths resolve..." | `check.py` **c2** (deterministic: README references a command that is *actually real* against the fixture, derived by parsing the fixture's own Makefile targets + known script paths — not a hardcoded guess) |

I deliberately did **not** turn "no hype words" into an LLM assertion — it's exact-string
matchable, so it belongs in `check.py` per the brief's own guidance ("absence of specific banned
patterns IF the skill names any concrete ones — cite the line"), and duplicating it as an LLM
assertion would be redundant scoring of the same fact.

4 LLM-rubric assertions (within the brief's 2–4 range), each narrow/binary/evidence-checkable and
individually traceable to a skill line — no "README is good" vibes assertions.

## 4 · Why baseline plausibly fails

- Generic README templates (what most coding agents default to without this skill) are
  Features/Installation/Usage/License-shaped: no explicit "why this exists" narrative separate
  from the feature list (fails a1), no "what it is not yet" honesty section — generic READMEs
  assert capability, not gaps (fails a2), "Future Work" as a single unstructured sentence rather
  than a roadmap list (fails a3), and — critically — **no embedded screenshot at all**, since
  capturing one requires standing up the app and running Playwright/headless Chromium, which is
  not something a baseline README-writing pass does spontaneously (fails a4 and c4). Toy/demo
  project READMEs also commonly reach for stock hype language ("blazing fast", "production-ready")
  even when unwarranted for a single-file localhost tool (fails c3). My `ws-fail` mock below
  encodes exactly this baseline shape and independently fails c2/c3/c4.

## 5 · Verification (self-run, no live agent)

### 5a. `check.py` standalone — passing mock workspace

Built by copying `fixture/` to a scratch dir, adding a doctrine-compliant `README.md` (why-this-
exists section, explicit "what it is not (yet)" paragraph, roadmap as a checklist, `make test` +
`make serve` referenced, a real local image at `docs/images/dashboard.png` — a minimal valid 1×1
PNG, not a URL), and running `check.py` with cwd = that workspace:

```
$ (cd $SCRATCH/ws-pass && python3 check.py | python3 -m json.tool)
[
    {
        "id": "c1-readme-exists",
        "passed": true,
        "evidence": "README.md present in workspace"
    },
    {
        "id": "c2-references-real-runnable-command",
        "passed": true,
        "evidence": "README.md contains real command(s): ['make test', 'make serve']"
    },
    {
        "id": "c3-no-banned-hype-phrases",
        "passed": true,
        "evidence": "none of the skill's named hype phrases found in README.md"
    },
    {
        "id": "c4-local-image-refs-resolve",
        "passed": true,
        "evidence": "all 1 local image ref(s) resolve: ['docs/images/dashboard.png']"
    }
]
```

### 5b. `check.py` standalone — failing mock workspace

Same fixture copy, but with a generic AI-boilerplate `README.md` (hype language, no gaps section,
"Future Work" as one sentence, no image, no reference to the fixture's real commands):

```
$ (cd $SCRATCH/ws-fail && python3 check.py | python3 -m json.tool)
[
    {
        "id": "c1-readme-exists",
        "passed": true,
        "evidence": "README.md present in workspace"
    },
    {
        "id": "c2-references-real-runnable-command",
        "passed": false,
        "evidence": "README.md contains none of the fixture's real commands ['make test', 'make serve', 'python3 server.py', 'python3 -m unittest discover -s tests']"
    },
    {
        "id": "c3-no-banned-hype-phrases",
        "passed": false,
        "evidence": "found banned phrase(s): ['production-ready', 'seamless', 'blazing-fast']"
    },
    {
        "id": "c4-local-image-refs-resolve",
        "passed": false,
        "evidence": "no local (non-URL) markdown image reference found in README.md"
    }
]
```

`c1` alone can't distinguish good/bad READMEs by design (both mocks have a README.md) — that's
expected; it's a floor check, not a discriminator. c2/c3/c4 discriminate exactly as intended.

### 5c. Case loads via `agent_harness.cases.load_cases`

Read `harness/agent_harness/cases.py` for the signature (`load_cases(candidate, cases_dir,
only=None)`, minimal validation: requires `prompt`, and every assertion needs `id` + `text`).
Ran it directly against the real cases dir:

```
$ cd harness && python3 -c "
from agent_harness.cases import load_cases
cases = load_cases('readme-value-and-proof', 'cases')
for c in cases:
    print('id:', c['id'])
    print('dir:', c['dir'])
    print('prompt:', c['prompt'][:80], '...')
    print('assertions:', [a['id'] for a in c.get('assertions', [])])
"
id: local-bookmark-vault
dir: cases/readme-value-and-proof/local-bookmark-vault
prompt: This project (Local Bookmark Vault, a small self-hosted bookmark manager) doesn' ...
assertions: ['a1-why-this-exists', 'a2-honest-gap-statement', 'a3-roadmap-as-bullets', 'a4-real-screenshot-of-running-app']
```

### 5d. Fixture is a genuinely working project (not just plausible-looking)

```
$ cd fixture && python3 -m unittest discover -s tests -v
... (9 tests) ... OK
```

Also live-checked the server end-to-end in a throwaway copy (never the committed fixture — see
note below): `GET /` → 200, `GET /api/bookmarks` → seed data, `GET /api/bookmarks?tag=news` →
filtered correctly, `POST /api/bookmarks` → 201 + new record, `DELETE /api/bookmarks/1` →
`{"removed": true}`, `GET /style.css` → 200. All as expected for a real, working stdlib-only app.

**Gotcha hit and corrected during authoring:** `server.py` writes `bookmarks.json` next to itself
(the script's own directory), so my first live-server smoke test mutated the committed fixture's
seed data in place. Caught it via `git diff`-equivalent inspection, restored the original 2-entry
seed content, and redid the live check against a `cp -r` throwaway copy in scratch instead. Final
committed `fixture/bookmarks.json` is the original untouched seed (verified via a diff against the
scratch copy showing only the copy differs). Also cleaned up `__pycache__/` litter my own
`unittest` runs left inside `fixture/` and `fixture/tests/` before finishing — the committed
fixture has none.

## 6 · Deferred / out of scope

- **A second case** (e.g. hype-language pressure-test on a project name/domain that tempts an LLM
  toward "blazing fast" claims, without needing a UI) — considered, deferred per §1's reasoning.
  Not built; a future Wave-3 pass could add it under a new case-id in the same candidate directory
  without touching this one.
- **Actually running the live grid** (with/baseline × trials, real claude CLI invocation) is out of
  this brief's scope ("VERIFY YOURSELF (no live agent runs)"). Flagging one real risk for whoever
  does run it: Part B (screenshot capture) requires Playwright/Chromium reachable from inside the
  ephemeral trial workspace (per SKILL.md L59–75, `npm i -g playwright` + browser binaries). If the
  live harness environment doesn't have that available, **both** `with` and `baseline` configs will
  likely fail a4/c4 for reasons unrelated to skill-following, which would need to be called out
  explicitly in the Wave-3 report rather than read as "the skill doesn't help." This is a fixture/
  environment property, not a case-authoring defect — I did not change the fixture to avoid it,
  since dodging the UI requirement would have made the case untrue to the skill's actual doctrine
  (per the STOP condition in my brief: encode the skill's real doctrine, not generic README taste).
- No changes made to `harness/agent_harness/**`, `primitives-core/**`, other `harness/cases/**`
  directories, or `evals/**` — all read-only for this slice, as scoped.

## 7 · Files touched

- `harness/cases/readme-value-and-proof/local-bookmark-vault/case.json` (new)
- `harness/cases/readme-value-and-proof/local-bookmark-vault/check.py` (new)
- `harness/cases/readme-value-and-proof/local-bookmark-vault/fixture/**` (new — Makefile, server.py,
  lib.py, bookmarks.json, static/{index.html,app.js,style.css}, tests/test_lib.py)
- `_meta/research/agent-harness/handoff-w3-readme.md` (this file)
