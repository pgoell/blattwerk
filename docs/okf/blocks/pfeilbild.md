---
type: Reference
title: "Block: pfeilbild"
description: "The arrow pictures (Pfeilbilder): boxes joined by arrows, each arrow labelled with an operator, and which boxes and operators are given."
tags: [block, pfeilbild]
covers: [pfeilbild]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T04:32:02Z }
---

# pfeilbild

The arrow pictures (Pfeilbilder): boxes joined by arrows, each arrow labelled with an operator, and which boxes and operators are given.

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
| count | number | 1 to 12 | yes | Number of Pfeilbilder on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 3 | yes | Number of Pfeilbilder per row. Default 2. |
| boxes | number or string | `random` | yes | Kästchen per Pfeilbild: a whole number from 3 to 8, or "random" (Zufällig): each Pfeilbild draws its own number from 3 to 8 from the seed. Default 4. |
| max | number |  | yes | The Zahlenraum: the largest number a box may show, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. |
| ops | list of string | `+`, `-`, `*`, `:` | yes | The Rechenarten: "+", "-", "*" (Mal) and ":" (Geteilt), in that order, each once. "*" and ":" need max 20 or more, under that they are dropped. Empty or not a list: ["+"]. Default ["+", "-"]. |
| arrows | string | `one`, `both` | yes | The arrows: "one" for arrows in one direction, "both" for arrows in both directions. Under each forward arrow a back arrow shows the inverse operator: "+4" goes back as "−4", "·2" as ":2", ":2" as "·2". Default "one". |
| given | string | `start`, `ends`, `mixed` | yes | Which numbers show: "start" the first box and every operator, "ends" the first and the last box (no operators), "mixed" (gemischt) the first box and for each arrow either its operator or the box after it, so that the pupil can solve it from left to right. Default "start". |
| drawOps | boolean |  | yes | Whether each operator place has an ellipse around it, also an empty one. Default true. |
| seed | number |  | yes | Seed for the random pictures. The same seed always gives the same pictures. |
| typed | list of list of number |  | no | Numbers the teacher typed into boxes. Each entry is [picture index from 0, box index from 0, value 0 to 9999]. The lowest typed box of a picture is its anchor. A picture whose numbers do not fit its operators is marked wrong. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "pfeilbild", "props": {}}
```
