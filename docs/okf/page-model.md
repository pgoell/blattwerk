---
type: Explanation
title: Page model
description: How a Blattomat sheet is laid out, A4 in mm, the box of each block, z order, pages, guide lines and the grid.
tags: [page, layout, doc]
covers: [text, shape, ruling, name, points, symbol, image, maths, table, suchsel, zahlenmauer, zahlenhaus, zahlenkette, pfeilbild, operatorfeld, rechenrad, rechendreieck, zahlenstrahl, hunderterfeld, uhr, selbstkontrolle]
generated: { by: "human:pgoell", at: 2026-10-19T10:20:00Z }
---

# Page model

A sheet is a `doc`: a list of pages, and what the pages share.

```json
{"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
```

## The paper

Every page is A4. Upright it is 210 mm wide and 297 mm tall; `landscape: true` lays it on its side, 297 by 210 mm, for the whole doc or for one page. Every length in a doc is in mm, from the paper's top left corner. There is no unit field and no pixel.

The printable area keeps 15 mm from each edge: upright, x from 15 to 195 and y from 15 to 282. A block outside it gets the warning `leaves the page's printable area`.

## The box of a block

Every block has the same box fields, whatever its type:

| Field | Meaning |
|---|---|
| `id` | A string unique on the sheet. Other blocks name it, such as a Selbstkontrolle's `links`. |
| `type` | One of the 16 [block types](blocks/index.md). |
| `x`, `y` | The top left corner in mm. |
| `w`, `h` | Width and height in mm. |
| `z` | Stacking order, 1 and up; a higher z lies on top. |
| `locked` | `false`. A locked block is one the teacher fixed in place; leave it where it is. |
| `props` | The type's own settings, on the type's page under [blocks](blocks/index.md). |

Some blocks grow to fit what they hold: a maths block takes the height its exercises need, a Lineatur linked to the Lernwörter grows a row per word. `add_block` gives the box the block ends up with; place the next block from that answer, not from what you asked for.

## No overlaps

Blocks must not meet. Stack them down the page: the next block's `y` is the last block's `y + h + 5`. Side by side, the next `x` is the last `x + w + 5`. A full-width block is `x: 15, w: 180`. The answer of each write names every overlap (`overlaps block <id>`); fix it with `move_block` before you go on.

## Pages

`pages` is in print order. A page holds its `blocks` and may set its own `landscape`, `grid` and `guides`. When the content does not fit on one page, add a page (`add_page`) and go on there at `y: 15`; do not shrink the font below what a child reads.

## Guides and grid

`guides` holds guide lines in mm: `x` the upright ones from the left edge, `y` the flat ones from the top edge. `grid` is the cell of a snap grid in mm, 0 for none. Both help the teacher place blocks in the editor; neither prints. Leave them empty unless asked.

## Lernwörter

`doc.words` holds the sheet's word list, one word to an entry. A Lineatur with `list` set shows them, one to a row; `set_words` changes the list and every linked block with it. A linked Lineatur with `syllables: true` draws a bow under each syllable. See the recipe [Lernwörter mit Lineatur und Silbenbögen](recipes/lernwoerter-silbenboegen.md).
