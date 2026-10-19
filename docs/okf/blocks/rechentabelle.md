---
type: Reference
title: "Block: rechentabelle"
description: "The calculation tables (Plus-, Minus-, Mal- and Geteilt-Tabellen): row values down the left, column values along the top, the operator in the corner, and each result cell the row value worked with the column value; which values and cells are given."
tags: [block, rechentabelle]
covers: [rechentabelle]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T12:29:34Z }
---

# rechentabelle

The calculation tables (Plus-, Minus-, Mal- and Geteilt-Tabellen): row values down the left, column values along the top, the operator in the corner, and each result cell the row value worked with the column value; which values and cells are given.

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
| count | number | 1 to 4 | yes | Number of Rechentabellen on the sheet, side by side in rows of `columns`. Default 2. |
| columns | number | 1 to 3 | yes | Number of Rechentabellen per row. Default 2. |
| rows | number | 2 to 10 | yes | Rows per table: the row values down the left side. Default 4. |
| cols | number | 2 to 10 | yes | Columns per table: the column values along the top. Default 4. |
| op | string | `+`, `-`, `*`, `:` | yes | The Rechenart in the corner: "+" (Plus), "-" (Minus, row value minus column value), "*" (Mal) or ":" (Geteilt, row value divided by column value; a cell with no whole answer is struck through). Default "+". |
| max | number |  | yes | Plus and Minus: the Zahlenraum, the largest number in the table, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. |
| carry | string | `none`, `required`, `either` | yes | Plus and Minus: the Übertrag of every cell: "none" no cell carries, "required" every cell carries at one place at least, "either" no rule. Default "either". |
| reihen | list of number |  | yes | Mal and Geteilt: the Einmaleins-Reihen, distinct numbers 1 to 10, as the column values. Default [2, 4, 5, 10]. |
| order | string | `related`, `random` | yes | Mal and Geteilt: the order of the Reihen along the top: "related" related Reihen side by side (1, 2, 4, 8, 3, 6, 9, 5, 10, 7), "random" a random order. Default "related". |
| first | string | `all`, `kings`, `near` | yes | Mal and Geteilt: the Erstfaktoren down the left side: "all" 1 to 10, "kings" only the Königsaufgaben 1, 2, 5, 10, "near" the Königsaufgaben plus or minus 1: 3, 4, 6, 9. Default "all". |
| hideRows | number | 0 to 9 | yes | How many row values are hidden; a given result cell in each such row lets the pupils work it back. 0 to rows − 1. Default 0. |
| hideCols | number | 0 to 9 | yes | How many column values are hidden; a given result cell in each such column lets the pupils work it back. 0 to cols − 1. Default 0. |
| tint | string | `none`, `blue`, `green`, `yellow`, `red`, `purple` | yes | A tint: "none", or one base colour ("blue", "green", "yellow", "red", "purple") for the value cells, darker in the corner; the result cells stay white. Default "none". |
| seed | number |  | yes | Seed for the random tables. The same seed always gives the same tables. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [table index from 0, row from 0, column from 0, value 0 to 9999]: row 0 holds the column values, column 0 the row values, the others the result cells. Typed numbers win over the drawn ones; a table whose numbers do not fit is marked wrong and its key shows no answers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "rechentabelle", "props": {}}
```
