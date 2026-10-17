---
type: Reference
title: "Block: ruling"
description: "The Lineatur's kind and colour, and the words it may show on its rows."
tags: [block, ruling]
covers: [ruling]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-17T20:43:14Z }
---

# ruling

The Lineatur's kind and colour, and the words it may show on its rows.

Every block has the box fields of the [page model](../page-model.md). This page lists the rest.

# Schema

## Block fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| id | string | yes | Unique id of the block on its sheet. |
| x | number | yes | Distance in mm from the left edge of the page to the left edge of the block, before any turn. The page is 210 mm wide upright. |
| y | number | yes | Distance in mm from the top edge of the page to the top edge of the block, before any turn. The page is 297 mm tall upright. |
| w | number | yes | Width of the block in mm, before any turn. |
| h | number | yes | Height of the block in mm, before any turn. |
| z | number | yes | Stacking order on the page: a block with a higher z lies over one with a lower z. |
| locked | boolean | yes | True when the block is locked, so the editor does not move, resize or turn it. Absent means not locked. |
| mark | string | no | Numbering printed before the block on paper, such as "1.", "a)" or "(1)", or a symbol's code. Absent means none. |
| group | list of string | no | The ids of the groups the block belongs to, the outermost group first. Absent when the block is in no group. |
| angle | number | no | Turn of the block about its centre, in degrees clockwise. 0 is upright, 90 a quarter turn. Absent means 0. |
| flipX | boolean | no | True mirrors the block from left to right inside its box, so a picture or a symbol faces the other way. Absent means not mirrored. |
| flipY | boolean | no | True mirrors the block from top to bottom inside its box. Absent means not mirrored. |
| keep | boolean | no | True keeps the width in proportion to the height when the block is resized, as PowerPoint's Lock aspect ratio does. Absent means off. |

## Props

| Prop | Type | Values | Required | Description |
| --- | --- | --- | --- | --- |
| kind | string | `l1`, `l2`, `l3`, `l4`, `lines`, `k5`, `k7` | yes | The ruled pattern (Lineatur) kind: its line pattern and school level, one of the RULINGS keys, such as "l1" for Lineatur 1 (Klasse 1). Required. |
| color | string |  | yes | The colour of the lines, as a six digit hex colour such as #1a56db. |
| text | string |  | no | Text printed on the lines, in the block's font. Left out, the lines stand alone. |
| font | string | `andika`, `nord`, `sued`, `grund`, `urff`, `va`, `sas`, `la` | no | The font of the text printed on the lines. Left out, the default font is used. |
| trace | boolean or string | `outline` or `dotted` | no | Trace text the pupil writes over: true for grey, "outline" or "dotted". Left out, no trace. |
| fade | string | `row`, `rows` | no | How the trace fades as the pupil writes on: "row" along each row, "rows" from row to row. Left out, it does not fade. |
| list | string | `copy`, `trace`, `row`, `fold` | no | Takes its words from the sheet's words to learn (Lernwörter), one to a row, in the way the mode says. Left out, no list. |
| from | number | at least 0 | no | Index of the first word to learn the block shows, counted from 0, so a ruled pattern run on over several pages picks up where the last one stopped. Left out, 0. |
| folds | number | 2 to 3 | no | Number of empty columns to write in on a fold sheet (Knickblatt), after the words. 2 or 3. Any other value gives 2. |
| house | boolean |  | no | Draws a house on the lines of a kind with zones, marking its room, roof and cellar. Left out, no house. |
| houseTint | string | `room`, `all` | no | Tints the house: "room" for the room alone, "all" for roof, room and cellar. Left out, the house is not tinted. |
| band | boolean |  | no | Whether the middle band between the lines is tinted. Left out, the kind's own default applies. |
| bandColor | string |  | no | The band's colour, as a six digit hex colour such as #ffe066. Left out, the line colour, paler, is used. |
| syllables | boolean |  | no | Draws an arc under each syllable of the text on the lines or in the squares. Left out, no arcs. |
| breaks | object |  | no | The word breaks set by hand for the text on the lines or in the squares. They win over the sheet's breaks. Left out, the sheet's apply. |
| tints | list of string |  | no | Two colours, such as #1a56db and #e02424, that colour the syllables in turn, on the lines or in the squares. Left out, no colour. |
| tintsAcross | boolean |  | no | Carries the colour turn on from word to word, instead of starting again with each word. On the lines or in the squares. Left out, it starts again. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "ruling", "props": {}}
```
