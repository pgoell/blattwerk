---
type: Reference
title: "Block: selbstkontrolle"
description: "The self-check (Selbstkontrolle): a key that tells the pupil whether the answers of the linked blocks are right."
tags: [block, selbstkontrolle]
covers: [selbstkontrolle]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-16T00:00:00Z }
---

# selbstkontrolle

The self-check (Selbstkontrolle): a key that tells the pupil whether the answers of the linked blocks are right.

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
| form | string | `mixed`, `word`, `sum` | yes | How the child checks her results. "mixed": the results in a shuffled list, each with a box to tick. "word": a Lösungswort with a letter box under each task. "sum": one control sum per linked block. Default "mixed". |
| links | list of string |  | yes | Ids of the linked maths blocks of the sheet, in the order the teacher ticked them. Default none. |
| word | string |  | yes | The Lösungswort the child builds from the letters, as the teacher typed it. Used with form "word" only. Default "". |
| title | string |  | yes | The heading of the block. An empty heading prints none. Default "Selbstkontrolle". |
| size | number | 8 to 24 | yes | Font size of the text in pt, except the heading, which is 1.2 times it. Default 14. |
| turn | string | `none`, `upside`, `fold` | yes | Turns the block for the child to read it later. "none": not turned. "upside": the whole content turned by 180 degrees. "fold": a dashed fold line along the top, with "Hier umknicken" over it, and the content turned by 180 degrees under it, so the child folds it back. Default "none". |
| seed | number |  | yes | Seed for the shuffle of form "mixed" and of the table of form "word". The same seed always gives the same order. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "selbstkontrolle", "props": {}}
```
