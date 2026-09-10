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
  addCard, addAccentBar, addBullets, addStatCard, writeDeck,
};
