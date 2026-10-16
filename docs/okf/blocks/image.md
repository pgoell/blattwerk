---
type: Reference
title: "Block: image"
description: "Which uploaded picture the block shows, and how it is cropped."
tags: [block, image]
covers: [image]
generated: { by: "process:frontend/okf.mjs" }
---

# image

Which uploaded picture the block shows, and how it is cropped.

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
| upload | number |  | yes | The id of the uploaded picture file, as the server stores it. |
| ratio | number |  | yes | The picture's width over its height, from the picture as uploaded. 1 for a square. |
| cut | list of number |  | yes | Four numbers for the share cropped off the left, top, right and bottom: each a fraction of the picture, 0 for none. |
| opacity | number | 0 to 1 | no | How solid the picture prints: 1 for full strength, 0 for see-through. Left out, 1. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "image", "props": {}}
```
