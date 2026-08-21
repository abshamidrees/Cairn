# Cairn, logo prompts for Nano Banana 2 / GPT Image 2

The SVG I built is attached and is production-ready. These prompts are for exploring alternatives before you commit. Run them, compare against `cairn-mark.svg`, keep whichever is better.

**Before you start, two warnings about image models and logos.** They cannot produce clean vectors, you will get a raster you have to redraw, so treat every output as a *sketch to trace*, never as a shippable asset. And they render text badly, so generate the **mark only** and set the wordmark in Newsreader yourself. Any prompt that asks for the word "Cairn" inside the image will come back misspelled about half the time.

Generate at 1:1, request a plain background, and ask for a single mark centred with margin.

---

## Prompt 1, the direct one (closest to the attached SVG)

> A minimalist vector logo mark of a small stack of five flat stones, viewed straight on from the front, arranged as a cairn trail marker. Each stone is a horizontal rounded rectangle with a different width and a slight 1-3 degree tilt, hand-stacked and slightly irregular rather than a neat symmetrical pyramid. The widest stone is at the bottom. One stone in the middle of the stack is wider than the stone directly beneath it, creating a small overhang. Even hairline gaps between all stones. Solid near-black fill, no outlines, no gradients, no shadows, no texture, no perspective. Flat 2D geometric icon on a plain pale off-white background. Centred with generous margin. Corporate identity mark, Swiss design, high contrast, crisp edges.

**Negative / avoid:** text, letters, words, 3D rendering, realistic rock texture, drop shadows, gradients, pyramid, wedding cake, children's stacking toy, perfectly symmetrical, mountain, landscape, background scenery.

---

## Prompt 2, the mineral one (more character, less geometric)

> A flat vector icon of five stacked flat river stones forming a cairn, seen edge-on. The stones are simplified organic silhouettes, slightly uneven, softly rounded, each one a distinct width and thickness, tilted at small angles as if balanced by hand. Bottom stone widest and flattest, top stone smallest. Thin consistent gaps between stones. Single solid dark ink colour, pure silhouette, no interior detail, no outline, no shading. Flat 2D, geometric but not mechanical. Plain pale limestone background. Centred, generous margin. Designed as an app icon at small size, must stay legible at 16 pixels.

**Negative / avoid:** text, 3D, photorealism, texture, shadow, gradient, noise, sand, water, beach, zen garden, spa, wellness.

---

## Prompt 3, the instrument one (takes the concept somewhere else)

> A flat vector logo mark combining a cairn and a data chart. Five horizontal bars of varying widths stacked vertically with even gaps, each bar tilted 1-3 degrees at a different angle so the stack reads as hand-balanced stones rather than a bar chart. The widths do not decrease evenly, one bar is wider than the one below it. Four bars in solid near-black, the top bar in a deep ultramarine blue. Flat 2D, no outlines, no gradients, no shadows. Plain pale cool grey-white background. Centred with margin. Precise, engineered, archival. Technical identity mark for a data infrastructure company.

**Negative / avoid:** text, axes, gridlines, labels, 3D, glossy, gradient, glow, tech-startup cliché, circuit board, network graph, brain, chip.

---

## Prompt 4, the wildcard (only if the first three feel safe)

> A flat vector logo mark: a cairn of five stones where the stones are drawn as horizontal slices through rock strata, each slice a different width and tilt, stacked into a small balanced tower. Geological cross-section rendered as a minimal identity mark. Single dark ink colour with one slice picked out in deep blue. Absolutely flat, no gradients, no texture, no shadow, no perspective. Plain pale background, centred, generous margin. Editorial, archival, precise, like a mark from a geological survey or a scientific journal.

**Negative / avoid:** text, realistic geology illustration, colour banding, earth tones, brown, orange, terracotta, 3D, shading.

---

## How to judge the outputs

Score each candidate against these five, in order. The attached SVG passes all five.

1. **Does it read as a cairn and not a pyramid?** If the widths decrease evenly and everything is centred, it is a stacking toy. You need at least one overhang and at least two horizontal offsets.
2. **Does it survive at 16px?** Shrink it. If the gaps close up, the stones need to be fewer or the gaps larger. This is why the shipped set has a separate three-stone icon for small sizes.
3. **Is it one flat colour plus at most one accent?** Anything with a gradient, a shadow or a texture is unusable, it will not work on basalt, it will not work in a favicon, and it will not print.
4. **Does the top stone work as a status light?** The keystone carries the standing, so it has to be visually separable from the rest of the stack at a glance.
5. **Would it still be legible if you rotated it 5 degrees?** Marks with a strong horizontal silhouette survive; fussy ones do not.

If a generated mark beats the SVG on 1 through 5, redraw it as a vector in Figma or Illustrator, do not ship the raster. Export at `viewBox="0 0 120 120"` with `fill="currentColor"` so it drops straight into the `CairnMark` component in part 3 of the brief.
