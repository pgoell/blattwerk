---
type: Reference
title: "Block: zahlenstrahl"
description: "The number line (Zahlenstrahl): its range, ticks and the tasks on it."
tags: [block, zahlenstrahl]
covers: [zahlenstrahl]
generated: { by: "process:frontend/okf.mjs" }
---

# zahlenstrahl

The number line (Zahlenstrahl): its range, ticks and the tasks on it.

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
| start | number | 0 to 999999 | yes | The number of the first tick, from 0 up. The line starts here. Default 0. |
| end | number | 0 to 1000000 | yes | The number of the last tick, above `start`. The last tick is the last multiple of `minor` that is not above it. Default 20. |
| minor | number | 1 to 1000000 | yes | The step between two ticks (small ticks), in whole numbers. Default 1. |
| major | number |  | yes | The step between two long ticks. A multiple of `minor`. A tick is long when its number minus `start` is a multiple of it. The first tick is always long. Default 5. |
| labels | string | `all`, `major`, `ends`, `none` | yes | Which ticks show their number. "all": every tick. "major": the long ticks. "ends": the first and the last tick. "none": no tick. Default "major". |
| size | number | 8 to 24 | yes | Font size of the numbers, in pt. Does not change with the block's size. Default 12. |
| cut | boolean |  | yes | Draws a break mark (two short slanted strokes) left of the first tick. Only shown when `start` is above 0. Default false. |
| tasks | string | `random`, `free` | yes | "random": boxes and arrows go on ticks chosen from the seed. "free": the ticks in `marks` get their task. Default "random". |
| boxes | number | 0 to 12 | yes | Number of boxes placed on the line with `tasks` "random". Default 3. |
| arrows | number | 0 to 6 | yes | Number of arrows placed on the line with `tasks` "random". Default 0. |
| marks | list of list of number and string |  | no | The ticks picked in "free" mode, each [number, "box" or "arrow"]. An entry that is not a tick is kept but not drawn. |
| jumps | boolean |  | yes | Draws jump arcs above the line, from the first tick on. Default false. |
| jump | number |  | no | Width of each jump arc, a multiple of `minor`. Default `major`. |
| arcs | list of string,null |  | no | A text for each jump arc, by index. A missing or empty entry shows "+" and the jump width. |
| seed | number |  | yes | Seed for the random tasks. The same seed always gives the same tasks. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zahlenstrahl", "props": {}}
```
