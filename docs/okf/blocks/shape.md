---
type: Reference
title: "Block: shape"
description: "The shape's form, fill and border, and the text it may hold: every field of a text block may stand here too."
tags: [block, shape]
covers: [shape]
generated: { by: "process:frontend/okf.mjs", at: 2026-10-16T00:00:00Z }
---

# shape

The shape's form, fill and border, and the text it may hold: every field of a text block may stand here too.

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
| kind | string | `rect`, `rounded`, `circle`, `triangle`, `star`, `bubble`, `line`, `arrow`, `double` | yes | Outline of the box the text sits in: "rect", "rounded", "circle", "triangle", "star" or "bubble". Absent means rect. |
| fill | string |  | yes | Colour inside the box as a hex colour. "none" or absent means no fill. |
| stroke | string |  | yes | Colour of the border as a hex colour. "none" or absent means no border. |
| strokeWidth | number | at most 3 | yes | Width of the border in mm. Absent means 0.5. |
| from | string | `nw`, `ne`, `sw`, `se` | no | For a line or an arrow: the corner of the box where it starts, "nw" top left, "ne" top right, "sw" bottom left, "se" bottom right. The line runs to the opposite corner. Absent means "nw". |
| ticks | boolean |  | no | True puts a short cross stroke at each end of a line. Absent means no ticks. |
| label | string | `show`, `key` | no | Prints the length of a line: "show" on the sheet, "key" on the answer key only. Absent means no length. |
| text | string |  | no | The words of the text as one plain string, with no look of their own. Always the same words as `rich`. |
| rich | list of object |  | no | The paragraphs with their own looks. Absent when one look covers the whole text: `text` then holds all of it. |
| syllables | boolean |  | no | True draws a bow under each syllable of each word (Silbenbögen). Absent means off. |
| breaks | object |  | no | The words the teacher split by hand into syllables. Absent means the program alone splits the words. |
| tints | list of string |  | no | The two colours the syllables take in turn, the first and then the second, such as blue and red. Absent means the syllables are not coloured in turn. |
| tintsAcross | boolean |  | no | True carries the colour turn on from word to word through the text. Absent means each word starts again with the first colour. |
| gapWidth | number | at most 200 | no | Every gap in the text is at least this many mm wide, so a pupil has room to write. Absent or 0 means each gap is only as wide as its word. Capped at 200 mm. |
| bank | number |  | no | Seed for the box of hidden words set under the text (Lösungswörter). The box shows the words shuffled in an order this seed sets. Absent means no box. |
| lines | number |  | no | Numbers the lines of the text as they break, in the margin. 1 numbers every line, 5 every fifth line. Absent means no numbers. |
| linesFrom | number | 1 to 9999 | no | The number of the first line, for the numbering in `lines`. Absent means 1. |
| mix | number |  | no | Seed for the scrambled words (Schüttelwörter). Each word shows its letters in another order, the same on every draw. Absent means no scrambling. |
| mixFirst | boolean |  | no | True keeps the first letter of each scrambled word in place. Absent means the first letter is scrambled too. |
| mixCaps | boolean |  | no | True sets the letters of the scrambled words in capitals. |
| mixLine | string | `after`, `under` | no | Where the pupil writes each scrambled word: "after" puts a line after it, "under" a line under it. Absent means no line, except that a list draws it after each word. |
| list | boolean |  | no | True makes the text draw the sheet's Lernwörter, one word to a paragraph (Text aus Lernwörtern). Its own text stays as it is and is not shown. |
| listCols | number | 1 to 4 | no | The number of columns the list words fill, column by column. Absent means 1. |
| holes | string | `one`, `second`, `vowels` | no | Lückenwörter for a linked text: "one" gives one letter of each word as a gap, "second" every second letter, "vowels" the vowels. Absent means no gaps. |
| holeSeed | number |  | no | Seed that picks which letters become gaps under `holes`. The same seed gives the same gaps on every draw. Absent means 0. |
| size | number |  | no | Font size of the text in pt (points). |
| align | string | `left`, `center`, `right` | no | Horizontal alignment of the lines in the box: "left", "center" or "right". |
| font | string | `andika`, `nord`, `sued`, `grund`, `urff`, `va`, `sas`, `la` | no | Typeface, one of the keys of FONTS, such as "andika" (the school print). Absent means andika. |
| bold | boolean |  | no | True sets the whole text in bold. Absent means off. |
| italic | boolean |  | no | True sets the whole text in italic. Absent means off. |
| underline | boolean |  | no | True underlines the whole text. Absent means off. |
| color | string |  | no | Colour of the text as a hex colour, such as "#222222". Absent means #222222. |
| spacing | number | 1 to 3 | no | Distance from one line of the text to the next, as a multiple of the font size. Absent means 1.3. |
| valign | string | `top`, `middle`, `bottom` | no | Vertical place of the text in its box: "top", "middle" or "bottom". Absent means top. |
| opacity | number | 0 to 1 | no | How solid the fill is: 0 is invisible, 1 is solid. Absent means 1. |
| strokeOpacity | number | 0 to 1 | no | How solid the border is: 0 is invisible, 1 is solid. Absent means 1. |
| inside | boolean |  | no | True keeps a circle's, triangle's or star's text inside its outline, shrunk to fit, rather than growing the shape. Absent means off. |
| floor | boolean |  | no | Set by the editor on a shape whose text the teacher has sized: the text then keeps at least 10 pt. Absent means off. |
| dash | string | `dashed`, `dotted` | no | Style of the border: "dashed" for dashes, "dotted" for dots. Absent means a solid border. |
| trace | boolean or string | `outline` or `dotted` | no | Nachspuren: the text prints in grey to write over. true is plain grey, "outline" a thin outline of the letters, "dotted" dotted letters (in fonts that have them, else grey). Absent means no trace text. |
| fade | string | `row`, `rows` | no | How the grey of a trace text fades: "row" fades each row from left to right, "rows" fades the rows step by step down the block. Absent means no fade. Needs `trace`. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "shape", "props": {}}
```
