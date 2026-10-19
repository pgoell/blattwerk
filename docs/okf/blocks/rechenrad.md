---
type: Reference
title: "Block: rechenrad"
description: "The calculation wheels (Rechenräder): a centre with an operator and a number, and rings of segments where each ring's number worked with the centre gives the next ring's, and which ring or boxes are empty."
tags: [block, rechenrad]
covers: [rechenrad]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T10:15:39Z }
---

# rechenrad

The calculation wheels (Rechenräder): a centre with an operator and a number, and rings of segments where each ring's number worked with the centre gives the next ring's, and which ring or boxes are empty.

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
| count | number | 1 to 6 | yes | Number of Rechenräder on the sheet, side by side in rows of `columns`. Default 2. |
| columns | number | 1 to 3 | yes | Number of Rechenräder per row. Default 2. |
| rings | number | 2 to 3 | yes | The number rings around the centre: 2 (an inner and an outer ring) or 3 (inner, middle, outer). Each ring's number, worked with the centre, gives the next ring's. Default 2. |
| segments | number | 4 to 12 | yes | Segments per Rechenrad, the spokes of the wheel. Default 8. |
| max | number |  | yes | The Zahlenraum: the largest number the generator puts in a ring, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. |
| op | string | `+`, `-`, `*`, `:` | yes | The Rechenart of the centre: "+" (Plus), "-" (Minus), "*" (Mal) or ":" (Geteilt). "*" and ":" need max 20 or more, else "+". Default "+". |
| task | string | `outer`, `inner`, `middle`, `mixed` | yes | The Aufgabentyp: "outer" the outer ring is empty, "inner" the inner ring is empty (the pupils work back), "middle" the middle ring is empty (only with 3 rings, else "outer"), "mixed" one empty box per segment in a ring drawn at random. The centre always shows. Default "outer". |
| seed | number |  | yes | Seed for the random wheels. The same seed always gives the same wheels. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [wheel index from 0, ring from 0 (0 is the centre's number, 1 the inner ring), segment from 0 clockwise from the top (0 for the centre), value 0 to 9999]. Typed numbers win over the drawn ones; a wheel whose numbers do not fit its centre is marked wrong and its key shows no answers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "rechenrad", "props": {}}
```
