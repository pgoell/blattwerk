---
type: Tutorial
title: A maths sheet with an answer key
description: For Claude. A minus sheet to 20 with a gap format, and a Selbstkontrolle in mixed form that checks its results, then what the teacher does for the answer key and the variants.
tags: [tutorial, maths, selbstkontrolle, loesungen, klasse-1]
covers: [text, name, maths, selbstkontrolle]
generated: { by: "human:pgoell", at: 2026-10-18T04:30:00Z }
---

# A maths sheet with an answer key

For Claude. Build a minus sheet to 20 with a self-check for the child, then tell the teacher how to get the answer key. Each step is one tool call. Read each answer before the next call.

The Selbstkontrolle reads the results of the maths block from its `links`. Put it below the maths block: its `y` is the maths block's `y + h + 5`.

1. Call `create_sheet` with the title `"Minusaufgaben bis 20"`. The answer gives `id` (here 7) and `version` (here 1).

```json create_sheet
{"title": "Minusaufgaben bis 20"}
```

2. Call `add_block` with `sheet_id` 7, `version` 1, `page` 1 and the heading below. The answer gives `version` (2).

```json
{"type": "text", "props": {"text": "Minusaufgaben bis 20", "size": 20, "align": "left"}, "x": 15, "y": 15, "w": 180, "h": 14}
```

3. Call `add_block` with `version` 2. The name line goes at `y` 34. The answer gives `version` (3) and `block.h` (18 here).

```json
{"type": "name", "props": {}, "x": 15, "y": 34, "w": 180, "h": 18}
```

4. Call `add_block` with `version` 3. The maths block goes at `y` 57. Leave out `h`: the server sets the height from the tasks. The `format` `"gap"` leaves one number open in each task. The answer gives `version` (4), `block.id` and `block.h`. Keep both for the next steps.

```json
{"type": "maths", "props": {"ops": ["-"], "max": 20, "carry": "either", "rest": false, "format": "gap", "count": 12, "seed": 42, "columns": 3, "size": 14}, "x": 15, "y": 57, "w": 180}
```

5. Call `add_block` with `version` 4. The Selbstkontrolle goes at `y` = 57 + `block.h` + 5 from step 4. Put that value in `y`. Its `links` holds the `block.id` of the maths block. The `form` `"mixed"` lists the results shuffled, each with a box to tick. The answer gives `version` (5) and `block.h`.

```json
{"type": "selbstkontrolle", "props": {"form": "mixed", "links": ["<block.id of the maths block>"], "title": "Selbstkontrolle", "size": 14, "turn": "none", "seed": 42}, "x": 15, "y": 109, "w": 180, "h": 60}
```

The `y` above is an example: if the maths block at `y` 57 came back with `h` 47, the next `y` is 57 + 47 + 5 = 109.

6. Call `render_preview` with `sheet_id` 7. Check that the tasks, the Selbstkontrolle and the heading do not overlap and stay on the page.

```json render_preview
{"sheet_id": 7, "page": 1}
```

7. Tell the teacher these three things, in German:
* In the editor, the button "Lösungen zeigen" shows the results on screen.
* The PDF "Lösungen" prints the sheet with the results. The plain PDF has none.
* The button "Varianten drucken" makes other versions of the sheet with other tasks, so neighbours cannot copy. Each answer key carries the letter of its variant.

You never print or download. The sheet is under "Meine Blätter" in Blattomat.
