---
type: Explanation
title: mm and pt
description: Lengths are mm from the paper's top left, font sizes are pt, and a text box needs room for its lines.
tags: [units, mm, pt, layout, text]
covers: [text, maths]
generated: { by: "human:pgoell", at: 2026-10-18T04:30:00Z }
---

# mm and pt

A doc has two units. Every length is mm. Every font size is pt. There is no other unit: no px, no cm, no %.

## Lengths are mm

Every `x`, `y`, `w`, `h`, guide and `grid` is in mm, counted from the paper's top left corner. `x` grows to the right. `y` grows down.

This holds for both orientations. Upright, the paper is 210 mm wide and 297 mm tall. Quer (`landscape: true`) turns it on its side: 297 mm wide and 210 mm tall. The numbers still start at the top left of the paper as it lies.

Keep 15 mm from each edge. Upright that is x 15 to 195 and y 15 to 282. Quer it is x 15 to 282 and y 15 to 195. See the [page model](page-model.md).

## Font sizes are pt

`size` on a text, maths or selbstkontrolle block is in pt. 1 pt = 25.4/72 mm, about 0.353 mm. Give the size in pt. Do not convert it to mm.

## How tall a text box is

A line of text takes its size times the line spacing. The default spacing is 1.3, so a line takes size x 1.3 pt. In mm, a line is size x 1.3 x 0.353 mm.

| Size | Line (pt) | Line (mm) |
|---|---|---|
| 11 pt | 14.3 | 5.0 |
| 14 pt | 18.2 | 6.4 |
| 20 pt | 26.0 | 9.2 |
| 28 pt | 36.4 | 12.8 |

A box holds lines one under the other. Three lines of 14 pt need about 19.3 mm. Give the box at least that height, plus room for the spacing you want.

## Maths blocks

Do not work out a maths block's height. The server gives it with the exercises. Read the `h` in the answer and place the next block from there. With `add_block` an `h` you pass wins over the server's height, so leave it out unless you need a box of another height. With `replace_doc` a maths block with empty `exercises` always gets the server's height.

## Never px

Do not write px. A number in a doc is mm or pt by its field, and that is all.
