# Prompting Nano Banana

Prompt-craft patterns for the Nano Banana family (Gemini-native image models). These are
model-behavior notes, independent of transport — they apply whether you call
`gemini-2.5-flash-image`, `gemini-3.1-flash-image-preview`, or `gemini-3-pro-image-preview`.

## What actually works

**Subject-first declarative grammar.** Lead with the primary subject, then action,
environment, style, and camera direction. Front-load the subject; trail with directives.

> A cinematic close-up portrait of a woman standing under neon lights in rainy Tokyo,
> shallow depth of field, reflective wet streets, ultra-detailed, realistic skin texture

**Quote in-image text literally.** For legible typography, quote the exact characters and
specify placement and font style — don't describe it indirectly.

> The label reads "AURA" in clean bold sans-serif, centered, white on black

Say `The headline "Brewed Quietly" in the top-right`, not "with the brand name on it".
Un-quoted in-image text renders unpredictably. `gemini-3-pro-image-preview`
(`nanobanana-pro`) is the strongest tier for legible multi-step text.

**Anchor one or two styles, not four.** "minimalist + ornate + retro + cyberpunk" cancels
out. Pick one or two style anchors and commit.

**Edit, don't re-describe, a stable subject.** To keep a subject's identity across images,
pass the reference with `--input-image` (repeatable for multi-reference) rather than trying
to pin identity in words. Verbal identity descriptions drift between generations.

**Ground on the web sparingly.** Add `--search` (or `GEMINI_USE_SEARCH=true`) only when the
prompt names current events or real entities that need fresh context. It adds latency and
cost; leave it off by default.

## Sizing and iteration

- Draft at a small `--size` (e.g. `512` on `nanobanana-2`), promote the winner to `2K`/`4K`.
- Use `batch` for ideation rounds (multiple variants of one prompt) before committing to a
  final render.
- Match `--ratio` to the destination surface up front (`9:16` / `4:5` for vertical/social,
  `16:9` / `21:9` for wide), rather than cropping after.

## Anti-patterns

- Describing a stable subject identity in prose across renders — use `--input-image` editing.
- Un-quoted in-image text — quote the literal characters.
- Stacking conflicting style keywords — anchor one or two.
- Enabling web grounding by default — reserve it for genuinely current/real-entity prompts.

## Sample prompts

**Cinematic portrait:**

```
A cinematic close-up portrait of a woman standing under neon lights in rainy Tokyo,
shallow depth of field, reflective wet streets, ultra-detailed, realistic skin texture
```

**Brand-asset card with quoted text (16:9):**

```
A minimalist product card: a matte black ceramic mug centered on a soft warm-grey paper
background, rim highlight from upper-left, the headline "Brewed Quietly" in clean bold
sans-serif top-right, balanced negative space below, clean studio lighting
```

**Vertical platform-native (9:16):**

```
A vertical hero for a wellness brand: a single ceramic teacup on a linen runner, soft
morning side-light, the words "Slow Down" in hand-drawn serif large at the top, gentle
steam rising, neutral color palette, uncluttered
```
