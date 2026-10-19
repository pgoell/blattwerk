---
type: Reference
title: "Block: zerlegungsfeld"
description: "The Zerlegungsfelder (Zehnerübergang in zwei Schritten): each task a + b with the split of b into the part to the full ten and the rest, then the two steps; which boxes are given."
tags: [block, zerlegungsfeld]
covers: [zerlegungsfeld]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T23:49:47Z }
---

# zerlegungsfeld

The Zerlegungsfelder (Zehnerübergang in zwei Schritten): each task a + b with the split of b into the part to the full ten and the rest, then the two steps; which boxes are given.

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
| count | number | 1 to 12 | yes | Number of tasks on the sheet, side by side in rows of `columns`. Default 6. |
| columns | number | 1 to 3 | yes | Number of tasks per row. Default 3. |
| op | string | `+`, `-` | yes | The Rechenart: "+" (Plus: 8 + 5 = 8 + 2 + 3) or "-" (Minus: 13 − 5 = 13 − 3 − 2). Default "+". |
| max | number |  | yes | The Zahlenraum, 20, 100 or 1000: the result of a Plus task and the first number of a Minus task are at most max. Default 20. |
| step | string | `zehner`, `hunderter` | yes | The Übergang: "zehner" (the first step reaches the full ten) or "hunderter" (the full hundred, with multiples of 10 such as 370 + 50; only with max 1000, else it acts as "zehner"). Default "zehner". |
| big | boolean |  | yes | Expert option: false draws a second number below the ten (or hundred) as in 8 + 5; true draws one of at least the ten (or hundred) as in 3 + 34 = 3 + 7 + 27. Default false. |
| task | string | `task`, `split`, `result` | yes | The Aufgabentyp, which boxes are given: "task" the first and the second number; "split" also the two parts of the split; "result" the first number and the result. The pupil fills the other boxes. Every drawn task has one solution. Default "task". |
| seed | number |  | yes | Seed for the random tasks. The same seed always gives the same tasks. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [task index from 0, position 0 to 5, value 0 to 9999]. Positions: 0 the first number, 1 the second number, 2 the result, 3 the left part of the split (to the full ten), 4 the right part, 5 the Zwischenergebnis (the full ten). A task with typed numbers shows exactly its typed boxes; the others are worked out from them. A task whose typed numbers do not fit is marked wrong and its key shows no answers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zerlegungsfeld", "props": {}}
```
