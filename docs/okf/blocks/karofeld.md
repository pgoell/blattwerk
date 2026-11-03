---
type: Reference
title: "Block: karofeld"
description: "A free squared grid: one digit or sign to a square, for Kopfrechnen, Rechenwege and geometry."
tags: [block, karofeld]
covers: [karofeld]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-02T22:29:07Z }
---

# karofeld

A free squared grid: one digit or sign to a square, for Kopfrechnen, Rechenwege and geometry.

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
| cols | number | 1 to 30 | yes | Squares across the grid. |
| rows | number | 1 to 40 | yes | Squares down the grid. |
| size | number | 4 to 16 | yes | Side of one square in mm. The letter is a fixed share of it. |
| look | string | `karos`, `kreise`, `punkte`, `iso` | yes | What is drawn: "karos" the squares, "kreise" a circle in each square, "punkte" a dot in each square, "iso" an isometric grid. |
| cells | list of list of object |  | no | The squares, row by row from the top left. A missing row or square is empty. |
| caret | list of number |  | no | The square the next sign goes in, as [column, row] counted from 0. Left out, the first square. |
| seed | number |  | yes | Stored with the block, as the other maths blocks store a seed. The grid does not use it. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "karofeld", "props": {}}
```
