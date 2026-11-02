---
type: Reference
title: "Block: formula"
description: "A formula of fractions, mixed numbers, powers and roots, set in the sheet's font."
tags: [block, formula]
covers: [formula]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-02T23:34:57Z }
---

# formula

A formula of fractions, mixed numbers, powers and roots, set in the sheet's font. The same formula can sit inline in a text or a cell.

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
| source | string |  | yes | The formula in the simple syntax: "3/4" a fraction, "1 3/4" a mixed number, "2^3" a power, "sqrt(16)" a root, "x_2" a subscript, "\\ " a gap. |
| size | number | at least 8 | yes | Font size of the formula in pt. A fraction, a power and a root scale with it. The editor steps it by 2 pt and never goes below 8. |
| color | string |  | no | Colour of the formula as a hex colour, such as "#222222". Absent means #222222. |
| align | string | `left`, `center`, `right` | no | Horizontal alignment in the box: "left", "center" or "right". Absent means center. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "formula", "props": {}}
```
