---
type: Reference
title: "Block: halbschriftlich"
description: "The Halbschriftlich tasks (semi-written addition and subtraction): each task a + b = r and its steps place by place, the highest place first; Karo or plain, place letters, tint, signs of the steps for the pupils."
tags: [block, halbschriftlich]
covers: [halbschriftlich]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-20T05:56:02Z }
---

# halbschriftlich

The Halbschriftlich tasks (semi-written addition and subtraction): each task a + b = r and its steps place by place, the highest place first; Karo or plain, place letters, tint, signs of the steps for the pupils.

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
| op | string | `+`, `-` | yes | The Rechenart: "+" (Plus: 345 + 123 = 345 + 100 + 20 + 3) or "-" (Minus: 468 − 123 = 468 − 100 − 20 − 3). Default "+". |
| max | number |  | yes | The Zahlenraum of the first number and the result, 100 or 1000: the first number, and the result of a Plus task, are at most max. Default 1000. |
| digits | number |  | yes | The places of the second number: 1, 2 or 3 digits (3 only with max 1000, else it acts as 2). One step per digit that is not 0. Default 3. |
| einer | string | `any`, `yes`, `no` | yes | The Übergang at the Einer, crossing a ten: "yes" every task crosses a ten (Plus: the Einer of both numbers add up to 10 or more; Minus: the first number's Einer is smaller than the second's), "no" none does, "any" either. Default "any". |
| zehner | string | `any`, `yes`, `no` | yes | The Übergang at the Zehner, crossing a hundred in any step, as the Übertrag of written arithmetic (Plus: the last two digits of both numbers add up to 100 or more, so 395 + 7 crosses; Minus: the first number's last two digits are smaller than the second's): "yes", "no" or "any". Counts only with max 1000. Default "any". |
| grid | boolean |  | yes | Karo: true draws 5 mm squares behind the tasks, one digit to a square; false draws plain white with a box per number. Default true. |
| head | boolean |  | yes | Stellenwerte: true draws the place letters T H Z E above each task's numbers. Default false. |
| tint | boolean |  | yes | true tints the second number and its parts in the steps. Default false. |
| ops | boolean |  | yes | true prints the signs (+ or − and =) of the step lines on the pupils' sheet; false leaves the signs out for the pupils to write (the number boxes stay). The key always shows the full steps. Default true. |
| seed | number |  | yes | Seed for the random tasks. The same seed always gives the same tasks. |
| typed | list of list of number |  | no | Numbers the teacher typed. Each entry is [task index from 0, position 0 to 2, value 0 to 9999]. Positions: 0 the first number, 1 the second number, 2 the result. Any two fix the task and its steps. A task with typed numbers shows exactly its typed boxes; the others are worked out from them. A task whose typed numbers do not fit is marked wrong and its key shows no answers. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "halbschriftlich", "props": {}}
```
