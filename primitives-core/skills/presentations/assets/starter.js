"use strict";
// Editable example content. Replace these illustrative figures and sources before delivery.
const path = require("node:path");
const { createDeck, addSlide, addKicker, addTitle, addFooter, addCard, addAccentBar, addBullets, addStatCard, writeDeck } = require("./deck-kit/deck-kit");
const type = "__TYPE__";
const topics = {
  status: {
    topic: "Pilot delivery readiness",
    purpose: "Purpose: decide whether delivery can start a limited pilot.",
    scope: "Scope: two pilot teams and the first review period.",
    conclusion: "Delivery is ready for a limited pilot",
    evidence: "The pilot starts with two teams",
    next: "The next review decides whether to expand",
    stat: { value: "2 teams", label: "Pilot scope", detail: "A small rollout provides feedback before expansion." },
  },
  advisor: {
    topic: "Pilot distribution channel",
    purpose: "Purpose: ask for one introduction to a distribution partner.",
    scope: "Scope: a wider trial built on repeat pilot usage.",
    conclusion: "The pilot needs a distribution partner",
    evidence: "Repeat usage supports a wider trial",
    next: "One introduction would test the channel",
    stat: { value: "Repeat use", label: "Wider trial scope", detail: "Repeat pilot usage is the basis for a wider trial." },
  },
  client: {
    topic: "Payment-difference review pilot",
    purpose: "Purpose: agree to start the pilot with your team.",
    scope: "Scope: one reporting period and a traceable review packet.",
    conclusion: "Your team can review every payment difference",
    evidence: "The pilot provides a traceable review packet",
    next: "Start with one reporting period",
    stat: { value: "1 period", label: "Pilot scope", detail: "One reporting period tests the review packet before expansion." },
  },
}[type];
const deck = createDeck({ author: "Presentation author", title: topics.topic, theme: type === "status" ? "carbon-white" : "actuarial-signal", fontFace: "Arial" });
const C = deck.colors;
{
  const slide = addSlide(deck);
  addKicker(deck, slide, `${type} readout`, { y: 0.9 });
  addTitle(deck, slide, topics.topic, { y: 1.35, size: 36, h: 0.8 });
  slide.addText([
    { text: topics.purpose, options: { breakLine: true, paraSpaceAfter: 8 } },
    { text: topics.scope },
  ], { x: deck.MX, y: 2.4, w: deck.CW, h: 1.1, fontFace: deck.fontFace, fontSize: 18, color: C.textSecondary, margin: 0, valign: "top" });
  addCard(deck, slide, { x: deck.MX, y: 4.2, w: deck.CW, h: 1.6 });
  addAccentBar(deck, slide, { x: deck.MX, y: 4.2, h: 1.6 });
  slide.addText("BOTTOM LINE", { x: deck.MX + 0.35, y: 4.4, w: deck.CW - 0.6, h: 0.3, fontFace: deck.fontFace, fontSize: 11, bold: true, charSpacing: 3, color: C.accentPrimary, margin: 0 });
  slide.addText(topics.conclusion, { x: deck.MX + 0.35, y: 4.8, w: deck.CW - 0.6, h: 0.7, fontFace: deck.fontFace, fontSize: 26, bold: true, color: C.textPrimary, margin: 0, valign: "top" });
  addFooter(deck, slide, "Source: illustrative package example");
  slide.addNotes("Opening: name the topic, the decision or action asked for and the scope, then give the bottom line. All figures are illustrative.");
}
{
  const slide = addSlide(deck);
  addKicker(deck, slide, "Evidence");
  addTitle(deck, slide, topics.conclusion);
  slide.addText(`${topics.evidence}.`, { x: deck.MX, y: 1.65, w: deck.CW, h: 0.5, fontFace: deck.fontFace, fontSize: 16, color: C.textSecondary, margin: 0, valign: "top" });
  addStatCard(deck, slide, { x: deck.MX, y: 2.3, w: 3.6, h: 2.5, ...topics.stat });
  slide.addChart(deck.pptx.ChartType.bar, [{ name: "Weekly reviews", labels: ["Week 1", "Week 2", "Week 3"], values: [8, 12, 18] }], {
    x: 4.8, y: 2.25, w: 7.7, h: 3.7, catAxisLabelFontFace: deck.fontFace, valAxisLabelFontFace: deck.fontFace,
    chartColors: [C.dataPrimary], showLegend: false, showTitle: false, showValue: true,
    valAxisMinVal: 0, valAxisMaxVal: 20, valAxisMajorUnit: 5, valAxisTitle: "Weekly reviews", valAxisTitleFontFace: deck.fontFace, catAxisLabelColor: C.textPrimary, valAxisLabelColor: C.textSecondary,
  });
  addFooter(deck, slide, "Source: illustrative weekly review counts; editable native chart");
  slide.addNotes("Evidence: 8, 12 and 18 are demonstration data, not measured customer results.");
}
{
  const slide = addSlide(deck);
  addKicker(deck, slide, "Next step");
  addTitle(deck, slide, topics.next);
  addBullets(deck, slide, ["Agree on the pilot owner and the data to review.", "Record the acceptance criteria before work starts.", "Review the result together before expanding the scope."], { x: deck.MX, y: 2.6, w: deck.CW, h: 2.8, size: 22, gap: 24 });
  addFooter(deck, slide, "Source: illustrative pilot proposal");
  slide.addNotes("Close: name the responsible person, date and decision criteria in the real deck.");
}
writeDeck(deck.pptx, path.join(__dirname, "__SLUG__.pptx"))
  .then(console.log).catch(error => { console.error(error.message); process.exitCode = 1; });
