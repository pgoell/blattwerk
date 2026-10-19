---
type: Reference
title: "Block: operatorfeld"
description: "The operator fields (Operatorfelder): number boxes joined by operators, in a ring or around a centre, and which numbers and operators are given."
tags: [block, operatorfeld]
covers: [operatorfeld]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-19T07:51:06Z }
---

# operatorfeld

The operator fields (Operatorfelder): number boxes joined by operators, in a ring or around a centre, and which numbers and operators are given.

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
| centre | boolean |  | yes | Whether the field has a centre (mit Zentrum): one number in the middle, linked to every outer box. Without (ohne Zentrum) the boxes stand in a closed ring and each pair of neighbours is linked. Default false. |
| count | number | 1 to 6 | yes | Number of Operatorfelder on the sheet, side by side in rows of `columns`. Default 2. |
| columns | number | 1 to 3 | yes | Number of Operatorfelder per row. Default 2. |
| boxes | number | 3 to 8 | yes | Kästchen per Operatorfeld: ohne Zentrum the boxes of the ring, mit Zentrum the outer boxes around the centre. Default 4. |
| max | number |  | yes | The Zahlenraum: the largest number a box may show, one of 10, 20, 100 or 1000. Any other value gives 20. Default 20. |
| ops | list of string | `+`, `-`, `*`, `:` | yes | The Rechenarten: "+", "-", "*" (Mal) and ":" (Geteilt), in that order, each once. Mit Zentrum only "+" and "-"; "*" and ":" need max 20 or more; the others are dropped. Several give each link its own (gemischt). Empty or not a list: ["+"]. Default ["+", "-"]. |
| only | string | `none`, `tens`, `hundreds` | yes | The Einschränkung: "none", "tens" (nur Zehnerzahlen: every number and every "+" or "-" operand a multiple of 10, needs max 100 or more) or "hundreds" (nur Hunderterzahlen: multiples of 100, needs max 1000). Too small a max gives "none". Default "none". |
| given | string | `start`, `ops`, `mixed` | yes | Which numbers show: "start" the first box (mit Zentrum the centre) and every operator; "ops" every box and no operator; "mixed" (gemischt) the first box (mit Zentrum the centre) and for each link either its operator or its other box. Ohne Zentrum with "+" or "-" and "*" or ":" together, "ops" and "mixed" may have several right answers ("+2" or "·2"), so the answer key says under the fields that other answers count too, and the block keeps a line for that note. Default "start". |
| drawOps | boolean |  | yes | Whether each operator place has an ellipse around it, also an empty one. Default true. |
| seed | number |  | yes | Seed for the random fields. The same seed always gives the same fields. |
| typed | list of list of number |  | no | Numbers the teacher typed into boxes. Each entry is [field index from 0, box index from 0 (mit Zentrum 0 is the centre), value 0 to 9999]. The operators of the links at a typed box follow from its numbers; a field where no allowed operator links two numbers is marked wrong. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "operatorfeld", "props": {}}
```
