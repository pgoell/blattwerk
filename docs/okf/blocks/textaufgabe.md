---
type: Reference
title: "Block: textaufgabe"
description: "Word problems (Textaufgaben): a story, a question, a Rechnung on squared paper and an Antwort line."
tags: [block, textaufgabe]
covers: [textaufgabe]
generated: { by: "process:frontend/okf.mjs", at: 2026-11-02T22:37:39Z }
---

# textaufgabe

Word problems (Textaufgaben): a story, a question, a Rechnung on squared paper and an Antwort line. The numbers come from a text pool, or the teacher writes all four parts.

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
| count | number | 1 to 4 | yes | Number of Textaufgaben, one under the other. Default 2. |
| themes | list of string | `kurz`, `sach`, `raetsel`, `zeit`, `geld` | yes | The Themen the stories are drawn from: "kurz" (kurze Texte), "sach" (Sachaufgaben), "raetsel" (Rätsel), "zeit" (Zeit) and "geld" (Geld). Default ["sach"]. |
| ops | list of string | `+`, `-`, `*`, `:` | yes | The Rechenarten: "+", "-", "*" (Mal) and ":" (Geteilt), in that order, each once. Empty or not a list: ["+"]. Default ["+"]. |
| steps | number | `1`, `2` | yes | The Komplexität: 1 for one step, 2 for two steps. Any other value gives 1. Default 1. |
| max | number |  | yes | The Zahlenraum: the largest number a task may use, one of 10, 20, 100 or 1000. Geld counts in euros, a Dauer in minutes. Any other value gives 20. Default 20. |
| numbers | string | `whole`, `decimal` | yes | The Zahlen: "whole" for natürliche Zahlen, "decimal" for Kommazahlen (two places). Geld is always Kommazahlen, a Zeit stays a clock. Default "whole". |
| carry | string | `any`, `yes`, `no` | yes | The Übertrag of an addition or a subtraction: "any" (egal), "yes" (mit Übergang) or "no" (ohne Übergang). It is a ten, or a euro for Kommazahlen. Mal and Geteilt ignore it. Default "any". |
| frage | boolean |  | yes | Whether the Frage is printed for the pupil. The Lösungen fill it when it is not. Default true. |
| rechnung | boolean |  | yes | Whether the Rechnung is printed for the pupil. The Lösungen fill it when it is not. Default false. |
| antwort | boolean |  | yes | Whether the Antwort is printed for the pupil. The Lösungen fill it when it is not. Default false. |
| sketch | boolean |  | yes | Whether a drawing box (Zeichenfeld) stands above the Rechnung. Default false. |
| rows | string or number | `auto` | yes | The height of the Rechnung: "auto" (one row per step, plus one row to write in) or a number of rows from 1 to 8. Default "auto". |
| manual | boolean |  | yes | Manual mode: the teacher writes the Text, the Frage, the Rechnung and the Antwort. Default false. |
| zeit | string | `punkt`, `dauer`, `both` | yes | Which Zeit stories are drawn when the theme "zeit" is on: "punkt" (Zeitpunkte), "dauer" (Dauern) or "both". Default "both". |
| seed | number |  | yes | Seed for the stories and the numbers. The same seed always gives the same tasks. |
| written | list of object |  | no | The four parts the teacher wrote, one entry per task, in order. Used when manual is on. |

# Examples

An empty block of this type as `add_block` takes it:

```json
{"type": "textaufgabe", "props": {}}
```
