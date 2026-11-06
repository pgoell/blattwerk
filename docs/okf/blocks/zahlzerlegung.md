---
type: Reference
title: "Block: zahlzerlegung"
description: "The Zahlzerlegung tasks: numbers split into place values (348 = 300 + 40 + 8) or put together from them, in place order, out of order, with H Z E letters, with a gap, with zeros or bundled; Zahlenraum, Aufgabentyp, the numbers typed in."
tags: [block, zahlzerlegung]
covers: [zahlzerlegung]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-06T17:24:50Z }
---

# zahlzerlegung

The Zahlzerlegung tasks: numbers split into place values (348 = 300 + 40 + 8) or put together from them, in place order, out of order, with H Z E letters, with a gap, with zeros or bundled; Zahlenraum, Aufgabentyp, the numbers typed in.

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
| columns | number | 1 to 3 | yes | Number of tasks per row. Default 2. |
| max | number |  | yes | The Zahlenraum: 100 (Zehner and Einer, numbers 10 to 99), 1000 (Hunderter, Zehner, Einer, numbers 100 to 999) or 10000 (Tausender too, numbers 1000 to 9999). Default 1000. |
| task | string | `split`, `join`, `shuffled`, `places`, `gap`, `zero`, `bundle` | yes | The Aufgabentyp: "split" the number shows and the pupil writes its place values (348 = __ + __ + __; a typed number with a 0 place keeps that gap and the key writes 0, 306 = 300 + 0 + 6); "join" the place values show in order and the pupil writes the number (400 + 30 + 5 = __); "shuffled" the place values show out of order (8 + 400 + 50 = __); "places" the digits show with the place letters, a place with 0 left out, every second task out of order (3 H 7 Z 2 E = __, 8 Z 4 H = __); "gap" one place value is missing (600 + __ + 4 = 674); "zero" numbers with a 0 in a place, the pupil writes every digit (506 = __ H __ Z __ E); "bundle" one place has more than 9 (4 H 12 Z 3 E = __). Every gap has the same width; the answer key fills them in. Default "split". |
| seed | number |  | yes | Seed for the random numbers. The same seed always gives the same tasks. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [task index from 0, number 0 to 9999]. A typed number wins over the seed; one that does not fit the Zahlenraum and the Aufgabentyp gives no task and a hint in the editor. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zahlzerlegung", "props": {}}
```
