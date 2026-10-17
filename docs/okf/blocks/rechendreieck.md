---
type: Reference
title: "Block: rechendreieck"
description: "The calculation triangles (Rechendreiecke) and which of their fields are given."
tags: [block, rechendreieck]
covers: [rechendreieck]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-16T00:00:00Z }
---

# rechendreieck

The calculation triangles (Rechendreiecke) and which of their fields are given.

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
| count | number | 1 to 12 | yes | Number of triangles on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 4 | yes | Number of triangles per row. Default 4. |
| max | number |  | yes | The Zahlenraum: the largest number any outer field of a generated triangle shows. One of 10, 20, 100 or 1000. Default 20. |
| given | string | `inner`, `mix`, `outer`, `free` | yes | Which fields show their number. "inner": the three inner fields (easy). "mix": two inner fields and one outer field (medium). "outer": the three outer fields (hard). "free": the fields flagged in `free`. Default "inner". |
| free | list of boolean |  | no | With `given` "free": one flag per field, index 0 to 5 (inner 0 to 2, outer 3 to 5). A flagged field shows its number. Missing or invalid: the three inner fields. |
| empty | boolean |  | yes | When true, no field shows a number, so the pupil fills in every field. Default false. |
| seed | number |  | yes | Seed for the random triangles. The same seed always gives the same triangles. |
| typed | list of list of number |  | no | Numbers the teacher typed into fields. Each entry is [triangle index from 0, field index 0 to 5, value 0 to 9999]. The triangles are then built to hold these numbers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "rechendreieck", "props": {}}
```
