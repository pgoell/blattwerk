---
type: Reference
title: "Block: magischesquadrat"
description: "The magic squares (Magische Quadrate): 3×3 or 5×5 squares where every row, column and both diagonals have the same sum, the Zielzahl; which cells are given, and optionally the Zielzahl above."
tags: [block, magischesquadrat]
covers: [magischesquadrat]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T16:56:43Z }
---

# magischesquadrat

The magic squares (Magische Quadrate): 3×3 or 5×5 squares where every row, column and both diagonals have the same sum, the Zielzahl; which cells are given, and optionally the Zielzahl above.

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
| count | number | 1 to 4 | yes | Number of magic squares on the sheet, side by side in rows of `columns`. Default 2. |
| columns | number | 1 to 3 | yes | Number of squares per row. Default 2. |
| size | number | `3`, `5` | yes | Cells per side: 3 (a 3×3 square) or 5 (a 5×5 square). Default 3. |
| max | number | 9 to 9999 | yes | The Zahlenraum, the largest number in a drawn square: 20, 100, 1000 or any whole number from 9 (3×3) or 25 (5×5) to 9999. A 5×5 with a smaller value gives 100. Default 20. |
| given | number | 2 to 24 | yes | The Schwierigkeit: how many cells are given on the pupils' sheet; the others are to fill in. 2 to 8 for a 3×3, 6 to 24 for a 5×5. With 3 or more (3×3) or 15 or more (5×5), or one fewer with showSum, the given cells allow exactly one solution; with fewer the key says that other solutions are right too. Default 4 (3×3) or 15 (5×5). |
| showSum | boolean |  | yes | Whether the Zielzahl, the sum of every row, column and diagonal, prints above each square ("Zielzahl: 15"). Default false. |
| seed | number |  | yes | Seed for the random squares. The same seed always gives the same squares. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [square index from 0, row from 1, column from 1, value 0 to 9999]. A square with typed numbers shows exactly its typed cells; the others are worked out from them. A square whose typed numbers fit no magic square is marked wrong and its key shows no answers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "magischesquadrat", "props": {}}
```
