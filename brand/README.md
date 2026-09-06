# Firsthand brand

## Marks

| File | Use |
|---|---|
| `firsthand-mark.svg` | Four rules, the third solid lapis. Primary mark, 20px and up |
| `firsthand-mark-mono.svg` | The same four rules entirely in `currentColor`, for single-colour contexts |
| `firsthand-icon.svg` | Three rules. Below 20px, and for favicons |
| `firsthand-app-icon.svg` | The icon on a graphite field, corners rounded 27 units in a 120 box |
| `*-1024.png` | Raster exports for avatars, OG cards and anywhere SVG is not accepted |

Four claims, one witnessed. Three rules are hairline outlines and one is solid,
which is the same grammar the token file already uses: `.stone--thin` is a
hairline outline and `.stone--grounded` is solid lapis. The mark is three thin
observations and one grounded one, so nothing in the design system is special
cased for it.

The solid rule is the only element that ever takes a colour other than the
mark's own, and it carries the standing. `FirsthandMark` in
`apps/web/src/components/firsthand-mark.tsx` drives it from the `standing` prop.

**Do not** tilt the rules, arrange them as a pyramid, make the widths
monotonic, fill the outlined rules, place the mark on any field other than
chalk, paper, basalt or graphite, or apply a gradient to it. The widths are
ragged because a record is uneven, and straightening them would say something
about the evidence that is not true.

## Colour

Full token set in `firsthand-tokens.css`, which is a copy of the file the app
loads at `apps/web/src/styles/tokens.css`. The rule that makes it a brand:
**colour means evidence.** Lapis `#223FA6` only appears where Firsthand can point
at an observation it holds. Oxide `#8C2130` only where its own record
contradicts a claim. `thin`: Firsthand has nothing, is rendered colourless on
purpose.

## Type

Newsreader 400 (display, never bold) · Geist (text) · Geist Mono (all data,
labels, eyebrows, buttons and code). Italic is reserved for the verdict line and
appears nowhere else in the product.
