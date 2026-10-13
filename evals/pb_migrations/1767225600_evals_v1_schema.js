/// <reference path="../pb_data/types.d.ts" />
// evals v1 schema, access rules and settings (SPEC.md, Persistence and Appendix A).
//
// On an empty database this creates every collection in dependency order. On a
// database the previous tooling built through the REST API it updates each
// collection in place: existing field ids, options and select values stay, and
// only missing fields, missing select values, missing indexes, the access rules
// and the settings are added. Forward-only: the down migration does nothing.

migrate((app) => {
  const AUTH = "@request.auth.id != ''";

  const text = (name, opts) => Object.assign({ name: name, type: "text", max: 0 }, opts || {});
  const num = (name) => ({ name: name, type: "number" });
  const bool = (name) => ({ name: name, type: "bool" });
  const json = (name) => ({ name: name, type: "json", maxSize: 2000000 });
  const select = (name, values, opts) =>
    Object.assign({ name: name, type: "select", values: values, maxSelect: 1 }, opts || {});
  const rel = (name, target, opts) =>
    Object.assign({ name: name, type: "relation", target: target, maxSelect: 1, cascadeDelete: false }, opts || {});

  const KINDS = ["skill", "agent", "hook", "mcp", "command", "plugin"];

  const SCHEMA = [
    {
      name: "frameworks",
      rules: AUTH,
      fields: [
        text("slug", { required: true }),
        text("name", { required: true }),
        text("source_org"),
        text("source_url"),
        select("kind", ["archetype-set", "section-taxonomy", "authoring-spec", "schema-spec", "evaluation-rubric", "principles", "job-taxonomy", "evaluation-methodology"], { required: true }),
        select("applies_to", ["skill", "agent", "hook", "mcp", "command", "plugin", "any"], { maxSelect: 7 }),
        text("summary"),
        select("status", ["active", "candidate", "superseded"]),
        text("notes"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_frameworks_slug ON frameworks (slug)"],
    },
    {
      name: "sources",
      rules: AUTH,
      fields: [
        text("slug", { required: true }),
        text("name", { required: true }),
        text("url"),
        select("publisher_kind", ["first-party", "marketplace", "individual", "research-lab", "community-collection"]),
        select("publishes", KINDS, { maxSelect: 6 }),
        select("trust_tier", ["trusted", "provisional", "watch", "avoid"]),
        bool("publishes_evals"),
        select("maintenance", ["active", "sporadic", "dormant", "unknown"]),
        text("license"),
        text("adoption_signal"),
        text("rationale", { max: 20000 }),
        text("evidence_url", { max: 20000 }),
        select("status", ["active", "candidate", "superseded"]),
        text("notes", { max: 20000 }),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_sources_slug ON sources (slug)"],
    },
    {
      name: "extenders",
      rules: AUTH,
      fields: [
        text("slug", { required: true }),
        text("name"),
        select("kind", KINDS, { required: true }),
        text("description"),
        select("origin", ["authored", "sourced", "external", "vendored"]),
        text("upstream"),
        text("upstream_ref"),
        text("repo_path"),
        rel("source", "sources"),
        select("shelf", ["core", "toggle"]),
        select("disposition", ["qualified", "grandfathered-pending-use", "demoted", "untriaged", "orphaned"]),
        json("requires"),
        json("assumes"),
        json("frontmatter"),
        text("body", { max: 2000000 }),
        text("entry_file"),
        num("file_count"),
        num("total_bytes"),
        num("word_count"),
        text("notes"),
        bool("retired"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_extenders_slug ON extenders (slug)"],
    },
    {
      name: "framework_elements",
      rules: AUTH,
      fields: [
        rel("framework", "frameworks", { required: true, cascadeDelete: true }),
        text("slug", { required: true }),
        text("name", { required: true }),
        select("element_kind", ["archetype", "section", "component", "principle", "rule", "dimension", "job"], { required: true }),
        text("description"),
        text("criteria"),
        text("category"),
        num("sort_order"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_fw_elements ON framework_elements (framework, slug)"],
    },
    {
      name: "files",
      rules: AUTH,
      fields: [
        rel("extender", "extenders", { required: true, cascadeDelete: true }),
        text("relpath", { required: true }),
        select("role", ["entrypoint", "reference", "script", "asset", "template", "eval", "doc", "license", "config", "other"]),
        text("content", { max: 2000000 }),
        bool("is_binary"),
        num("size_bytes"),
        text("sha256"),
        text("language"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_files_ext_path ON files (extender, relpath)"],
    },
    {
      name: "distributions",
      rules: AUTH,
      fields: [
        text("slug", { required: true }),
        select("kind", ["bundle", "plugin", "standalone"], { required: true }),
        text("version"),
        text("description"),
        rel("members", "extenders", { maxSelect: 500 }),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_distributions_slug ON distributions (slug)"],
    },
    {
      name: "frontmatter_dimensions",
      rules: null,
      fields: [
        text("key", { required: true }),
        select("applies_to", KINDS, { required: true }),
        select("requirement", ["required", "optional", "harness", "custom", "deprecated"]),
        text("description"),
        rel("spec_framework", "frameworks"),
        num("observed_count"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_fm_dims ON frontmatter_dimensions (key, applies_to)"],
    },
    {
      name: "eval_runs",
      rules: AUTH,
      fields: [
        text("slug", { required: true }),
        select("kind", ["mechanical", "judged", "adversarial-review", "adjudication", "comparative", "experiment"], { required: true }),
        text("method", { max: 200000 }),
        text("criteria_text", { max: 2000000 }),
        rel("frameworks", "frameworks", { maxSelect: 20 }),
        select("status", ["planned", "running", "complete", "abandoned"]),
        text("notes", { max: 200000 }),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_eval_runs_slug ON eval_runs (slug)"],
    },
    {
      name: "eval_responses",
      rules: AUTH,
      fields: [
        rel("run", "eval_runs", { required: true, cascadeDelete: true }),
        text("role", { required: true }),
        text("agent_type"),
        text("model"),
        text("prompt", { max: 2000000 }),
        text("response_text", { max: 2000000 }),
        json("response_json"),
        rel("extenders", "extenders", { maxSelect: 100 }),
        num("tokens"),
        num("duration_ms"),
        json("measurement"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_eval_responses ON eval_responses (run, role)"],
    },
    {
      name: "assessments",
      rules: AUTH,
      fields: [
        rel("extender", "extenders", { required: true, cascadeDelete: true }),
        rel("framework", "frameworks", { required: true }),
        rel("element", "framework_elements"),
        rel("eval_run", "eval_runs"),
        select("verdict", ["present", "partial", "absent", "not-applicable"], { required: true }),
        num("score"),
        text("evidence"),
        text("assessor"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_assessments ON assessments (extender, framework, element, assessor)"],
    },
    {
      name: "job_coverage",
      rules: AUTH,
      fields: [
        rel("job", "framework_elements", { required: true }),
        select("disposition", ["author", "vendor", "reference", "compare"]),
        select("status", ["covered", "partial", "gap"]),
        rel("source", "sources"),
        text("rationale", { max: 10000 }),
        rel("eval_run", "eval_runs"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_job_coverage ON job_coverage (job)"],
    },
    {
      name: "relationships",
      rules: null,
      fields: [
        rel("extender_a", "extenders", { required: true }),
        rel("extender_b", "extenders", { required: true }),
        select("kind", ["duplicative", "conflicting", "complementary", "precedes", "feeds-into"], { required: true }),
        rel("job", "framework_elements"),
        text("evidence", { max: 10000 }),
        text("assessor"),
        rel("eval_run", "eval_runs"),
      ],
      indexes: ["CREATE UNIQUE INDEX idx_relationships ON relationships (extender_a, extender_b, kind, job)"],
    },
    {
      name: "coverage_gaps",
      type: "view",
      rules: null,
      viewQuery:
        "SELECT jc.id AS id, fe.slug AS job_slug, fe.name AS job_name, fe.category AS category, jc.status AS status, jc.disposition AS disposition, jc.rationale AS rationale, jc.updated AS updated FROM job_coverage jc JOIN framework_elements fe ON fe.id = jc.job WHERE jc.status != 'covered'",
    },
    {
      name: "runs",
      rules: AUTH,
      fields: [
        select("harness", ["claude", "opencode", "codex"], { required: true }),
        select("era", ["legacy", "post", "na"]),
        text("campaign"),
        text("candidate", { required: true }),
        text("case", { required: true }),
        select("config", ["with", "baseline"]),
        text("kind"),
        num("trial"),
        text("model"),
        text("grader_model"),
        text("cli_version"),
        text("session_id"),
        bool("passed"),
        bool("skill_used"),
        num("exit_code"),
        num("num_turns"),
        num("cost_usd"),
        num("duration_ms"),
        num("input_tokens"),
        num("output_tokens"),
        num("cache_creation_tokens"),
        num("cache_read_tokens"),
        text("error", { max: 2000 }),
        text("workspace"),
        json("checks"),
        json("grades"),
        json("tool_names"),
        json("model_usage"),
        json("provenance"),
        json("measurement"),
        text("log_path"),
        text("ts"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_runs_key ON runs (campaign, harness, model, candidate, `case`, config, trial)",
        "CREATE UNIQUE INDEX idx_runs_session ON runs (session_id) WHERE session_id != ''",
        "CREATE INDEX idx_runs_log ON runs (log_path)",
      ],
    },
    {
      name: "artifacts",
      rules: AUTH,
      fields: [
        rel("run", "runs", { required: true }),
        select("kind", ["write_content", "edit_diff", "screenshot", "tool_output"]),
        text("mime"),
        { name: "blob", type: "file", maxSelect: 1, maxSize: 10000000, mimeTypes: [], thumbs: [], protected: true },
        text("sha256", { required: true }),
        num("byte_size"),
        text("text_ref", { max: 5000 }),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_artifacts_sha ON artifacts (sha256)",
        "CREATE INDEX idx_artifacts_run ON artifacts (run)",
      ],
    },
    {
      name: "run_events",
      rules: AUTH,
      fields: [
        rel("run", "runs", { required: true, cascadeDelete: true }),
        num("seq"),
        num("ts"),
        select("vendor", ["claude", "opencode", "codex"]),
        select("role", ["assistant", "tool_call", "tool_result", "system", "result"]),
        text("event_type"),
        text("tool_name"),
        text("tool_call_id"),
        text("status"),
        bool("is_error"),
        num("input_tokens"),
        num("output_tokens"),
        num("cache_read_tokens"),
        num("cache_write_tokens"),
        num("cost_usd"),
        num("wallclock_ms"),
        text("text", { max: 5000 }),
        json("payload"),
        rel("artifact", "artifacts"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_run_events_key ON run_events (run, seq)",
        "CREATE INDEX idx_run_events_call ON run_events (tool_call_id)",
      ],
    },
    {
      name: "tool_calls",
      rules: AUTH,
      fields: [
        rel("run", "runs", { required: true, cascadeDelete: true }),
        text("tool_call_id", { required: true }),
        text("tool_name", { required: true }),
        json("input"),
        json("output"),
        text("status"),
        bool("is_error"),
        num("wallclock_ms"),
        num("started_ts"),
        rel("artifact", "artifacts"),
      ],
      indexes: [
        "CREATE UNIQUE INDEX idx_tool_calls_key ON tool_calls (run, tool_call_id)",
        "CREATE INDEX idx_tool_calls_name ON tool_calls (tool_name)",
      ],
    },
  ];

  const AUTODATES = [
    { name: "created", type: "autodate", onCreate: true, onUpdate: false },
    { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
  ];

  const findCollection = (name) => {
    try {
      return app.findCollectionByNameOrId(name);
    } catch (_) {
      return null;
    }
  };

  // A field definition as PocketBase takes it: relations name their target collection by id.
  const fieldData = (spec) => {
    const data = Object.assign({}, spec);
    if (data.type === "relation") {
      data.collectionId = app.findCollectionByNameOrId(spec.target).id;
      data.minSelect = 0;
      delete data.target;
    }
    return data;
  };

  const indexName = (sql) => {
    const m = /INDEX\s+(\S+)\s+ON/i.exec(sql);
    return m ? m[1] : sql;
  };

  // A rule as a plain string or null (the Go side holds it as a string pointer).
  const ruleOf = (value) => (value === undefined || value === null ? null : String(value));

  // Sets the access rules; returns whether any changed.
  const applyRules = (collection, rule) => {
    const wanted = { listRule: rule, viewRule: rule };
    if (collection.type !== "view") {
      wanted.createRule = null;
      wanted.updateRule = null;
      wanted.deleteRule = null;
    }
    let changed = false;
    for (const key in wanted) {
      if (ruleOf(collection[key]) !== wanted[key]) {
        collection[key] = wanted[key];
        changed = true;
      }
    }
    return changed;
  };

  // Adds what an existing collection lacks; returns whether anything changed.
  const upgrade = (collection, spec) => {
    let changed = false;
    const wanted = spec.fields.concat(AUTODATES);
    for (let i = 0; i < wanted.length; i++) {
      const fieldSpec = wanted[i];
      const existing = collection.fields.getByName(fieldSpec.name);
      if (!existing) {
        // Insert after the field that precedes it in the spec, so the order reads as Appendix A.
        let pos = collection.fields.length;
        for (let j = i - 1; j >= 0; j--) {
          const before = collection.fields.getByName(wanted[j].name);
          if (before) {
            pos = collection.fields.indexOf(before) + 1;
            break;
          }
        }
        collection.fields.addAt(pos, new Field(fieldData(fieldSpec)));
        changed = true;
        continue;
      }
      if (fieldSpec.type === "select") {
        const values = [];
        for (const v of existing.values) values.push(v);
        let added = false;
        for (const v of fieldSpec.values) {
          if (values.indexOf(v) < 0) {
            values.push(v);
            added = true;
          }
        }
        if (added) {
          existing.values = values;
          changed = true;
        }
      }
    }
    const present = {};
    const indexes = [];
    for (const sql of collection.indexes) {
      indexes.push(sql);
      present[indexName(sql)] = true;
    }
    for (const sql of spec.indexes) {
      if (!present[indexName(sql)]) {
        indexes.push(sql);
        changed = true;
      }
    }
    if (changed) collection.indexes = indexes;
    return changed;
  };

  for (const spec of SCHEMA) {
    let collection = findCollection(spec.name);
    let dirty = false;
    if (!collection) {
      dirty = true;
      collection =
        spec.type === "view"
          ? new Collection({ type: "view", name: spec.name, viewQuery: spec.viewQuery })
          : new Collection({
              type: "base",
              name: spec.name,
              fields: spec.fields.concat(AUTODATES).map(fieldData),
              indexes: spec.indexes,
            });
    } else if (spec.type !== "view") {
      dirty = upgrade(collection, spec);
    }
    if (applyRules(collection, spec.rules)) dirty = true;
    if (dirty) app.save(collection);
  }

  const users = app.findCollectionByNameOrId("users");
  const own = "id = @request.auth.id";
  const userRules = { listRule: own, viewRule: own, createRule: null, updateRule: null, deleteRule: null };
  let usersDirty = false;
  for (const key in userRules) {
    if (ruleOf(users[key]) !== userRules[key]) {
      users[key] = userRules[key];
      usersDirty = true;
    }
  }
  if (usersDirty) app.save(users);

  const settings = app.settings();
  if (!settings.rateLimits.enabled) {
    settings.rateLimits.enabled = true;
    app.save(settings);
  }
}, (_app) => {
  // Forward-only: an application rollback redeploys the previous package and
  // leaves additive fields in place.
});
