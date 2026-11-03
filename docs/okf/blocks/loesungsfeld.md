---
type: Reference
title: "Block: loesungsfeld"
description: "A blank the pupil writes in."
tags: [block, loesungsfeld]
covers: [loesungsfeld]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-03T05:33:17Z }
---

# loesungsfeld

A blank the pupil writes in. The Lösungen print its text or its picture, and nowhere else.

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
| kind | string | `text`, `image` | yes | What the Lösungen print: "text" a one-line Lösungstext, "image" a Lösungsbild. Default "text". |
| text | string |  | yes | The Lösungstext, one line. The pupil's sheet leaves it blank. Default "". |
| blank | string | `line`, `box`, `none` | yes | How the blank looks on the pupil's sheet: "line" an underline (Unterstrich), "box" a frame (Rahmen), "none" nothing. Default "line". |
| code | string |  | no | The OpenMoji code of the Lösungsbild, from the symbol library. Absent for a Lösungstext, or when the picture is an upload. |
| upload | number |  | no | The id of an uploaded picture used as the Lösungsbild. Absent when the picture is a symbol. |
| ratio | number |  | no | The uploaded picture's width over its height. 1 for a square. Absent means 1. |
| wrongs | list of object |  | no | Wrong answers (falsche Lösungen) for a Selbstkontrolle and later for digital sheets. Absent means none. |
| size | number | 8 to 48 | yes | Font size of the Lösungstext in pt. Default 14. |
| even | boolean |  | yes | True makes this field as wide as the widest even Lösungsfeld on the page, so the line length gives nothing away. Default false. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "loesungsfeld", "props": {}}
```
