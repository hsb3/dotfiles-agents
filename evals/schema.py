"""Create/update the extender-db collections in PocketBase (idempotent).

Run after `pocketbase serve` is up and the superuser exists:
    python3 evals/schema.py

Collections (see README.md for the full data model):
    frameworks, framework_elements        - mental models used to compose/evaluate
    sources                               - trusted publishers of extenders + quality signals
    extenders, files                      - the extender registry + file inventory
    distributions                         - bundle/plugin/standalone packaging
    frontmatter_dimensions                - per-kind frontmatter key catalog
    eval_runs, eval_responses             - evaluation provenance: campaigns, prompts,
                                            raw agent responses
    assessments                           - extender x framework-element verdicts,
                                            linked to their eval_run
    job_coverage                          - per-job curation: disposition, coverage
                                            status, chosen source, linked eval_run
    relationships                         - pairwise extender links: duplicative /
                                            conflicting / complementary / directional
    coverage_gaps  (view)                 - read-only saved view over job_coverage joined
                                            to its job element, non-covered rows only
                                            (status != 'covered'): gaps + partials

    harness telemetry (GH #174):
    runs                                  - one row per harness trial: ledger row (verdict +
                                            token/cost counts) fused with log provenance
    artifacts                             - content-addressed blobs (file writes,
                                            screenshots) as PB file fields, sha-deduped
    run_events                            - normalized event stream, one row per log line
    tool_calls                            - denormalized convenience, one row per tool call
"""

import sys

from pb import PB

# "plugin" covers whole-plugin externals recorded by reference (externals.yaml kind: plugin)
EXTENDER_KINDS = ["skill", "agent", "hook", "mcp", "command", "plugin"]


def text(name, required=False, max_len=0):
    # max_len 0 = PocketBase default cap (~5000 chars); large bodies need an explicit max.
    return {"name": name, "type": "text", "required": required, "max": max_len}


def num(name):
    return {"name": name, "type": "number", "required": False}


def boolean(name):
    return {"name": name, "type": "bool", "required": False}


def js(name):
    return {"name": name, "type": "json", "required": False, "maxSize": 2000000}


def select(name, values, required=False, max_select=1):
    return {
        "name": name,
        "type": "select",
        "required": required,
        "values": values,
        "maxSelect": max_select,
    }


def rel(name, collection_id, required=False, cascade=False, max_select=1):
    return {
        "name": name,
        "type": "relation",
        "required": required,
        "collectionId": collection_id,
        "cascadeDelete": cascade,
        "maxSelect": max_select,
    }


def file_field(name, max_size=10_000_000, max_select=1, mime_types=None, protected=False):
    # PocketBase file field: blob lands in pb_data/storage/<coll>/<rec>/; JSON
    # record writes can't carry it — use pb.create_multipart().
    return {"name": name, "type": "file", "required": False,
            "maxSelect": max_select, "maxSize": max_size,
            "mimeTypes": mime_types or [], "thumbs": [], "protected": protected}


def stamps():
    return [
        {"name": "created", "type": "autodate", "onCreate": True, "onUpdate": False},
        {"name": "updated", "type": "autodate", "onCreate": True, "onUpdate": True},
    ]


def collection_specs(ids):
    """Return ordered collection specs. `ids` maps already-known collection name -> id
    so relation fields can point at their targets."""
    return [
        {
            "name": "frameworks",
            "type": "base",
            "fields": [
                text("slug", required=True),
                text("name", required=True),
                text("source_org"),
                text("source_url"),
                select(
                    "kind",
                    [
                        "archetype-set",
                        "section-taxonomy",
                        "authoring-spec",
                        "schema-spec",
                        "evaluation-rubric",
                        "principles",
                        "job-taxonomy",
                        "evaluation-methodology",
                    ],
                    required=True,
                ),
                select("applies_to", EXTENDER_KINDS + ["any"], max_select=len(EXTENDER_KINDS) + 1),
                text("summary"),
                select("status", ["active", "candidate", "superseded"]),
                text("notes"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_frameworks_slug ON frameworks (slug)"
            ],
        },
        {
            "name": "framework_elements",
            "type": "base",
            "fields": [
                rel("framework", ids["frameworks"], required=True, cascade=True),
                text("slug", required=True),
                text("name", required=True),
                select(
                    "element_kind",
                    ["archetype", "section", "component", "principle", "rule", "dimension", "job"],
                    required=True,
                ),
                text("description"),
                text("criteria"),
                text("category"),
                num("sort_order"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_fw_elements ON framework_elements (framework, slug)"
            ],
        },
        {
            "name": "sources",
            "type": "base",
            "fields": [
                text("slug", required=True),
                text("name", required=True),
                text("url"),
                select(
                    "publisher_kind",
                    ["first-party", "marketplace", "individual", "research-lab",
                     "community-collection"],
                ),
                select("publishes", EXTENDER_KINDS, max_select=len(EXTENDER_KINDS)),
                select("trust_tier", ["trusted", "provisional", "watch", "avoid"]),
                boolean("publishes_evals"),
                select("maintenance", ["active", "sporadic", "dormant", "unknown"]),
                text("license"),
                text("adoption_signal"),
                text("rationale", max_len=20000),
                text("evidence_url", max_len=20000),
                select("status", ["active", "candidate", "superseded"]),
                text("notes", max_len=20000),
                *stamps(),
            ],
            "indexes": ["CREATE UNIQUE INDEX idx_sources_slug ON sources (slug)"],
        },
        {
            "name": "extenders",
            "type": "base",
            "fields": [
                text("slug", required=True),
                text("name"),
                select("kind", EXTENDER_KINDS, required=True),
                text("description"),
                select("origin", ["authored", "sourced", "external", "vendored"]),
                text("upstream"),
                text("upstream_ref"),
                text("repo_path"),
                rel("source", ids["sources"]),
                select("shelf", ["core", "toggle"]),
                select(
                    "disposition",
                    ["qualified", "grandfathered-pending-use", "demoted", "untriaged", "orphaned"],
                ),
                js("requires"),
                js("frontmatter"),
                text("body", max_len=2000000),
                text("entry_file"),
                num("file_count"),
                num("total_bytes"),
                num("word_count"),
                text("notes"),
                # Set by ingest.py when the tree stops defining the slug (row and dependents
                # retained, consumers filter on it); cleared by re-ingest.
                boolean("retired"),
                *stamps(),
            ],
            "indexes": ["CREATE UNIQUE INDEX idx_extenders_slug ON extenders (slug)"],
        },
        {
            "name": "files",
            "type": "base",
            "fields": [
                rel("extender", ids["extenders"], required=True, cascade=True),
                text("relpath", required=True),
                select(
                    "role",
                    [
                        "entrypoint",
                        "reference",
                        "script",
                        "asset",
                        "template",
                        "eval",
                        "doc",
                        "license",
                        "config",
                        "other",
                    ],
                ),
                text("content", max_len=2000000),
                boolean("is_binary"),
                num("size_bytes"),
                text("sha256"),
                text("language"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_files_ext_path ON files (extender, relpath)"
            ],
        },
        {
            "name": "distributions",
            "type": "base",
            "fields": [
                text("slug", required=True),
                select("kind", ["bundle", "plugin", "standalone"], required=True),
                text("version"),
                text("description"),
                rel("members", ids["extenders"], max_select=500),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_distributions_slug ON distributions (slug)"
            ],
        },
        {
            "name": "frontmatter_dimensions",
            "type": "base",
            "fields": [
                text("key", required=True),
                select("applies_to", EXTENDER_KINDS, required=True),
                select(
                    "requirement",
                    ["required", "optional", "harness", "custom", "deprecated"],
                ),
                text("description"),
                rel("spec_framework", ids["frameworks"]),
                num("observed_count"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_fm_dims ON frontmatter_dimensions (key, applies_to)"
            ],
        },
        {
            "name": "eval_runs",
            "type": "base",
            "fields": [
                text("slug", required=True),
                select(
                    "kind",
                    ["mechanical", "judged", "adversarial-review", "adjudication",
                     "comparative", "experiment"],
                    required=True,
                ),
                text("method", max_len=200000),
                text("criteria_text", max_len=2000000),
                rel("frameworks", ids["frameworks"], max_select=20),
                select("status", ["planned", "running", "complete", "abandoned"]),
                text("notes", max_len=200000),
                *stamps(),
            ],
            "indexes": ["CREATE UNIQUE INDEX idx_eval_runs_slug ON eval_runs (slug)"],
        },
        {
            "name": "eval_responses",
            "type": "base",
            "fields": [
                rel("run", ids["eval_runs"], required=True, cascade=True),
                text("role", required=True),
                text("agent_type"),
                text("model"),
                text("prompt", max_len=2000000),
                text("response_text", max_len=2000000),
                js("response_json"),
                rel("extenders", ids["extenders"], max_select=100),
                num("tokens"),
                num("duration_ms"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_eval_responses ON eval_responses (run, role)"
            ],
        },
        {
            "name": "assessments",
            "type": "base",
            "fields": [
                rel("extender", ids["extenders"], required=True, cascade=True),
                rel("framework", ids["frameworks"], required=True),
                rel("element", ids["framework_elements"]),
                rel("eval_run", ids["eval_runs"]),
                select(
                    "verdict",
                    ["present", "partial", "absent", "not-applicable"],
                    required=True,
                ),
                num("score"),
                text("evidence"),
                text("assessor"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_assessments ON assessments (extender, framework, element, assessor)"
            ],
        },
        {
            # Per-job curation (CHARTER decision 9): disposition + coverage status are
            # per JOB, not per (extender x job), so they live here, not on assessments.
            "name": "job_coverage",
            "type": "base",
            "fields": [
                rel("job", ids["framework_elements"], required=True),
                select("disposition", ["author", "vendor", "reference", "compare"]),
                select("status", ["covered", "partial", "gap"]),
                rel("source", ids["sources"]),
                text("rationale", max_len=10000),
                rel("eval_run", ids["eval_runs"]),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_job_coverage ON job_coverage (job)"
            ],
        },
        {
            # Pairwise extender links (CHARTER decision 10). `kind` carries symmetric
            # values plus directional ones (precedes / feeds-into, read A->B). Composite
            # unique index keeps upserts idempotent (mirrors assessments).
            "name": "relationships",
            "type": "base",
            "fields": [
                rel("extender_a", ids["extenders"], required=True),
                rel("extender_b", ids["extenders"], required=True),
                select(
                    "kind",
                    ["duplicative", "conflicting", "complementary", "precedes", "feeds-into"],
                    required=True,
                ),
                rel("job", ids["framework_elements"]),
                text("evidence", max_len=10000),
                text("assessor"),
                rel("eval_run", ids["eval_runs"]),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_relationships ON relationships (extender_a, extender_b, kind, job)"
            ],
        },
        {
            # coverage_gaps (view, GH #161): gaps + partials as a first-class saved view
            # for the admin UI and API. Read-only projection over job_coverage joined to
            # its job element, filtered to non-covered rows. A view is defined ONLY by its
            # `viewQuery`; PocketBase derives the fields from the query (no stored `fields`),
            # so there are no field ids to preserve — the merge-by-name guard in main() is a
            # no-op for it. Must sit after the tables it queries in `order`: the query
            # references the job_coverage and framework_elements tables, which must already
            # exist when the view is created (the harness-telemetry base collections that
            # follow it in `order` don't feed the view, so trailing them is safe).
            # Views need an id column, so `id` aliases job_coverage.id. Portable
            # SQLite; `job` is a single relation (maxSelect 1) stored as the related id text,
            # so `fe.id = jc.job` joins directly.
            "name": "coverage_gaps",
            "type": "view",
            "viewQuery": (
                "SELECT jc.id AS id, "
                "fe.slug AS job_slug, fe.name AS job_name, fe.category AS category, "
                "jc.status AS status, jc.disposition AS disposition, "
                "jc.rationale AS rationale, jc.updated AS updated "
                "FROM job_coverage jc "
                "JOIN framework_elements fe ON fe.id = jc.job "
                "WHERE jc.status != 'covered'"
            ),
        },
        {
            # Harness telemetry (GH #174), one row per harness trial: the ledger row
            # (candidate x case x config x trial verdict + token/cost/turn counts) fused
            # with log provenance (session_id joins log lines back to the run). Small
            # bounded strings stay text; per-row arrays/maps (checks, grades, model_usage,
            # provenance) are json. `ts` is text deliberately — ledger stamps are naive
            # local ISO with no zone, and a PB date field would coerce/shift them.
            "name": "runs",
            "type": "base",
            "fields": [
                select("harness", ["claude", "opencode"], required=True),
                select("era", ["legacy", "post", "na"]),
                text("campaign"),
                text("candidate", required=True),
                text("case", required=True),
                select("config", ["with", "baseline"]),
                text("kind"),
                num("trial"),
                text("model"),
                text("grader_model"),
                text("cli_version"),
                text("session_id"),
                boolean("passed"),
                boolean("skill_used"),
                num("exit_code"),
                num("num_turns"),
                num("cost_usd"),
                num("duration_ms"),
                num("input_tokens"),
                num("output_tokens"),
                num("cache_creation_tokens"),
                num("cache_read_tokens"),
                text("error", max_len=2000),
                text("workspace"),
                js("checks"),
                js("grades"),
                js("tool_names"),
                js("model_usage"),
                js("provenance"),
                text("log_path"),
                text("ts"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_runs_key ON runs "
                "(campaign, harness, model, candidate, `case`, config, trial)",
                # partial: empty session_ids (legacy rows) must not collide on unique
                "CREATE UNIQUE INDEX idx_runs_session ON runs (session_id) WHERE session_id != ''",
                "CREATE INDEX idx_runs_log ON runs (log_path)",
            ],
        },
        {
            # Content-addressed blobs too large for a text field (base64 screenshots
            # 24-75 KB, file writes up to ~5 KB). NO cascade and NO `event` rel: a
            # sha-deduped artifact may be referenced by many events across runs, so the
            # rel lives on the many side (run_events.artifact / tool_calls.artifact).
            # Dropping the doc's artifacts.event rel also breaks the run_events<->artifacts
            # cycle so single-pass ordered creation holds. `blob` is a file field; write
            # it via pb.create_multipart(), not a JSON record body.
            "name": "artifacts",
            "type": "base",
            "fields": [
                rel("run", ids["runs"], required=True),
                select("kind", ["write_content", "edit_diff", "screenshot", "tool_output"]),
                text("mime"),
                file_field("blob", protected=True),
                text("sha256", required=True),
                num("byte_size"),
                text("text_ref", max_len=5000),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_artifacts_sha ON artifacts (sha256)",
                "CREATE INDEX idx_artifacts_run ON artifacts (run)",
            ],
        },
        {
            # Normalized event stream: one row per raw log line minus dropped types
            # (system/thinking_tokens noise). `ts` is ms epoch (opencode native; claude
            # derived). `payload` is json so the 2 % of tool bodies over the 5000-char cap
            # fit; oversized blobs are externalized to `artifact`. Cascade on `run`.
            "name": "run_events",
            "type": "base",
            "fields": [
                rel("run", ids["runs"], required=True, cascade=True),
                num("seq"),
                num("ts"),
                select("vendor", ["claude", "opencode"]),
                select("role", ["assistant", "tool_call", "tool_result", "system", "result"]),
                text("event_type"),
                text("tool_name"),
                text("tool_call_id"),
                text("status"),
                boolean("is_error"),
                num("input_tokens"),
                num("output_tokens"),
                num("cache_read_tokens"),
                num("cache_write_tokens"),
                num("cost_usd"),
                num("wallclock_ms"),
                text("text", max_len=5000),
                js("payload"),
                rel("artifact", ids["artifacts"]),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_run_events_key ON run_events (run, seq)",
                "CREATE INDEX idx_run_events_call ON run_events (tool_call_id)",
            ],
        },
        {
            # Denormalized convenience: one row per tool call (claude call+result pair or
            # fused opencode event), so tool-level analytics don't re-parse payload. Cascade
            # on `run`. `input`/`output` are json (cap headroom); oversized output -> artifact.
            "name": "tool_calls",
            "type": "base",
            "fields": [
                rel("run", ids["runs"], required=True, cascade=True),
                text("tool_call_id", required=True),
                text("tool_name", required=True),
                js("input"),
                js("output"),
                text("status"),
                boolean("is_error"),
                num("wallclock_ms"),
                num("started_ts"),
                rel("artifact", ids["artifacts"]),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_tool_calls_key ON tool_calls (run, tool_call_id)",
                "CREATE INDEX idx_tool_calls_name ON tool_calls (tool_name)",
            ],
        },
    ]


def main():
    pb = PB()
    ids = {}
    # Two passes: relation fields need target collection ids, and the graph has no cycles
    # in creation order (frameworks -> extenders -> the rest), so a single ordered pass
    # with a growing `ids` map suffices; specs are re-derived each iteration.
    order = [
        "frameworks",
        "sources",
        "extenders",
        "framework_elements",
        "files",
        "distributions",
        "frontmatter_dimensions",
        "eval_runs",
        "eval_responses",
        "assessments",
        "job_coverage",
        "relationships",
        "coverage_gaps",
        "runs",
        "artifacts",
        "run_events",
        "tool_calls",
    ]
    for name in order:
        existing = pb.get_collection(name)
        if existing:
            ids[name] = existing["id"]
    for name in order:
        spec = next(
            s for s in collection_specs({k: ids.get(k, "") for k in order})
            if s["name"] == name
        )
        existing = pb.get_collection(name)
        if existing:
            # Merge by field name, preserving existing field ids — a field sent without
            # its id is treated as NEW by PocketBase (old column dropped = data loss).
            # View collections have no stored fields (PocketBase re-derives them from
            # viewQuery on every write), so `.get("fields", [])` makes this a no-op for
            # them while the create-vs-update-by-name flow still holds.
            by_name = {f["name"]: f for f in existing.get("fields", [])}
            for f in spec.get("fields", []):
                if f["name"] in by_name:
                    f["id"] = by_name[f["name"]]["id"]
            pb.update_collection(name, spec)
            print(f"updated  {name}")
        else:
            created = pb.create_collection(spec)
            ids[name] = created["id"]
            print(f"created  {name}")


if __name__ == "__main__":
    sys.exit(main())
