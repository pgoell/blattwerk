---
type: Reference
title: "Block: zehnerfeld"
description: "The Zehnerfeld tasks: Plus and Minus on a Zehnerfeld, Zwanzigerfeld or Hunderterfeld of dots, the task line under each field; Aufgabentyp, Zahlenraum, Zehnerübergang, Trennlinien, Farben, dots set by hand."
tags: [block, zehnerfeld]
covers: [zehnerfeld]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-20T08:27:20Z }
---

# zehnerfeld

The Zehnerfeld tasks: Plus and Minus on a Zehnerfeld, Zwanzigerfeld or Hunderterfeld of dots, the task line under each field; Aufgabentyp, Zahlenraum, Zehnerübergang, Trennlinien, Farben, dots set by hand.

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
| count | number | 1 to 12 | yes | Number of tasks (fields) on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 4 | yes | Number of tasks per row. Default 2. |
| field | string | `zehn`, `zehn2`, `zwanzig`, `hundert` | yes | The Typ of field: "zehn" Zehnerfeld 1 × 10, "zehn2" Zehnerfeld 2 × 5, "zwanzig" Zwanzigerfeld 2 × 10, "hundert" Hunderterfeld 10 × 10. The dots count row by row from the top left. Default "zwanzig". |
| op | string | `+`, `-` | yes | The Rechenart: "+" (Plus: the first number's dots in colour 1, the second number's in colour 2) or "-" (Minus: the first number's dots in colour 1, the second number's of them struck through). Default "+". |
| task | string | `dots`, `write`, `mixed` | yes | The Aufgabentyp: "dots" the field shows the dots and the pupil writes the task; "write" the task's two numbers show and the pupil paints the dots and writes the result; "mixed" the two by turns, starting with "dots". Default "dots". |
| max | number |  | yes | The Zahlenraum: 5, 10, 20, 50 or 100, at most the field's size (10, 20 or 100). Plus results and Minus first numbers stay within it. Default 20. |
| cross | string | `any`, `yes`, `no` | yes | The Zehnerübergang: "yes" every task crosses a ten (Plus: the Einer of both numbers add up to more than 10, as 8 + 5; Minus: the Einer of the result and the second number do, as 13 − 5), "no" none does (6 + 4 = 10 and 20 − 4 do not cross), "any" either. Counts only with the Zwanziger- and Hunderterfeld. Default "any". |
| lines | boolean |  | yes | Trennlinien: true draws a strong line after each five dots, across and down. Default true. |
| colors | string | `color`, `grey`, `own` | yes | Farben: "color" red and blue, "grey" Graustufen (black and grey, for black and white copies), "own" the colours `color1` and `color2`. Default "color". |
| color1 | string |  | no | The first colour with `colors` "own", as "#rrggbb". Default "#e3463b". |
| color2 | string |  | no | The second colour with `colors` "own", as "#rrggbb". Default "#1d4ea6". |
| manual | boolean |  | yes | Punkte selbst setzen: true shows in each field exactly the dots in `marks` and no task; the number boxes stay empty for the pupil. Default false. |
| marks | list of list of number |  | no | The dots the teacher set with `manual`. Each entry is [task index from 0, dot 0 to 99 counted row by row, mark 1 colour 1, 2 colour 2 or 3 colour 1 struck through]. |
| seed | number |  | yes | Seed for the random tasks. The same seed always gives the same tasks. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [task index from 0, position 0 to 2, value 0 to 999]. Positions: 0 the first number, 1 the second number, 2 the result. The other positions are worked out from them; a task whose typed numbers do not fit the field is marked wrong and shows no dots and no numbers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zehnerfeld", "props": {}}
```
