"use strict";

// Advisor-board overview deck: what acme-platform is + the add-on module /
// services expansion opportunity. Theme: actuarial-signal (semantic tokens).
// Sources: docs/charter.md (2026-06-09), acme-labs docs/PRODUCT.md (2026-06-10).

const pptxgen = require("pptxgenjs");
const { THEMES } = require("~/.claude/skills/pptx-henry/assets/theme-tokens.js");

const C = THEMES["actuarial-signal"];
const FONT = "Avenir Next";

const W = 13.33;
const H = 7.5;
const MX = 0.65; // side margin
const CW = W - 2 * MX; // content width
const FOOTER_Y = 7.05;

const SRC = "Sources: acme-platform charter (2026-06-09) - acme-labs product thesis (2026-06-10)";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Sample Presenter";
pres.title = "RA Platform - Advisor Board Overview";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT, lang: "en-US" };

const makeShadow = () => ({ type: "outer", color: C.shadow, blur: 7, offset: 2, angle: 135, opacity: 0.16 });

function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: C.canvas };
  return s;
}

function kicker(s, text, y = 0.55, color = C.accentPrimary) {
  s.addText(text.toUpperCase(), {
    x: MX, y, w: CW, h: 0.32, fontFace: FONT, fontSize: 11, bold: true,
    color, charSpacing: 3, margin: 0,
  });
}

function slideTitle(s, text, y = 0.92, opts = {}) {
  s.addText(text, {
    x: MX, y, w: CW, h: opts.h || 0.95, fontFace: FONT, fontSize: opts.size || 28,
    bold: true, color: C.textPrimary, margin: 0, valign: "top",
  });
}

function footer(s, text = SRC) {
  s.addText(text, {
    x: MX, y: FOOTER_Y, w: CW - 1.2, h: 0.3, fontFace: FONT, fontSize: 9,
    color: C.textSecondary, margin: 0, valign: "middle",
  });
  s.addText("RA Platform - Confidential", {
    x: W - MX - 2.6, y: FOOTER_Y, w: 2.6, h: 0.3, fontFace: FONT, fontSize: 9,
    color: C.textSecondary, align: "right", margin: 0, valign: "middle",
  });
}

function card(s, x, y, w, h, fill = C.surface, withShadow = true) {
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: fill },
    line: { color: C.border, width: 0.75 },
    shadow: withShadow ? makeShadow() : undefined,
  });
}

function accentBar(s, x, y, h, color = C.accentPrimary, w = 0.07) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color }, line: { type: "none" } });
}

function bullets(s, items, x, y, w, h, opts = {}) {
  const runs = items.map((t, i) => ({
    text: t,
    options: {
      bullet: { code: "2022", indent: 14 },
      breakLine: i < items.length - 1,
      paraSpaceAfter: opts.gap == null ? 10 : opts.gap,
    },
  }));
  s.addText(runs, {
    x, y, w, h, fontFace: FONT, fontSize: opts.size || 15,
    color: opts.color || C.textPrimary, margin: 0, valign: opts.valign || "top",
  });
}

// ---------------------------------------------------------------- 1 - TITLE
{
  const s = lightSlide();
  accentBar(s, 0, 0, H, C.accentPrimary, 0.14);
  kicker(s, "Advisor board briefing - June 2026", 1.5);
  s.addText("Proving what Medicare Advantage\nplans are actually paid", {
    x: MX, y: 1.95, w: CW, h: 1.9, fontFace: FONT, fontSize: 42, bold: true,
    color: C.textPrimary, margin: 0, valign: "top", lineSpacingMultiple: 1.05,
  });
  s.addText("RA Platform - what we built, where it stands, and the add-on module and services opportunity it opens", {
    x: MX, y: 3.85, w: 9.6, h: 0.8, fontFace: FONT, fontSize: 18,
    color: C.textSecondary, margin: 0, valign: "top",
  });
  card(s, MX, 5.1, 8.3, 1.35, C.surface);
  accentBar(s, MX, 5.1, 1.35, C.accentSecondary);
  s.addText([
    { text: "The product in one sentence: ", options: { bold: true, color: C.textAccent } },
    { text: "ingest a plan's CMS payment files, recompute every risk score and payment, and show — member by member, month by month — where the dollars diverge.", options: { color: C.textPrimary } },
  ], {
    x: MX + 0.28, y: 5.1, w: 7.8, h: 1.35, fontFace: FONT, fontSize: 14.5,
    margin: 0, valign: "middle",
  });
  s.addText("Sample Presenter - June 12, 2026", {
    x: MX, y: 6.85, w: CW, h: 0.35, fontFace: FONT, fontSize: 11,
    color: C.textSecondary, margin: 0,
  });
}

// ------------------------------------------------------ 2 - EXEC SUMMARY
{
  const s = lightSlide();
  kicker(s, "Executive summary");
  slideTitle(s, "A working audit engine today, a platform business next");

  const stats = [
    { v: "3", l: "ledgers reconciled", d: "true - transmitted - paid" },
    { v: "$", l: "member-month granularity", d: "every finding is dollar-tagged" },
    { v: "3-step", l: "commercial motion", d: "scan - recovery - recurring" },
  ];
  const sw = (CW - 0.8) / 3;
  stats.forEach((st, i) => {
    const x = MX + i * (sw + 0.4);
    card(s, x, 1.85, sw, 1.7);
    accentBar(s, x, 1.85, 1.7);
    s.addText(st.v, { x: x + 0.3, y: 2.02, w: sw - 0.5, h: 0.7, fontFace: FONT, fontSize: 27, bold: true, color: C.accentPrimary, margin: 0 });
    s.addText(st.l.toUpperCase(), { x: x + 0.3, y: 2.72, w: sw - 0.5, h: 0.3, fontFace: FONT, fontSize: 10.5, bold: true, charSpacing: 2, color: C.textSecondary, margin: 0 });
    s.addText(st.d, { x: x + 0.3, y: 3.02, w: sw - 0.5, h: 0.4, fontFace: FONT, fontSize: 12.5, color: C.textPrimary, margin: 0 });
  });

  bullets(s, [
    "The platform works end to end: provision a client, land its CMS file set, return a tenant-scoped payment audit",
    "First client deployment is imminent — a per-client desktop install for IT-constrained plans",
    "The audit is the wedge: every dollar gap it exposes is an add-on module or service a client will pay for",
    "Destination: recurring, CFO-grade revenue — the monthly accrual close packet, defended actuary-to-actuary",
  ], MX, 4.05, CW, 2.8, { size: 16, gap: 18 });
  footer(s);
}

// ------------------------------------------------------------ 3 - PROBLEM
{
  const s = lightSlide();
  kicker(s, "The problem");
  slideTitle(s, "Plans cannot independently verify what CMS pays them");

  const ledgers = [
    { n: "1", t: "TRUE", d: "The member's actual clinical state and the plan's real entitlements", who: "Known only to the plan — inferred, never fully observed" },
    { n: "2", t: "TRANSMITTED", d: "What reached CMS through the submission machinery, surviving rejections and deadlines", who: "Submission records: 837 / RAPS-EDS, enrollment transactions" },
    { n: "3", t: "PAID", d: "What CMS heard, scored, and settled", who: "CMS return files: MOR, MMR, PPR" },
  ];
  const lw = (CW - 0.8) / 3;
  ledgers.forEach((L, i) => {
    const x = MX + i * (lw + 0.4);
    card(s, x, 2.0, lw, 2.55);
    s.addText(L.n, { x: x + 0.28, y: 2.18, w: 0.8, h: 0.6, fontFace: FONT, fontSize: 30, bold: true, color: C.accentSecondary, margin: 0 });
    s.addText(L.t, { x: x + 0.28, y: 2.78, w: lw - 0.56, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, charSpacing: 2, color: C.textPrimary, margin: 0 });
    s.addText(L.d, { x: x + 0.28, y: 3.16, w: lw - 0.56, h: 0.85, fontFace: FONT, fontSize: 12.5, color: C.textPrimary, margin: 0 });
    s.addText(L.who, { x: x + 0.28, y: 4.02, w: lw - 0.56, h: 0.45, fontFace: FONT, fontSize: 10.5, italic: true, color: C.textSecondary, margin: 0 });
  });

  card(s, MX, 4.95, CW, 1.6, C.surfaceInverse);
  s.addText([
    { text: "Dollars leak in the gaps between the three ledgers. ", options: { bold: true, color: C.textInverse } },
    { text: "And the leaks expire: under 42 CFR 422.310(g), a diagnosis submitted after the final risk-adjustment deadline is never paid. Every gap a plan has not found yet is on a regulatory clock.", options: { color: C.textInverse } },
  ], {
    x: MX + 0.35, y: 4.95, w: CW - 0.7, h: 1.6, fontFace: FONT, fontSize: 15, margin: 0, valign: "middle",
  });
  footer(s);
}

// ------------------------------------------------------------ 4 - ENGINE
{
  const s = lightSlide();
  kicker(s, "What we built");
  slideTitle(s, "We recompute the government's math and show our work");

  const steps = ["Ingest the client's CMS payment file set", "Recompute risk scores + payment", "Reconcile recomputed vs paid", "Per-member-month verdicts with dollar impact"];
  const stw = (CW - 3 * 0.55) / 4;
  steps.forEach((t, i) => {
    const x = MX + i * (stw + 0.55);
    card(s, x, 2.0, stw, 1.45, C.surface);
    accentBar(s, x, 2.0, 1.45, C.accentPrimary);
    s.addText(t, { x: x + 0.24, y: 2.18, w: stw - 0.42, h: 1.1, fontFace: FONT, fontSize: 12.5, bold: true, color: C.textPrimary, margin: 0, valign: "top" });
    if (i < 3) {
      s.addText("→", { x: x + stw + 0.05, y: 2.0, w: 0.5, h: 1.45, fontFace: FONT, fontSize: 20, bold: true, color: C.accentSecondary, align: "center", valign: "middle", margin: 0 });
    }
  });

  const colW = (CW - 0.5) / 2;
  s.addText("EVIDENCE-GRADE BY DESIGN", { x: MX, y: 3.85, w: colW, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, charSpacing: 2, color: C.accentPrimary, margin: 0 });
  bullets(s, [
    "Every answer drills to its evidence — the source record and audit trail",
    "Byte-verified ingestion; findings carry citations",
    "Proprietary judgment layer kept cleanly separate from the evidence layer — that is the IP boundary and the audit story",
  ], MX, 4.2, colW, 2.4, { size: 13.5, gap: 9 });

  s.addText("BUILT FOR REAL CLIENTS", { x: MX + colW + 0.5, y: 3.85, w: colW, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, charSpacing: 2, color: C.accentPrimary, margin: 0 });
  bullets(s, [
    "Multi-tenant on GCP, invite-only; tenant isolation at the data and compute layers",
    "Dual delivery: cloud web app + a per-client desktop install for plans whose IT departments hold up contracts",
    "Operations Center in build: file-arrival, run-status, and data-quality answers in 30 seconds",
  ], MX + colW + 0.5, 4.2, colW, 2.4, { size: 13.5, gap: 9 });
  footer(s);
}

// ------------------------------------------------------------ 5 - MARKET
{
  const s = lightSlide();
  kicker(s, "The wedge market");
  slideTitle(s, "Small and mid-size MA plans - D-SNPs first - sold peer-to-peer");

  const cols = [
    { h: "WHY D-SNPs FIRST", items: [
      "Dual-status complexity maximizes the error surface — more divergence to find",
      "Thin internal actuarial staff: they cannot run this audit themselves",
      "Decision-makers are reachable — no enterprise sales gauntlet",
    ] },
    { h: "THE CHANNEL MULTIPLIER", items: [
      "Management companies and TPAs operate many small plans at once",
      "One integration and one relationship covers their whole roster",
      "Each new module we ship resells across that installed base",
    ] },
    { h: "THE FOUNDER EDGE", items: [
      "20+ year credentialed actuary; Kellogg MBA",
      "Built an actuarial department and an enterprise data warehouse",
      "The sale is peer-to-peer: actuary to actuary, CFO to CFO",
    ] },
  ];
  const cw3 = (CW - 0.8) / 3;
  cols.forEach((c, i) => {
    const x = MX + i * (cw3 + 0.4);
    card(s, x, 2.25, cw3, 3.85);
    accentBar(s, x, 2.25, 3.85, C.accentPrimary);
    s.addText(c.h, { x: x + 0.3, y: 2.5, w: cw3 - 0.55, h: 0.55, fontFace: FONT, fontSize: 13, bold: true, charSpacing: 1.5, color: C.textPrimary, margin: 0 });
    bullets(s, c.items, x + 0.3, 3.15, cw3 - 0.55, 2.8, { size: 13, gap: 12 });
  });
  footer(s);
}

// ------------------------------------------------------------ 6 - MOTION
{
  const s = lightSlide();
  kicker(s, "Commercial motion");
  slideTitle(s, "A scan to land, recovery to convert, recurring to keep");

  const steps = [
    { n: "1", t: "Payment-integrity scan", tag: "THE WEDGE - FREE OR CHEAP", d: "The plan hands over one month of CMS return files; we return a verdict report — what every file is, whether its totals reconcile, dollar-tagged findings. Built and running today." },
    { n: "2", t: "Recovery engagement", tag: "CONTINGENCY - DEADLINE-DRIVEN", d: "Close the gaps that are still actionable before the regulatory deadline makes them permanent. Urgency is built into the engagement: every clock is CMS's, not ours." },
    { n: "3", t: "Accrual support", tag: "RECURRING - THE DESTINATION", d: "A monthly close packet: the per-member-month sub-ledger behind the risk-adjusted revenue accrual, evidence attached. Sold to the CFO, defended actuary-to-actuary, sticky once an auditor accepts it." },
  ];
  const cw3 = (CW - 0.8) / 3;
  steps.forEach((st, i) => {
    const x = MX + i * (cw3 + 0.4);
    card(s, x, 2.05, cw3, 4.35);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 2.32, w: 0.62, h: 0.62, fill: { color: C.accentPrimary }, line: { type: "none" } });
    s.addText(st.n, { x: x + 0.3, y: 2.32, w: 0.62, h: 0.62, fontFace: FONT, fontSize: 20, bold: true, color: C.textInverse, align: "center", valign: "middle", margin: 0 });
    s.addText(st.t, { x: x + 0.3, y: 3.12, w: cw3 - 0.6, h: 0.45, fontFace: FONT, fontSize: 16.5, bold: true, color: C.textPrimary, margin: 0 });
    s.addText(st.tag, { x: x + 0.3, y: 3.58, w: cw3 - 0.6, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, charSpacing: 1.5, color: C.accentSecondary, margin: 0 });
    s.addText(st.d, { x: x + 0.3, y: 3.98, w: cw3 - 0.6, h: 2.25, fontFace: FONT, fontSize: 12.5, color: C.textPrimary, margin: 0, valign: "top" });
    if (i < 2) {
      s.addText("→", { x: x + cw3 + 0.02, y: 2.33, w: 0.38, h: 0.6, fontFace: FONT, fontSize: 22, bold: true, color: C.accentSecondary, align: "center", valign: "middle", margin: 0 });
    }
  });
  footer(s);
}

// ------------------------------------------------------------ 7 - DIVIDER
{
  const s = pres.addSlide();
  s.background = { color: C.surfaceInverse };
  s.addText("02", { x: MX, y: 2.05, w: 3, h: 1.6, fontFace: FONT, fontSize: 88, bold: true, color: C.accentSecondary, margin: 0 });
  s.addText("The expansion opportunity", {
    x: MX, y: 3.85, w: CW, h: 1.0, fontFace: FONT, fontSize: 38, bold: true, color: C.textInverse, margin: 0,
  });
  s.addText("Why the core audit is a beachhead, not the business — add-on modules and services that compound on the same engine and the same installed base.", {
    x: MX, y: 4.9, w: 9.8, h: 1.0, fontFace: FONT, fontSize: 16, color: C.textInverse, margin: 0,
  });
}

// ------------------------------------------------- 8 - GAPS BECOME MODULES
{
  const s = lightSlide();
  kicker(s, "Expansion logic");
  slideTitle(s, "Every gap the audit exposes is a product we can sell");

  s.addText("The audit puts us at the divergence data. Each ledger gap maps to a distinct product surface:", {
    x: MX, y: 1.78, w: CW, h: 0.4, fontFace: FONT, fontSize: 14.5, color: C.textSecondary, margin: 0,
  });

  const rows = [
    [
      { text: "LEDGER GAP", options: { bold: true, color: C.textInverse, fill: { color: C.accentPrimary }, fontSize: 11.5 } },
      { text: "WHAT IT MEANS", options: { bold: true, color: C.textInverse, fill: { color: C.accentPrimary }, fontSize: 11.5 } },
      { text: "ADD-ON MODULE", options: { bold: true, color: C.textInverse, fill: { color: C.accentPrimary }, fontSize: 11.5 } },
      { text: "REVENUE SHAPE", options: { bold: true, color: C.textInverse, fill: { color: C.accentPrimary }, fontSize: 11.5 } },
    ],
    ["Transmitted vs Paid", "Submitted diagnoses CMS never scored or paid", "Submission recovery", "Contingency fee"],
    ["True vs Transmitted", "Documented conditions that never got submitted", "Chart-review + suspecting analytics", "Per engagement, then SaaS"],
    ["Paid, over time", "New return files drift from expectations each month", "Continuous monitoring + feed watch", "Subscription"],
    ["All three, monthly", "The CFO accrues revenue without a defensible sub-ledger", "Accrual close packet", "Recurring monthly"],
  ];
  const styledRows = rows.map((r, ri) => r.map((cell) => {
    if (typeof cell === "string") {
      const base = { fontSize: 12.5, color: C.textPrimary, fill: { color: ri % 2 === 1 ? "FFFFFF" : C.surfaceElevated }, valign: "middle" };
      return { text: cell, options: base };
    }
    return cell;
  }));
  s.addTable(styledRows, {
    x: MX, y: 2.4, w: CW, colW: [2.4, 4.13, 3.4, 2.1],
    border: { pt: 0.75, color: C.border },
    fontFace: FONT, rowH: [0.45, 0.78, 0.78, 0.78, 0.78],
    margin: [0.07, 0.12, 0.07, 0.12],
  });

  s.addText("Module list is directional — sequencing and packaging are open questions for this board (slide 13).", {
    x: MX, y: 6.45, w: CW, h: 0.35, fontFace: FONT, fontSize: 11, italic: true, color: C.textSecondary, margin: 0,
  });
  footer(s);
}

// ------------------------------------------------------------ 9 - 2x2
{
  const s = lightSlide();
  kicker(s, "Module portfolio");
  slideTitle(s, "Near-term offers fund the build toward recurring revenue", 0.92, { size: 28 });

  // matrix geometry
  const gx = 3.1, gy = 1.95, gw = 8.4, gh = 4.3;
  const cx = gx + gw / 2, cy = gy + gh / 2;

  // quadrant field
  s.addShape(pres.shapes.RECTANGLE, { x: gx, y: gy, w: gw, h: gh, fill: { color: "FFFFFF" }, line: { color: C.borderStrong, width: 1.5 } });
  // axes
  s.addShape(pres.shapes.LINE, { x: gx, y: cy, w: gw, h: 0, line: { color: C.borderStrong, width: 1.5 } });
  s.addShape(pres.shapes.LINE, { x: cx, y: gy, w: 0, h: gh, line: { color: C.borderStrong, width: 1.5 } });

  // axis labels (gutters)
  s.addText("SELLABLE NOW  →  NEEDS BUILD", { x: gx, y: gy + gh + 0.12, w: gw, h: 0.3, fontFace: FONT, fontSize: 10.5, bold: true, charSpacing: 2, color: C.textSecondary, align: "center", margin: 0 });
  s.addText("ONE-TIME  →  RECURRING", { x: gx - 2.27, y: cy - 0.15, w: 4.0, h: 0.3, fontFace: FONT, fontSize: 10.5, bold: true, charSpacing: 2, color: C.textSecondary, align: "center", rotate: 270, margin: 0 });

  function chip(label, x, y, w, fillColor, textColor) {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.44, fill: { color: fillColor }, line: { type: "none" }, shadow: makeShadow() });
    s.addText(label, { x, y, w, h: 0.44, fontFace: FONT, fontSize: 11.5, bold: true, color: textColor, align: "center", valign: "middle", margin: 0 });
  }
  const qh = gh / 2; // 2.15
  const chipX = (qx) => qx + (gw / 2 - 3.55) / 2; // center chips horizontally in quadrant
  // top-left: sellable now / recurring (1 chip, centered)
  chip("Continuous monitoring + feed watch", chipX(gx), gy + (qh - 0.44) / 2, 3.55, C.accentPrimary, C.textInverse);
  // top-right: needs build / recurring (3 chips, centered stack)
  const trY = gy + (qh - (3 * 0.44 + 2 * 0.16)) / 2;
  chip("Accrual close packet", chipX(cx), trY, 3.55, C.accentSecondary, C.textInverse);
  chip("Chart-review + suspecting analytics", chipX(cx), trY + 0.6, 3.55, C.accentSecondary, C.textInverse);
  chip("Part D + encounter expansion", chipX(cx), trY + 1.2, 3.55, C.surfaceInverse, C.textInverse);
  // bottom-left: sellable now / one-time (2 chips, centered stack)
  const blY = cy + (qh - (2 * 0.44 + 0.16)) / 2;
  chip("Payment-integrity scan", chipX(gx), blY, 3.55, C.accentPrimary, C.textInverse);
  chip("Recovery engagements", chipX(gx), blY + 0.6, 3.55, C.accentPrimary, C.textInverse);
  // bottom-right: needs build / one-time (1 chip, centered)
  chip("RADV audit-defense support", chipX(cx), cy + (qh - 0.44) / 2, 3.55, C.surfaceInverse, C.textInverse);

  // left rail: reading guide
  s.addText("HOW TO READ THIS", { x: MX, y: 2.0, w: 1.85, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, charSpacing: 2, color: C.accentPrimary, margin: 0 });
  s.addText("Blue: runs on today's engine.\n\nBronze: the recurring destination — funded by near-term wins.\n\nSlate: later bets, same data spine.\n\nPlacement is directional, not a roadmap commitment.", {
    x: MX, y: 2.35, w: 1.85, h: 4.3, fontFace: FONT, fontSize: 11, color: C.textPrimary, margin: 0, valign: "top",
  });
  footer(s);
}

// ------------------------------------------------------------ 10 - SERVICES
{
  const s = lightSlide();
  kicker(s, "The services layer");
  slideTitle(s, "Services attach to every module the audit opens");

  const items = [
    { t: "Recovery engagements", d: "Contingency work the scan itself generates — findings convert to fees" },
    { t: "Managed monthly close", d: "We run the accrual packet as a service before it is self-serve software" },
    { t: "Onboarding + data operations", d: "Feed setup, expectation manifests, file wrangling — billable from day one" },
    { t: "Audit-defense support", d: "Stand behind the evidence when the client's auditor or CMS comes asking" },
  ];
  const cw2 = (CW - 0.5) / 2;
  items.forEach((it, i) => {
    const x = MX + (i % 2) * (cw2 + 0.5);
    const y = 2.0 + Math.floor(i / 2) * 1.45;
    card(s, x, y, cw2, 1.2);
    accentBar(s, x, y, 1.2, C.accentPrimary);
    s.addText(it.t, { x: x + 0.3, y: y + 0.14, w: cw2 - 0.55, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: C.textPrimary, margin: 0 });
    s.addText(it.d, { x: x + 0.3, y: y + 0.55, w: cw2 - 0.55, h: 0.55, fontFace: FONT, fontSize: 12.5, color: C.textSecondary, margin: 0 });
  });

  card(s, MX, 5.15, CW, 1.45, C.surfaceInverse);
  s.addText([
    { text: "The commercial prime directive: ", options: { bold: true, color: C.textInverse } },
    { text: "solve any kind of problem for a client so we can afford to do more for them. The first engagement may be ad hoc and off-thesis — land it, learn from it, expand. Through a management company or TPA, every expansion repeats across their whole roster of plans.", options: { color: C.textInverse } },
  ], { x: MX + 0.35, y: 5.15, w: CW - 0.7, h: 1.45, fontFace: FONT, fontSize: 14, margin: 0, valign: "middle" });
  footer(s);
}

// ------------------------------------------------------------ 11 - MOAT
{
  const s = lightSlide();
  kicker(s, "Why it sticks");
  slideTitle(s, "Once an auditor accepts the evidence, we are the system of record");

  const cw2 = (CW - 0.5) / 2;
  s.addText("DEFENSIBILITY", { x: MX, y: 2.3, w: cw2, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, charSpacing: 2, color: C.accentPrimary, margin: 0 });
  card(s, MX, 2.7, cw2, 3.5);
  bullets(s, [
    "Byte-verified ingestion; every finding cites its source record",
    "Evidence layer is deliberately separated from the proprietary judgment layer — an auditor can rely on the evidence precisely because the opinion is not baked into it",
    "The same separation is the IP boundary: competitors can see what we prove, not how we decide",
  ], MX + 0.3, 3.0, cw2 - 0.6, 3.0, { size: 13.5, gap: 14 });

  s.addText("STICKINESS", { x: MX + cw2 + 0.5, y: 2.3, w: cw2, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, charSpacing: 2, color: C.accentPrimary, margin: 0 });
  card(s, MX + cw2 + 0.5, 2.7, cw2, 3.5);
  bullets(s, [
    "The per-member-month sub-ledger ends up underneath the plan's risk-adjusted revenue accrual",
    "Switching vendors means re-proving the books to your auditor — a cost no CFO volunteers for",
    "Each added module reads from the same spine, so every cross-sell deepens the dependency",
  ], MX + cw2 + 0.8, 3.0, cw2 - 0.6, 3.0, { size: 13.5, gap: 14 });
  footer(s);
}

// ------------------------------------------------------------ 12 - STATUS
{
  const s = lightSlide();
  kicker(s, "Where we are now");
  slideTitle(s, "The engine works; the build now is about comprehension");

  const rows = [
    { t: "Working end-to-end audit", st: "DONE", d: "Provision a client, land CMS files, get a tenant-scoped audit back — verified against a demo client", c: C.positive },
    { t: "First client deployment", st: "IN MOTION", d: "Per-client desktop install (client IT constraints make desktop the first vehicle; cloud follows compliance gating)", c: C.caution },
    { t: "Operations Center", st: "IN BUILD", d: "The operator home: did files arrive, did the run succeed, is the data clean, is it ready to hand off — in 30 seconds", c: C.caution },
    { t: "Multi-tenant hardening", st: "IN BUILD", d: "Compute-schema isolation and authz tightening so a second live client onboards safely", c: C.caution },
  ];
  rows.forEach((r, i) => {
    const y = 2.0 + i * 1.22;
    card(s, MX, y, CW, 0.92);
    s.addShape(pres.shapes.RECTANGLE, { x: MX, y, w: 0.07, h: 0.92, fill: { color: r.c }, line: { type: "none" } });
    s.addText(r.t, { x: MX + 0.3, y: y + 0.085, w: 3.6, h: 0.75, fontFace: FONT, fontSize: 14.5, bold: true, color: C.textPrimary, margin: 0, valign: "middle" });
    s.addShape(pres.shapes.RECTANGLE, { x: MX + 4.0, y: y + 0.26, w: 1.25, h: 0.4, fill: { color: r.c }, line: { type: "none" } });
    s.addText(r.st, { x: MX + 4.0, y: y + 0.26, w: 1.25, h: 0.4, fontFace: FONT, fontSize: 10, bold: true, charSpacing: 1, color: C.textInverse, align: "center", valign: "middle", margin: 0 });
    s.addText(r.d, { x: MX + 5.55, y: y + 0.085, w: CW - 5.85, h: 0.75, fontFace: FONT, fontSize: 12, color: C.textSecondary, margin: 0, valign: "middle" });
  });
  footer(s);
}

// ------------------------------------------------------------ 13 - THE ASK
{
  const s = lightSlide();
  kicker(s, "The ask");
  slideTitle(s, "Where this board can move the needle");

  card(s, MX, 1.95, CW, 1.5, C.surfaceInverse);
  s.addText([
    { text: "The engine works and the first client is landing. ", options: { bold: true, color: C.textInverse } },
    { text: "The open questions are commercial, not technical — which is exactly what this board is for.", options: { color: C.textInverse } },
  ], { x: MX + 0.35, y: 1.95, w: CW - 0.7, h: 1.5, fontFace: FONT, fontSize: 16, margin: 0, valign: "middle" });

  const asks = [
    { n: "1", t: "Introductions", d: "Management companies, TPAs, and D-SNP decision-makers — one channel relationship covers many plans" },
    { n: "2", t: "Packaging + pricing", d: "Scan-to-recovery conversion, contingency structures, and what a monthly close packet should cost" },
    { n: "3", t: "Module sequencing", d: "Which add-on follows the first recovery wins — monitoring, chart-review analytics, or straight to the accrual packet" },
  ];
  const cw3 = (CW - 0.8) / 3;
  asks.forEach((a, i) => {
    const x = MX + i * (cw3 + 0.4);
    card(s, x, 3.85, cw3, 2.45);
    accentBar(s, x, 3.85, 2.45, C.accentSecondary);
    s.addText(a.n, { x: x + 0.3, y: 4.05, w: 0.8, h: 0.55, fontFace: FONT, fontSize: 26, bold: true, color: C.accentSecondary, margin: 0 });
    s.addText(a.t, { x: x + 0.3, y: 4.62, w: cw3 - 0.55, h: 0.4, fontFace: FONT, fontSize: 16, bold: true, color: C.textPrimary, margin: 0 });
    s.addText(a.d, { x: x + 0.3, y: 5.05, w: cw3 - 0.55, h: 1.1, fontFace: FONT, fontSize: 12.5, color: C.textSecondary, margin: 0 });
  });
  footer(s, "Contact: Sample Presenter");
}

pres.writeFile({ fileName: "<dev-root>/acme-platform/_meta/briefings/2026-06-12-advisor-board-overview/acme-platform-advisor-overview.pptx" })
  .then(() => console.log("written"));
