---
type: Reference
title: "Block: zahlenhaus"
description: "The number houses (Zahlenhäuser): a roof number and floors of two boxes that add up to it, and which boxes are given."
tags: [block, zahlenhaus]
covers: [zahlenhaus]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-18T19:13:00Z }
---

# zahlenhaus

The number houses (Zahlenhäuser): a roof number and floors of two boxes that add up to it, and which boxes are given.

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
| count | number | 1 to 12 | yes | Number of houses on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 6 | yes | Number of houses per row. Default 4. |
| floors | number | 2 to 10 | yes | Number of floors (Stockwerke) under the roof. Each floor has two boxes that add up to the roof. Default 4. |
| max | number | 2 to 1000 | yes | The Zahlenraum: the largest roof number of a generated house, a whole number from 2 to 1000. The editor offers 10, 20 and 100, or any other. Default 10. |
| given | string | `side`, `roof`, `mix`, `free` | yes | Which boxes show their number. "side": the roof and the left box of each floor (easy). "roof": the roof only, the pupil finds the splits. "mix": the roof and one box of each floor, left or right from the seed. "free": the boxes flagged in `free`. Default "side". |
| free | list of boolean |  | no | With `given` "free": one flag per box, index 0 the roof, then 1 + 2f the left and 2 + 2f the right box of floor f (0 the top floor). A flagged box shows its number. The same for every house. Missing or of another length: the roof and the left boxes. |
| seed | number |  | yes | Seed for the random houses. The same seed always gives the same houses. |
| typed | list of list of number |  | no | Numbers the teacher typed into boxes. Each entry is [house index from 0, box index, value 0 to 9999]. A floor that does not add up to the roof is marked wrong. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zahlenhaus", "props": {}}
```
