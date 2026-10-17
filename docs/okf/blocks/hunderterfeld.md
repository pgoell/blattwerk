---
type: Reference
title: "Block: hunderterfeld"
description: "The hundred square (Hunderterfeld or Hundertertafel) and what the pupil fills in."
tags: [block, hunderterfeld]
covers: [hunderterfeld]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-16T00:00:00Z }
---

# hunderterfeld

The hundred square (Hunderterfeld or Hundertertafel) and what the pupil fills in.

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
| look | string | `tafel`, `punkte` | yes | What is drawn: "tafel" the Hundertertafel with its numbers in a 10 by 10 grid, "punkte" a field of 10 by 10 dots. Default "tafel". |
| from | number | `0`, `1` | yes | The first number of the Tafel: 1 gives 1 to 100, 0 gives 0 to 99. Default 1. |
| show | string | `all`, `none`, `random`, `free` | yes | Which numbers of the Tafel show. "all": every number. "none": no number. "random": all but `hide` cells, picked from the seed, are hidden. "free": all but the cells in `hidden` show. Default "all". |
| hide | number | 0 to 100 | yes | Number of cells hidden with `show` "random". Default 20. |
| hidden | list of number |  | no | Cell indices (0 to 99, row by row from the top left) whose number is hidden with `show` "free". |
| tint | string | `none`, `even`, `times`, `row`, `column`, `free` | yes | Which cells of the Tafel are tinted. "none": no cell. "even": the even numbers. "times": the multiples of `times` up to 10 times `times`. "row": the row `line`. "column": the column `line`. "free": the cells in `tints`. Default "none". |
| times | number | 1 to 10 | yes | The row of the Einmaleins that "times" tints, 1 to 10. Default 2. |
| line | number | 1 to 10 | yes | The row or column tinted with "row" or "column", counted from the top or the left, 1 to 10. Default 1. |
| color | number | `1`, `2` | yes | The colour of a tint from "even", "times", "row" or "column": 1 yellow, 2 blue. Default 1. |
| tints | list of list of number and number |  | no | Each tinted cell with its colour, for tint "free": [cell index 0 to 99, colour 1 yellow or 2 blue]. |
| cut | boolean |  | yes | Cut-out (Ausschnitt): when true, only the cells in `shape` are drawn, and the cell `given` shows its number while the other cells stay empty for the pupil to fill in. Default false. |
| shape | list of number |  | no | Cell indices (0 to 99) drawn with `cut`. Default a cross: 34, 43, 44, 45, 54. An empty list draws nothing. |
| given | number | 0 to 99 | no | The cell index (0 to 99) that shows its number with `cut`. If it is not in `shape`, the lowest cell of `shape` is used. Default 44. |
| fill | string | `count`, `free` | yes | With "count", the first `dots` dots are filled, row by row. With "free", the dots in `filled` are. Default "count". |
| dots | number | 0 to 100 | yes | Number of filled dots with `fill` "count", counted row by row from the top left. Default 0. |
| filled | list of number |  | no | Cell indices (0 to 99) of the filled dots with `fill` "free". |
| seed | number |  | yes | Seed for the random hidden cells with `show` "random". The same seed always hides the same cells. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "hunderterfeld", "props": {}}
```
