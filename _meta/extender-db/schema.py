"""Create/update the extender-db collections in PocketBase (idempotent).

Run after `pocketbase serve` is up and the superuser exists:
    python3 _meta/extender-db/schema.py

Collections (see README.md for the full data model):
    frameworks, framework_elements        - mental models used to compose/evaluate
    extenders, files                      - the extender registry + file inventory
    distributions                         - bundle/plugin/standalone packaging
    frontmatter_dimensions                - per-kind frontmatter key catalog
    eval_runs, eval_responses             - evaluation provenance: campaigns, prompts,
                                            raw agent responses
    assessments                           - extender x framework-element verdicts,
                                            linked to their eval_run
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
                    ["archetype", "section", "component", "principle", "rule", "dimension"],
                    required=True,
                ),
                text("description"),
                text("criteria"),
                num("sort_order"),
                *stamps(),
            ],
            "indexes": [
                "CREATE UNIQUE INDEX idx_fw_elements ON framework_elements (framework, slug)"
            ],
        },
        {
            "name": "extenders",
            "type": "base",
            "fields": [
                text("slug", required=True),
                text("name"),
                select("kind", EXTENDER_KINDS, required=True),
                text("description"),
                select("origin", ["authored", "sourced", "external"]),
                text("upstream"),
                text("upstream_ref"),
                text("repo_path"),
                select("shelf", ["core", "toggle"]),
                select(
                    "disposition",
                    ["qualified", "grandfathered-pending-use", "demoted", "untriaged"],
                ),
                js("requires"),
                js("frontmatter"),
                text("body", max_len=2000000),
                text("entry_file"),
                num("file_count"),
                num("total_bytes"),
                num("word_count"),
                text("notes"),
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
    ]


def main():
    pb = PB()
    ids = {}
    # Two passes: relation fields need target collection ids, and the graph has no cycles
    # in creation order (frameworks -> extenders -> the rest), so a single ordered pass
    # with a growing `ids` map suffices; specs are re-derived each iteration.
    order = [
        "frameworks",
        "extenders",
        "framework_elements",
        "files",
        "distributions",
        "frontmatter_dimensions",
        "eval_runs",
        "eval_responses",
        "assessments",
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
            by_name = {f["name"]: f for f in existing["fields"]}
            for f in spec["fields"]:
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
