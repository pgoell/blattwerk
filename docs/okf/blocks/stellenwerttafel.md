---
type: Reference
title: "Block: stellenwerttafel"
description: "The Stellenwerttafel tasks: tables of Plättchen (dots) in the columns of H, Z and E (or T, H, Z and E) with the number to write, the number with the dots to lay, or one dot to move to another column with every number that makes; Zahlenraum, Aufgabentyp, Plättchen, Leere Stellen, the numbers typed in."
tags: [block, stellenwerttafel]
covers: [stellenwerttafel]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-06T18:39:07Z }
---

# stellenwerttafel

The Stellenwerttafel tasks: tables of Plättchen (dots) in the columns of H, Z and E (or T, H, Z and E) with the number to write, the number with the dots to lay, or one dot to move to another column with every number that makes; Zahlenraum, Aufgabentyp, Plättchen, Leere Stellen, the numbers typed in.

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
| count | number | 1 to 12 | yes | Number of tasks (tables) on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 4 | yes | Number of tasks per row. Default 2. |
| max | number |  | yes | The Zahlenraum: 1000 (columns H Z E, numbers 1 to 999) or 10000 (columns T H Z E, numbers 1 to 9999). Default 1000. |
| task | string | `read`, `lay`, `move` | yes | The Aufgabentyp: "read" the table shows the dots (Plättchen) and the pupil writes the number; "lay" the number shows and the pupil draws its dots in the empty table; "move" the table shows the dots, the pupil moves one dot to another column and writes every number that makes (the answer key lists them all). Default "read". |
| dots | number | 1 to 36 | yes | Plättchen: the most dots of one task (the sum of its digits), 1 to 36, so tasks like "lege Zahlen mit höchstens 4 Plättchen" stay in range. Default 9. |
| zero | boolean |  | yes | Leere Stellen: false every column holds at least one dot (no digit 0); true a column may be empty (306, 45). Default false. |
| seed | number |  | yes | Seed for the random numbers. The same seed always gives the same tasks. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [task index from 0, number 0 to 9999]. A typed number wins over the seed and may have empty columns (306) whatever `zero` says; one outside the Zahlenraum, with more dots than `dots`, or with no move in "move" gives an empty task and a hint in the editor. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "stellenwerttafel", "props": {}}
```
