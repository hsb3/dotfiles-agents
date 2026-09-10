"use strict";
// Editable example content. Replace these illustrative figures and sources before delivery.
const path = require("node:path");
const { createDeck, addSlide, addKicker, addTitle, addFooter, addBullets, addStatCard, writeDeck } = require("./deck-kit/deck-kit");
const type = "__TYPE__";
const topics = {
  status: ["Delivery is ready for a limited pilot", "The pilot starts with two teams", "The next review decides whether to expand"],
  advisor: ["The pilot needs a distribution partner", "Repeat usage supports a wider trial", "One introduction would test the channel"],
  client: ["Your team can review every payment difference", "The pilot provides a traceable review packet", "Start with one reporting period"],
};
const deck = createDeck({ author: "Presentation author", title: topics[type][0], theme: type === "status" ? "carbon-white" : "actuarial-signal", fontFace: "Arial" });
const C = deck.colors;
{
  const slide = addSlide(deck);
  addKicker(deck, slide, `${type} readout`, { y: 1.2 });
  addTitle(deck, slide, topics[type][0], { y: 1.8, size: 36, h: 1.6 });
  addBullets(deck, slide, ["This example shows the decision, its evidence and the next step.", "Replace the example statements with verified source material."], { x: deck.MX, y: 4.0, w: deck.CW, h: 1.5, size: 20 });
  addFooter(deck, slide, "Source: illustrative package example");
  slide.addNotes("Opening: explain the audience and the decision. All figures are illustrative.");
}
{
  const slide = addSlide(deck);
  addKicker(deck, slide, "Evidence");
  addTitle(deck, slide, topics[type][1]);
  addStatCard(deck, slide, { x: deck.MX, y: 2.3, w: 3.6, h: 2.5, value: "2 teams", label: "Pilot scope", detail: "A small rollout provides feedback before expansion." });
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
  addTitle(deck, slide, topics[type][2]);
  addBullets(deck, slide, ["Agree on the pilot owner and the data to review.", "Record the acceptance criteria before work starts.", "Review the result together before expanding the scope."], { x: deck.MX, y: 2.6, w: deck.CW, h: 2.8, size: 22, gap: 24 });
  addFooter(deck, slide, "Source: illustrative pilot proposal");
  slide.addNotes("Close: name the responsible person, date and decision criteria in the real deck.");
}
writeDeck(deck.pptx, path.join(__dirname, "__SLUG__.pptx"))
  .then(console.log).catch(error => { console.error(error.message); process.exitCode = 1; });
