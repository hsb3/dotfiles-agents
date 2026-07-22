# _meta/reference — secret-free durable runbooks & how-to

Durable, settled reference for working *on this repo* — runbooks and how-to notes whose
audience is this desk (machine-specific operational detail), kept free of secrets.

This slot fills a gap in the repo-meta-structure taxonomy (#149). What belongs here vs. the
neighbouring desk dirs:

| Dir | Holds | Not this |
|---|---|---|
| `reference/` (here) | Secret-free durable runbooks / how-to; settled, undated | — |
| `operations/` | Runbooks **with secrets**, live URLs, credentials — untracked | keep secrets out of here |
| `research/` | Live investigations; findings graduate out | not settled reference |
| `briefings/` | Dated readouts (`yyyy-mm-dd-subject/`) | not undated reference |
| `docs/` (repo root) | Audience-facing durable docs | not machine-specific ops detail |

Declared in [`../mise-en-place.yml`](../mise-en-place.yml) `required_folders` until the
shared `repo-meta-structure` standard grows a universal `reference/` slot.
