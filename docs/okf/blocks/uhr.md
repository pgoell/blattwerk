---
type: Reference
title: "Block: uhr"
description: "The clock faces, their times and the task: read the time or draw the hands."
tags: [block, uhr]
covers: [uhr]
generated: { by: "process:frontend/okf.mjs" }
---

# uhr

The clock faces, their times and the task: read the time or draw the hands.

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
| numbers | string | `all`, `quarters`, `none` | yes | The numbers on the face. "all": 1 to 12. "quarters": only 12, 3, 6 and 9. "none": no numbers. Default "all". |
| minutes | boolean |  | yes | Draws the 60 minute ticks. The 12 hour ticks are always drawn. Default true. |
| ring | boolean |  | yes | Draws a second ring with 13 to 24 inside the numbers. Not drawn when `numbers` is "none". Default false. |
| task | string | `read`, `draw` | yes | "read": the hands are drawn and the pupil writes the time under the clock. "draw": no hands, the time is written under the clock and the pupil draws the hands. Default "read". |
| answer | string | `box`, `line` | yes | The empty answer under a clock with task "read". "box": a digital box `__:__ Uhr`. "line": a writing line. Default "box". |
| format | string | `12`, `24`, `words` | yes | How the time is written under the clock. "12": `3:30 Uhr`, hours 1 to 12. "24": `15:30 Uhr`, hours 0 to 23. "words": in words, such as "halb vier". Default "12". |
| region | string | `nach`, `viertel` | yes | The form of the time in words, with format "words". "nach": "viertel nach drei" and "viertel vor vier". "viertel": "viertel vier" and "dreiviertel vier". Default "nach". |
| count | number | 1 to 12 | yes | Number of clocks on the sheet, 1 to 12. Default 4. |
| cols | number | 1 to 6 | yes | Number of clocks per row, 1 to 6. The rows fill from the top left. Default 4. |
| step | number | `60`, `30`, `15`, `5`, `1` | yes | The minutes that random times keep to: 60 full hours, 30 half hours, 15 quarter hours, 5 or 1 minute. Default 15. |
| fill | string | `random`, `free` | yes | "random": every time is drawn from the seed. "free": each clock takes its time from `times`, and from the seed where that is missing. Default "random". |
| times | list of number |  | no | The time of each clock in minutes since 0:00 (0 to 1439), in clock order. A missing or -1 entry takes a random time. Used with fill "free". |
| seed | number |  | yes | Seed for the random times. The same seed always gives the same times. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "uhr", "props": {}}
```
