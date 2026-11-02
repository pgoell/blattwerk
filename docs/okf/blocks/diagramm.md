---
type: Reference
title: "Block: diagramm"
description: "A chart (Diagramm) of bars, columns or a pie, drawn from a few values."
tags: [block, diagramm]
covers: [diagramm]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-02T23:35:44Z }
---

# diagramm

A chart (Diagramm) of bars, columns or a pie, drawn from a few values.

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
| kind | string | `balken`, `saeulen`, `kreis` | yes | Balken are horizontal bars, Säulen are vertical columns, Kreis is a pie. |
| points | list of object |  | yes | The data points, in order, at most 8. |
| legend | boolean |  | yes | Whether a legend is drawn. |
| values | string | `keine`, `innen`, `aussen` | yes | Where a value is written: nowhere, inside the bar or slice, or outside it. |
| axes | string | `keine`, `x`, `y`, `beide` | yes | Which axes are drawn. A pie draws none. |
| xTitle | string |  | yes | Title of the horizontal axis. Empty draws none. |
| yTitle | string |  | yes | Title of the vertical axis. Empty draws none. |
| grid | string | `keine`, `haupt`, `zwischen` | yes | Gridlines: none, the main steps, or the main steps and the steps between them. A pie draws none. |
| seed | number |  | yes | Kept so a sheet made with the other maths blocks still carries a seed. The chart does not roll from it. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "diagramm", "props": {}}
```
