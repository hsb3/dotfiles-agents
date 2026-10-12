"use strict";

const fs = require("node:fs");
const path = require("node:path");
const pptxgen = require("pptxgenjs");
const { THEMES } = require("./theme-tokens");

const W = 13.33;
const H = 7.5;
const MX = 0.65;
const CW = W - 2 * MX;
const FOOTER_Y = 7.05;

function createDeck({ author, title, theme = "carbon-white", fontFace = "Avenir Next" }) {
  if (!Object.hasOwn(THEMES, theme)) throw new Error(`Unknown theme: ${theme}`);
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = author;
  pptx.title = title;
  pptx.theme = { headFontFace: fontFace, bodyFontFace: fontFace, lang: "en-US" };
  return { pptx, colors: THEMES[theme], fontFace, W, H, MX, CW, FOOTER_Y };
}

function addSlide(deck, background = deck.colors.canvas) {
  const slide = deck.pptx.addSlide();
  slide.background = { color: background };
  return slide;
}

function addKicker(deck, slide, text, { y = 0.55, color = deck.colors.accentPrimary } = {}) {
  slide.addText(text.toUpperCase(), {
    x: deck.MX, y, w: deck.CW, h: 0.32, fontFace: deck.fontFace, fontSize: 11,
    bold: true, color, charSpacing: 3, margin: 0,
  });
}

function addTitle(deck, slide, text, { y = 0.92, size = 28, h = 0.95, color = deck.colors.textPrimary } = {}) {
  slide.addText(text, {
    x: deck.MX, y, w: deck.CW, h, fontFace: deck.fontFace, fontSize: size,
    bold: true, color, margin: 0, valign: "top",
  });
}

function addFooter(deck, slide, left, right = "") {
  slide.addText(left, {
    x: deck.MX, y: deck.FOOTER_Y, w: deck.CW - (right ? 2.6 : 0), h: 0.3,
    fontFace: deck.fontFace, fontSize: 9, color: deck.colors.textSecondary, margin: 0,
    valign: "middle",
  });
  if (right) {
    slide.addText(right, {
      x: deck.W - deck.MX - 2.6, y: deck.FOOTER_Y, w: 2.6, h: 0.3,
      fontFace: deck.fontFace, fontSize: 9, color: deck.colors.textSecondary, margin: 0,
      align: "right", valign: "middle",
    });
  }
}

function addCard(deck, slide, { x, y, w, h, fill = deck.colors.surface, shadow = true }) {
  slide.addShape(deck.pptx.ShapeType.rect, {
    x, y, w, h, fill: { color: fill }, line: { color: deck.colors.border, width: 0.75 },
    shadow: shadow ? { type: "outer", color: deck.colors.shadow, blur: 4, offset: 1, angle: 135, opacity: 0.1 } : undefined,
  });
}

function addAccentBar(deck, slide, { x, y, h, w = 0.07, color = deck.colors.accentPrimary }) {
  slide.addShape(deck.pptx.ShapeType.rect, { x, y, w, h, fill: { color }, line: { color, transparency: 100 } });
}

function addBullets(deck, slide, items, { x, y, w, h, size = 14, gap = 10, color = deck.colors.textPrimary } = {}) {
  const runs = items.map((text, index) => ({
    text,
    options: { bullet: { code: "2022", indent: 14 }, breakLine: index < items.length - 1, paraSpaceAfter: gap },
  }));
  slide.addText(runs, { x, y, w, h, fontFace: deck.fontFace, fontSize: size, color, margin: 0, valign: "top" });
}

function addStatCard(deck, slide, { x, y, w, h, value, label, detail, accent = deck.colors.accentPrimary }) {
  addCard(deck, slide, { x, y, w, h });
  addAccentBar(deck, slide, { x, y, h, color: accent });
  slide.addText(value, { x: x + 0.3, y: y + 0.18, w: w - 0.5, h: 0.58, fontFace: deck.fontFace, fontSize: 23, bold: true, color: accent, margin: 0 });
  slide.addText(label.toUpperCase(), { x: x + 0.3, y: y + 0.82, w: w - 0.5, h: 0.25, fontFace: deck.fontFace, fontSize: 10, bold: true, charSpacing: 1.5, color: deck.colors.textSecondary, margin: 0 });
  slide.addText(detail, { x: x + 0.3, y: y + 1.13, w: w - 0.5, h: h - 1.28, fontFace: deck.fontFace, fontSize: 11.5, color: deck.colors.textPrimary, margin: 0, valign: "top" });
}

// Nothing in this package can measure an image file (image-size is a stub), so callers pass pixels.
function fitImage(srcW, srcH, box, mode = "contain") {
  if (![srcW, srcH].every(v => Number.isFinite(v) && v >= 1)) {
    throw new Error(`srcW and srcH must be the image's pixel size (>= 1), got ${srcW} x ${srcH}: nothing here can measure the file`);
  }
  if (!(box.w > 0 && box.h > 0)) throw new Error(`Image box needs w and h > 0, got ${box.w} x ${box.h}`);
  if (mode !== "contain" && mode !== "cover") throw new Error(`Image mode must be contain or cover, got ${mode}`);
  const scale = (mode === "contain" ? Math.min : Math.max)(box.w / srcW, box.h / srcH);
  const w = srcW * scale, h = srcH * scale;
  if (mode === "contain") {
    return { x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h, crop: { l: 0, r: 0, t: 0, b: 0 } };
  }
  const l = (1 - box.w / w) / 2, t = (1 - box.h / h) / 2;
  return { x: box.x, y: box.y, w: box.w, h: box.h, crop: { l, r: l, t, b: t } };
}

function addImageFit(deck, slide, { path: file, data, srcW, srcH, x, y, w, h, mode = "contain", name, altText, ...rest }) {
  if (!file === !data) throw new Error("addImageFit needs exactly one of path or data");
  if (!name) throw new Error("addImageFit needs a name; the picture is named img:<name>");
  const fit = fitImage(srcW, srcH, { x, y, w, h }, mode);
  // PptxGenJS writes the file path into descr when altText is absent, which leaks it into the deck.
  const image = { ...rest, ...(file ? { path: file } : { data }), altText: altText || name, objectName: `img:${name}` };
  // pptxgenjs "contain" pads with negative srcRect across the whole box, so place the fitted size.
  if (mode === "contain") slide.addImage({ ...image, x: fit.x, y: fit.y, w: fit.w, h: fit.h });
  // pptxgenjs "cover" reads w/h as the source's own size; numbers >= 100 stay EMU, keeping the ratio exact.
  else slide.addImage({ ...image, x, y, w: srcW * 1000, h: srcH * 1000, sizing: { type: "cover", w, h } });
  return fit;
}

// OOXML extents cannot be negative: direction lives in flipH/flipV, never in a negative w/h.
function addLine(deck, slide, x1, y1, x2, y2, opts = {}) {
  slide.addShape(deck.pptx.ShapeType.line, {
    line: { color: deck.colors.textPrimary, width: 1 }, ...opts,
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1,
  });
}

// The three statuses differ by shape, not only colour: check, cross, circled question mark.
function addStatusIcon(deck, slide, status, { x, y, size = 0.32 }) {
  const C = deck.colors;
  const at = (fx, fy) => [x + fx * size, y + fy * size];
  const stroke = color => ({ line: { color, width: size * 8 }, objectName: `icon:${status}` });
  if (status === "pass") {
    addLine(deck, slide, ...at(0.12, 0.52), ...at(0.4, 0.8), stroke(C.positive));
    addLine(deck, slide, ...at(0.4, 0.8), ...at(0.9, 0.18), stroke(C.positive));
  } else if (status === "fail") {
    addLine(deck, slide, ...at(0.18, 0.18), ...at(0.82, 0.82), stroke(C.negative));
    addLine(deck, slide, ...at(0.82, 0.18), ...at(0.18, 0.82), stroke(C.negative));
  } else if (status === "unknown") {
    slide.addShape(deck.pptx.ShapeType.ellipse, { x, y, w: size, h: size, line: { color: C.textSecondary, width: size * 5 }, objectName: "icon:unknown" });
    slide.addText("?", {
      x, y, w: size, h: size, fontFace: deck.fontFace, fontSize: Math.round(size * 44), bold: true, objectName: "icon:unknown",
      color: C.textSecondary, align: "center", valign: "middle", margin: 0,
    });
  } else {
    throw new Error(`Status must be pass, fail or unknown, got ${status}`);
  }
}

async function writeDeck(pptx, outputPath) {
  const absolute = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(absolute), { recursive: true });
  if (fs.existsSync(absolute) && (!fs.lstatSync(absolute).isFile() || fs.lstatSync(absolute).isSymbolicLink())) {
    throw new Error(`Output must be a regular file: ${absolute}`);
  }
  const temporary = fs.mkdtempSync(path.join(path.dirname(absolute), ".deck-"));
  try {
    const file = path.join(temporary, "deck.pptx");
    await pptx.writeFile({ fileName: file });
    fs.renameSync(file, absolute);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
  return absolute;
}

module.exports = {
  W, H, MX, CW, FOOTER_Y, createDeck, addSlide, addKicker, addTitle, addFooter,
  addCard, addAccentBar, addBullets, addStatCard, fitImage, addImageFit, addLine, addStatusIcon, writeDeck,
};
