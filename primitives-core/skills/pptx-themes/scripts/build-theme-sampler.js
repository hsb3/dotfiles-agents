"use strict";
// Build a 3-slide sampler deck that exercises every semantic token of one
// theme: title page, section divider, and a data slide. Use it to vet a new
// or tuned palette before using it in a real deck.
//
// Usage: NODE_PATH=<dir-with-node_modules> node build-theme-sampler.js <theme> [outdir]
// Then render with scripts/render-pptx.sh for visual inspection.

const path = require("path");
const pptxgen = require("pptxgenjs");
const { THEMES } = require(path.join(__dirname, "..", "assets", "theme-tokens.js"));

const themeKey = process.argv[2];
const outDir = process.argv[3] || ".";
if (!THEMES[themeKey]) {
  console.error(`Unknown theme "${themeKey}". Available: ${Object.keys(THEMES).join(", ")}`);
  process.exit(2);
}
const C = THEMES[themeKey];
const FONT = process.env.DECK_FONT || "Avenir Next";

const pptx = new pptxgen();
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pptx.layout = "WIDE";
pptx.theme = { headFontFace: FONT, bodyFontFace: FONT, lang: "en-US" };

// --- Slide 1: title page (canvas, text tiers, stat cards, accents) ---
let s = pptx.addSlide();
s.background = { color: C.canvas };
s.addText("THEME SAMPLER", { x: 0.62, y: 0.45, w: 6, h: 0.3, fontFace: FONT, fontSize: 11, bold: true, color: C.accentPrimary, charSpacing: 2.5, margin: 0 });
s.addText(`${C.name} earns the room without raising its voice`, { x: 0.6, y: 0.95, w: 8.2, h: 1.7, fontFace: FONT, fontSize: 31, bold: true, color: C.textPrimary, margin: 0 });
s.addText("Secondary text tier: supporting context set in textSecondary.", { x: 0.62, y: 2.75, w: 7.4, h: 0.4, fontFace: FONT, fontSize: 16, color: C.textSecondary, margin: 0 });
s.addShape(pptx.ShapeType.roundRect, { x: 0.62, y: 3.4, w: 2.4, h: 0.42, rectRadius: 0.21, fill: { color: C.accentSoft } });
s.addText("accentSoft chip · textAccent", { x: 0.62, y: 3.4, w: 2.4, h: 0.42, fontFace: FONT, fontSize: 10.5, color: C.textAccent, align: "center", margin: 0 });
const stats = [
  { v: "$49.8M", l: "accentPrimary", c: C.accentPrimary },
  { v: "+18%", l: "accentSecondary", c: C.accentSecondary },
  { v: "4 of 12", l: "accentTertiary", c: C.accentTertiary },
  { v: "▲ 2.3pts", l: "positive", c: C.positive },
];
stats.forEach((st, i) => {
  const x = 0.62 + i * 3.1;
  s.addShape(pptx.ShapeType.rect, { x, y: 4.6, w: 2.85, h: 1.5, fill: { color: C.surface }, line: { color: C.border, width: 1 } });
  s.addText(st.v, { x, y: 4.75, w: 2.85, h: 0.75, fontFace: FONT, fontSize: 30, bold: true, color: st.c, align: "center", margin: 0 });
  s.addText(st.l, { x, y: 5.55, w: 2.85, h: 0.4, fontFace: FONT, fontSize: 11, color: C.textSecondary, align: "center", margin: 0 });
});
s.addText("Source: footer tier in textSecondary on canvas", { x: 0.62, y: 7.05, w: 9, h: 0.25, fontFace: FONT, fontSize: 9, color: C.textSecondary, margin: 0 });

// --- Slide 2: section divider ---
// Light themes: surfaceInverse page + textInverse. Dark themes keep the dark
// canvas (a full light page mid-deck is a flash-bang) and mark the divider
// with an accent numeral + surfaceElevated band; surfaceInverse appears only
// as a small contrast chip.
s = pptx.addSlide();
if (C.dark) {
  s.background = { color: C.canvas };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 2.0, w: 13.333, h: 3.2, fill: { color: C.surfaceElevated } });
  s.addText("02", { x: 0.62, y: 2.2, w: 2, h: 1, fontFace: FONT, fontSize: 52, bold: true, color: C.accentPrimary, margin: 0 });
  s.addText("Section divider stays on the dark canvas", { x: 0.62, y: 3.3, w: 10.5, h: 1, fontFace: FONT, fontSize: 30, bold: true, color: C.textPrimary, margin: 0 });
  s.addShape(pptx.ShapeType.roundRect, { x: 0.62, y: 4.45, w: 3.3, h: 0.42, rectRadius: 0.21, fill: { color: C.surfaceInverse } });
  s.addText("surfaceInverse contrast chip", { x: 0.62, y: 4.45, w: 3.3, h: 0.42, fontFace: FONT, fontSize: 10.5, bold: true, color: C.textInverse, align: "center", margin: 0 });
} else {
  s.background = { color: C.surfaceInverse };
  s.addText("02", { x: 0.62, y: 2.2, w: 2, h: 1, fontFace: FONT, fontSize: 52, bold: true, color: C.accentSecondary, margin: 0 });
  s.addText("Section divider on surfaceInverse", { x: 0.62, y: 3.3, w: 10.5, h: 1, fontFace: FONT, fontSize: 30, bold: true, color: C.textInverse, margin: 0 });
  s.addText("textInverse body copy, with a borderStrong rule below.", { x: 0.62, y: 4.4, w: 9, h: 0.4, fontFace: FONT, fontSize: 15, color: C.textInverse, margin: 0 });
  s.addShape(pptx.ShapeType.line, { x: 0.62, y: 5.1, w: 6, h: 0, line: { color: C.borderStrong, width: 1.5 } });
}

// --- Slide 3: data slide (series, track, status, elevated panel) ---
s = pptx.addSlide();
s.background = { color: C.canvas };
s.addText("Data tokens hold their order across every chart", { x: 0.6, y: 0.5, w: 12, h: 0.7, fontFace: FONT, fontSize: 25, bold: true, color: C.textPrimary, margin: 0 });
s.addChart(pptx.ChartType.bar, [
  { name: "dataPrimary", labels: ["Q1", "Q2", "Q3", "Q4"], values: [42.1, 44.5, 47.2, 49.8] },
  { name: "dataSecondary", labels: ["Q1", "Q2", "Q3", "Q4"], values: [40.8, 43.9, 48.1, 51.5] },
  { name: "dataTertiary", labels: ["Q1", "Q2", "Q3", "Q4"], values: [38.2, 41.0, 44.6, 47.9] },
  { name: "dataQuaternary", labels: ["Q1", "Q2", "Q3", "Q4"], values: [36.5, 39.2, 42.8, 45.1] },
], {
  x: 0.6, y: 1.5, w: 7.6, h: 4.6,
  chartColors: [C.dataPrimary, C.dataSecondary, C.dataTertiary, C.dataQuaternary],
  catAxisLabelColor: C.textSecondary, valAxisLabelColor: C.textSecondary,
  valGridLine: { color: C.gridline, style: "solid", size: 0.5 },
  catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT,
  showLegend: true, legendPos: "b", legendColor: C.textSecondary, legendFontFace: FONT,
  chartColorsOpacity: 100, barGapWidthPct: 60,
});
const chips = [
  { l: "positive", c: C.positive }, { l: "caution", c: C.caution },
  { l: "negative", c: C.negative }, { l: "informational", c: C.informational },
];
chips.forEach((ch, i) => {
  const y = 1.6 + i * 0.62;
  s.addShape(pptx.ShapeType.roundRect, { x: 8.6, y, w: 1.95, h: 0.44, rectRadius: 0.22, fill: { color: ch.c } });
  s.addText(ch.l, { x: 8.6, y, w: 1.95, h: 0.44, fontFace: FONT, fontSize: 10.5, bold: true, color: C.textInverse, align: "center", margin: 0 });
});
s.addShape(pptx.ShapeType.rect, { x: 8.6, y: 4.3, w: 4.1, h: 1.8, fill: { color: C.surfaceElevated }, line: { color: C.border, width: 1 } });
s.addText("surfaceElevated panel", { x: 8.8, y: 4.45, w: 3.7, h: 0.35, fontFace: FONT, fontSize: 12, bold: true, color: C.textPrimary, margin: 0 });
s.addText([
  { text: "▲ dataPositive  ", options: { color: C.dataPositive, bold: true } },
  { text: "▼ dataNegative  ", options: { color: C.dataNegative, bold: true } },
  { text: "— dataNeutral", options: { color: C.dataNeutral, bold: true } },
], { x: 8.8, y: 4.85, w: 3.7, h: 0.4, fontFace: FONT, fontSize: 11, margin: 0 });
s.addShape(pptx.ShapeType.rect, { x: 8.8, y: 5.45, w: 3.7, h: 0.18, fill: { color: C.dataTrack } });
s.addShape(pptx.ShapeType.rect, { x: 8.8, y: 5.45, w: 2.5, h: 0.18, fill: { color: C.dataPrimary } });
s.addText("Source: sampler — every visible element consumes a semantic token", { x: 0.62, y: 7.05, w: 10, h: 0.25, fontFace: FONT, fontSize: 9, color: C.textSecondary, margin: 0 });

const outFile = path.join(outDir, `theme-sampler-${themeKey}.pptx`);
pptx.writeFile({ fileName: outFile }).then(() => console.log(`Wrote ${outFile}`));
