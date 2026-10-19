---
type: Reference
title: "Block: malquadrat"
description: "The Malquadrate (Einmaleins-Rätsel): row numbers down the left, column numbers along the top, the products (or sums) inside, the sum of each row and column outside and the total in the corner; which numbers are given."
tags: [block, malquadrat]
covers: [malquadrat]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T19:45:12Z }
---

# malquadrat

The Malquadrate (Einmaleins-Rätsel): row numbers down the left, column numbers along the top, the products (or sums) inside, the sum of each row and column outside and the total in the corner; which numbers are given.

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
| count | number | 1 to 4 | yes | Number of Malquadrate on the sheet, side by side in rows of `columns`. Default 2. |
| columns | number | 1 to 3 | yes | Number of Malquadrate per row. Default 2. |
| size | number | 2 to 4 | yes | Inner cells per side: the square has size × size products, size row numbers down the left and size column numbers along the top, a sum after each row and below each column, and the total in the corner. Default 3. |
| op | string | `*`, `+` | yes | The Rechenart: "*" (Mal: each inner cell is row number times column number) or "+" (Plus: row number plus column number). Default "*". |
| reihen | list of number |  | yes | Mal only: the Einmaleins-Reihen the column numbers are drawn from, distinct numbers 1 to 10. The row numbers are 2 to 10. Default [2, 3, 4, 5, 6, 7, 8, 9]. |
| max | number |  | yes | Plus only: the Zahlenraum, 20, 100 or 1000: every row and column number is at most half of it, so every inner cell is at most max. Default 20. |
| task | string | `factors`, `mixed`, `knobel` | yes | The Aufgabentyp: "factors" every row and column number is given and the rest is to fill; "mixed" some row and column numbers are hidden and one inner cell each is given instead; "knobel" as mixed, but one hidden row number can only be found through its given row sum. Every task has one solution. Default "factors". |
| seed | number |  | yes | Seed for the random squares. The same seed always gives the same squares. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [square index from 0, row 0 to 5, column 0 to 5, value 0 to 9999]. Row 0 holds the column numbers, column 0 the row numbers, row and column size + 1 the sums, and [s, size + 1, size + 1] the total. A square with typed numbers shows exactly its typed cells; the others are worked out from them. A square whose typed numbers do not fit together is marked wrong and its key shows no answers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "malquadrat", "props": {}}
```
