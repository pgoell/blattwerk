---
type: Reference
title: "Block: table"
description: "The table's text, layout and lines."
tags: [block, table]
covers: [table]
generated: { by: "process:frontend/okf.mjs" }
---

# table

The table's text, layout and lines.

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
| lineStyle | string | `solid`, `dashed`, `dotted`, `none` | no | The style of every line of the table: "solid", "dashed", "dotted" or "none". Left out, solid. |
| lineWidth | number | 0.25 to 3 | no | The width of every line of the table, in mm, from 0.25 to 3. Left out, 0.25. |
| cut | boolean |  | no | Whether scissors mark a cutting line (Schneidelinie) at the left end of the top line. Left out, no. |
| edges | object |  | no | The style and width of single lines, per edge of a cell. Left out, every line takes lineStyle and lineWidth. |
| cells | list of list of string |  | yes | The text of each cell, as cells[row][column], counted from 0. A cell holds one plain text. |
| cols | list of number |  | yes | The width share of each column, as parts of the sum of all of them. Only the ratios between columns count. |
| size | number |  | yes | Font size of the cell text, in pt. |
| align | string | `left`, `center`, `right` | yes | Horizontal alignment of the cell text: "left", "center" or "right". |
| font | string | `andika`, `nord`, `sued`, `grund`, `urff`, `va`, `sas`, `la` | no | Font of the cell text. Left out, the default font. |
| color | string |  | no | Colour of the cell text. Left out, the default colour. |
| line | string |  | no | Colour of the table's lines. |
| head | boolean |  | no | Whether the first row is printed in bold. Default false. |
| syllables | boolean |  | no | Whether the words in the cells are split into syllables, with hyphens at the breaks. Default false. |
| breaks | object |  | no | The teacher's own syllable breaks: each word in lower case as the key, with the places it breaks at as the value. |
| tints | list of string |  | no | The two colours the syllables take in turn, first then second. |
| tintsAcross | boolean |  | no | Whether the colours of the syllables turn on from word to word through the text. Left out, each word starts with the first colour. |
| gaps | list of list of boolean |  | no | Per cell, true makes the whole cell a gap to fill in, a row of columns at a time as cells does. |
| gapWidth | number | at least 5 | no | Width of the gaps in mm, all the same. The editor takes 5 mm or more. |
| bank | number |  | no | A word bank printed under the table for the gaps. Left out, there is none. |
| trace | boolean or string | `outline` or `dotted` | no | How the cell text shows as a trace to write over: true for grey, "outline" for letters with a line round them and no fill, "dotted" for dotted letters. Left out, no trace. |
| fade | string | `row`, `rows` | no | Makes the trace fade step by step until it is gone: "row" along each row, "rows" from row to row. Left out, no fade. |
| spans | list of list of number and number and number and number |  | no | Merged cells, each as [row, column, rows, columns]: the cell where it starts and how many rows and columns it covers, counted from 0. |
| rows | list of number |  | no | The lowest height of each row, in mm. A row still grows when its text needs more. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "table", "props": {}}
```
