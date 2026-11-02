---
type: Reference
title: "Block: geobrett"
description: "The geoboard (Geobrett): nails, rubber bands and the geometry task the pupil solves."
tags: [block, geobrett]
covers: [geobrett]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-02T21:33:19Z }
---

# geobrett

The geoboard (Geobrett): nails, rubber bands and the geometry task the pupil solves.

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
| cols | number | 2 to 12 | yes | Nails across the board. |
| rows | number | 2 to 12 | yes | Nails down the board. |
| bands | list of object |  | yes | The rubber bands, in the order they are drawn. |
| task | string | `leer`, `spiegel`, `achsen`, `drehung`, `winkel`, `parallelen`, `flaeche`, `umfang`, `koordinaten` | yes | The task. "leer" is an empty board the pupil draws on. The others ask for the mirror image, the axes, a quarter turn, the right angles, the parallel sides, the area, the perimeter or the coordinates. |
| figure | number |  | no | Which starting figure of `task` the bands came from, from 0. Absent when the teacher drew the bands. |
| axis | object |  | no | The mirror line of task "spiegel". |
| centre | list of number |  | no | The nail a task "drehung" turns about, [column, row]. |
| seed | number |  | yes | Kept so a sheet made with the other maths blocks still carries a seed. The board does not roll from it. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "geobrett", "props": {}}
```
