---
type: Reference
title: "Block: suchsel"
description: "The word search's settings: the grid, the words and how they run."
tags: [block, suchsel]
covers: [suchsel]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-16T00:00:00Z }
---

# suchsel

The word search's settings: the grid, the words and how they run.

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
| words | list of string |  | yes | The words to hide in the grid, one entry per word, as the teacher typed them. |
| cols | number | 6 to 20 | yes | Number of squares across the grid. |
| rows | number | 6 to 20 | yes | Number of squares down the grid. |
| ways | string | `across`, `down`, `diag`, `back` | yes | The directions the words may run: "across" only, "down" too, "diag" (diagonal) too, or "back" (backwards) too. Each level includes the ones before. |
| caps | boolean |  | yes | Whether every letter shows as a capital. If not, every letter is small. |
| umlauts | boolean |  | yes | Whether ä, ö, ü and ß stay. If not, they become AE, OE, UE and SS. |
| show | string | `words`, `count` | yes | Whether the hidden words print under the grid ("words") or only how many there are ("count"). |
| seed | number |  | yes | The number that sets the layout of the grid. The same seed gives the same grid. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "suchsel", "props": {}}
```
