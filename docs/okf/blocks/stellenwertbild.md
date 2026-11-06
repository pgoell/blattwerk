---
type: Reference
title: "Block: stellenwertbild"
description: "The Stellenwert-Bild tasks: pictures of Hunderterplatten, Zehnerstangen and Einerwürfel with the number to write, or the number with the picture to draw; Zahlenraum, Aufgabentyp, Stellenwerttafel, Stellen mit 0, Bündeln, the numbers typed in."
tags: [block, stellenwertbild]
covers: [stellenwertbild]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-06T15:21:40Z }
---

# stellenwertbild

The Stellenwert-Bild tasks: pictures of Hunderterplatten, Zehnerstangen and Einerwürfel with the number to write, or the number with the picture to draw; Zahlenraum, Aufgabentyp, Stellenwerttafel, Stellen mit 0, Bündeln, the numbers typed in.

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
| count | number | 1 to 12 | yes | Number of tasks (pictures) on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 4 | yes | Number of tasks per row. Default 2. |
| max | number |  | yes | The Zahlenraum: 100 (two places, Zehner and Einer; numbers 10 to 99) or 1000 (three places, Hunderter, Zehner and Einer; numbers 100 to 999). Default 1000. |
| task | string | `read`, `draw` | yes | The Aufgabentyp: "read" the picture of Hunderterplatten, Zehnerstangen and Einerwürfel shows and the pupil writes the number; "draw" the number shows and the pupil draws it as square (Hunderter), stroke (Zehner) and dot (Einer). Default "read". |
| table | boolean |  | yes | Stellenwerttafel: true puts a table of the places (H Z E) before the number box of a "read" task, for the pupil to write the digits in. Plays no part with "draw". Default true. |
| zero | boolean |  | yes | Stellen mit 0: false every number has no digit 0; true every number has a 0 in a place that is not the first (305, 260). Default false. |
| bundle | boolean |  | yes | Bündeln: true gives every picture more than 9 pieces in exactly one place (2 H 14 Z 6 E), so the pupil exchanges first; the answer key shows the number and the exchanged form (3 H 4 Z 6 E). With "draw" the task shows that form as text. Default false. |
| seed | number |  | yes | Seed for the random numbers. The same seed always gives the same tasks. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [task index from 0, number 0 to 9999]. A typed number wins over the seed; one that does not fit the Zahlenraum and Bündeln gives no task and a hint in the editor. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "stellenwertbild", "props": {}}
```
