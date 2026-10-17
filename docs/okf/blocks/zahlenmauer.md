---
type: Reference
title: "Block: zahlenmauer"
description: "The wall block's settings: the stones, the walls and the numbers shown."
tags: [block, zahlenmauer]
covers: [zahlenmauer]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-16T00:00:00Z }
---

# zahlenmauer

The wall block's settings: the stones, the walls and the numbers shown.

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
| base | number | `3`, `4`, `5` | yes | Number of stones in the lowest row of each wall: 3, 4 or 5. |
| count | number | 1 to 12 | yes | Number of walls in the block. |
| columns | number | 1 to 4 | yes | Number of walls standing side by side. |
| max | number |  | yes | The Zahlenraum: no stone lies above it. One of 10, 20, 100 or 1000. |
| op | string | `+`, `*` | yes | How a stone is made from the two under it: "+" the sum, "*" the product. |
| given | string | `base`, `mix`, `free` | yes | Which stones show a number: "base" the base row only, "mix" per wall a mix that needs the way back, "free" the stones marked in free. |
| free | list of boolean |  | no | Per stone index, true shows that stone's number when given is "free". The same for every wall. |
| empty | boolean |  | yes | Whether no stone shows a number. Default false. |
| seed | number |  | yes | The number that sets the walls. The same seed gives the same walls. |
| typed | list of list of number |  | no | Numbers the teacher typed into stones, each as [wall, stone index, value], counted from 0. A stone's index counts from the left end of the base row, a row at a time. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zahlenmauer", "props": {}}
```
