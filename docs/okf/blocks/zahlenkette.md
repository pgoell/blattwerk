---
type: Reference
title: "Block: zahlenkette"
description: "The number chains (Zahlenketten): rings in a row, each step adding or taking away the same number, and which rings are given."
tags: [block, zahlenkette]
covers: [zahlenkette]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T02:21:48Z }
---

# zahlenkette

The number chains (Zahlenketten): rings in a row, each step adding or taking away the same number, and which rings are given.

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
| count | number | 1 to 12 | yes | Number of chains (Ketten) on the sheet, side by side in rows of `columns`. Default 4. |
| columns | number | 1 to 4 | yes | Number of chains per row. Default 2. |
| rings | number | 4 to 12 | yes | Number of rings per chain. Default 6. |
| max | number |  | yes | The Zahlenraum: the largest number a chain may reach, one of 10, 20, 100 or 1000. Any other value gives 20. Every number stays in it: a random step is one that fits, and a chain that cannot fit (a fixed step too big, or too many rings, as with "*") is not drawn. Default 20. |
| op | string | `+`, `-`, `*` | yes | The operation: "+" adds the step, "-" takes it away, "*" multiplies by it. "*" needs max 100 or more, under that it becomes "+". Default "+". |
| step | number | 1 to 1000 | no | The fixed step (Schrittweite): for "+" and "-" a whole number from 1 to 1000, for "*" from 2 to 10. Missing: a random step per chain. Out of range: dropped. |
| showStep | boolean |  | yes | Whether each arc shows its step on the pupil sheet. On: "+3", "−3" or "·2". Off: the arcs are empty, and the answer key writes the step on them in red. Default false. |
| given | string | `start`, `ends`, `random`, `free` | yes | Which rings show their number: "start" the first two, "ends" the first and the last, "random" a few per chain from the seed, "free" the rings flagged in `free`, the same for every chain. Default "start". |
| free | list of boolean |  | no | With `given` "free": one flag per ring, a flagged ring shows its number. The same for every chain. Missing or of another length: the first two rings. |
| seed | number |  | yes | Seed for the random chains. The same seed always gives the same chains. |
| typed | list of list of number |  | no | Numbers the teacher typed into rings. Each entry is [chain index from 0, ring index from 0, value 0 to 9999]. The lowest typed ring of a chain is its anchor. A chain whose numbers do not fit its step is marked wrong. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "zahlenkette", "props": {}}
```
