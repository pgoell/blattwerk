---
type: Reference
title: "Block: maths"
description: "The maths block's limits, layout and exercises."
tags: [block, maths]
covers: [maths]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-03T03:40:15Z }
---

# maths

The maths block's limits, layout and exercises.

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
| columns | number | 1 to 6 | yes | Number of columns the exercises stand in side by side across the block. |
| size | number | at least 8 | yes | Font size of a row or a gap, in pt. The editor steps it by 2 pt and never goes below 8. |
| numbering | string |  | no | How the exercises are numbered on the sheet, as the editor's numbering control sets it. |
| exercises | list of object |  | yes | The exercises the server made for the limits, in the order they stand on the sheet. |
| loosen | list of string or null |  | yes | The limits in the way when fewer exercises came than asked for, by name, such as "max" or "zehner". null when the count is met. |
| ops | list of string | `+`, `-`, `*`, `/` | yes | The operations the tasks may use: "+" plus, "-" minus, "*" times and "/" divided by. At least one. |
| max | number | 1 to 1000000 | yes | The Zahlenraum: no number or result lies above it. The editor offers 10, 20, 100, 1000 and 1000000. |
| a | list of list of number |  | no | The digits the first number may have, one range of 0 to 9 per place, units first. A place left out takes any digit. |
| b | list of list of number |  | no | The digits the second number may have, one range of 0 to 9 per place, units first. A place left out takes any digit. |
| c | list of list of number |  | no | The digits the third number may have, one range of 0 to 9 per place, units first, for tasks of three numbers. Left out, any digit. |
| carry | list of string or string | `none`, `required`, `either` or `none` or `required` or `either` | yes | Plus and Minus: the Übertrag per place, smallest place first, [Zehnerübergang, Hunderterübergang, Tausenderübergang]. Each is "none" (that place does not cross), "required" (it does) or "either" (no rule). A place counts when the Zahlenraum goes past it: the Zehner past 10, the Hunderter past 100, the Tausender past 1000. With places after the comma the list starts at the smallest place (one decimal: Einerübergang, then Zehnerübergang). Plus crosses a place when its digits sum to more than 10 (7 + 3 and 17 + 23 do not). A carry does not run on, so 395 + 7 does not cross a hundred. Minus crosses when that digit of the first number is smaller than the second's. "none" at the top place that counts also rules out every place above it. An older single "none", "required" or "either" is read as every place, only the smallest place, or no rule. Default ["either", "either", "either"]. |
| rest | boolean |  | yes | Whether a division leaves a remainder. false, the default, gives even divisions only. |
| format | string | `row`, `gap`, `written`, `compare` | yes | How each task is written: "row" as a line of numbers, "gap" as a line with a gap to fill, "written" as a column calculation on squared paper, "compare" as comparisons with a ring to fill. |
| count | number | 1 to 100 | yes | How many tasks the block makes. |
| seed | number |  | yes | The number the tasks are drawn from. The same seed and limits give the same tasks; a new seed draws new ones. |
| sides | string | `nn`, `tn`, `tt` | no | What stands on each side of a comparison: "nn" number and number, "tn" term and number, "tt" term and term. Default "tn". Only comparisons use it. |
| close | boolean |  | no | Whether the sides of a comparison lie close together, 1 or 2 units or tens apart. Default false. Only comparisons use it. |
| equal | string | `none`, `some` | no | Whether comparisons have equal sides: "none" never, "some" about one in five. Default "some". Only comparisons use it. |
| numbers | number | `2`, `3`, `4` | no | How many numbers a task has: 2 or 3 for a row or a gap, and 2, 3 or 4 for a written plus. Default 2. A written plus of 3 or 4 is one column sum. 4 applies to that plus only. |
| pvs | boolean |  | no | Whether times and divide tasks mix with plus and minus tasks, with the times or divide worked out first (Punkt vor Strich). Default false. |
| brackets | boolean |  | no | Whether about half of the tasks put brackets round the plus or minus part (Klammern). Default false. |
| decimals | number | `0`, `1`, `2` | no | Places after the comma in plus and minus tasks: 0 for whole numbers, 1 for tenths or 2 for hundredths. Default 0. |
| money | boolean |  | no | Whether the numbers are money, always with two places after the comma. Default false. |
| af | list of list of number |  | no | The digits of the first number's places after the comma, tenths first, one range of 0 to 9 per place. Left out, any digit. |
| bf | list of list of number |  | no | The digits of the second number's places after the comma, tenths first, one range of 0 to 9 per place. Left out, any digit. |
| cf | list of list of number |  | no | The digits of the third number's places after the comma, tenths first, one range of 0 to 9 per place. Left out, any digit. |
| family | string | `none`, `swap`, `reverse`, `neighbour` | no | Families of related tasks: "none" makes single tasks, "swap" a task with its swapped numbers, "reverse" with its opposite operation, "neighbour" with its neighbouring tasks. A family has two or three tasks. Default "none". |
| moves | string | `a`, `b` | no | Which number a neighbouring task moves: "a" the first, the default, or "b" the second. |
| gaps | list of string | `a`, `b`, `c`, `result` | no | What a gap may hide: any of the numbers "a", "b" and "c", or the "result". Left out, a gap hides any number and never the result. |
| zero | boolean |  | no | Whether 0 may be a number and a result. Default true. |
| one | boolean |  | no | Whether 1 may be a factor or a divisor in times and divide tasks. Default true. |
| distinct | boolean |  | no | Whether tasks with equal numbers are left out. Default false. |
| small | boolean |  | no | Whether times and divide tasks stay in the small one-times table (Kleines Einmaleins): every factor, divisor and quotient from 1 to 10. Default false. |
| minus | string | `fill`, `unbundle`, `extend` | no | How a written subtraction is drawn. "fill" is Ergänzungsverfahren: the small carry sits in the next column, between the numbers and the line. "unbundle" is Entbündelungsverfahren: the changed digits sit above the first number. "extend" is Abziehverfahren mit Erweitern: a small 1 above the first number's digit and a small 1 on the next digit of the second number. Default "fill". |
| stellen | boolean |  | no | Stellenwerte: true draws the place letters over a written plus or minus, E Z H T from the right, and ZT HT M where the number needs them. Default false. |
| signs | string | `all`, `last` | no | Where a written sum of more than two numbers puts its signs: "all" on every number but the first, "last" only on the last. Default "all". Two numbers look the same either way. |
| pa | string |  | no | Pattern of the first number: "X" is any digit, a digit is fixed, and the length is the number of digits, as in "X0" or "20". Empty means no pattern. At most two of the first number, the second and the result are fixed, with no "X". |
| pb | string |  | no | Pattern of the second number, as for the first. For a written plus of more than two numbers it is the pattern of each following number. Empty means no pattern. |
| pr | string |  | no | Pattern of the result, as for the first number, as in "100". Empty means no pattern. A comparison has no result pattern. |
| nil | object |  | no | Whether the digit 0 may occur, per operation family. A missing family allows it. A 0 the pattern itself asks for counts. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "maths", "props": {}}
```
