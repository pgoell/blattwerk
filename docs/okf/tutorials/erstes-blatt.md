---
type: Tutorial
title: Your first sheet
description: For Claude. A heading, a name line and twelve plus sums to 20 with a seed, placed one under the other and checked with a preview.
tags: [tutorial, maths, klasse-1]
covers: [text, name, maths]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Your first sheet

For Claude. Build a one-page sheet from nothing. Each step is one tool call. Read each answer before the next call.

The sheet has a heading, a name line and a maths block. Blocks stack down the page: the next `y` is the last block's `y + h + 5`. Use the `h` that the answer gives, not the one you sent.

1. Call `create_sheet` with the title `"Plusaufgaben bis 20"`. The answer gives `id` (here 7) and `version` (here 1). Use them in every later call.

```json create_sheet
{"title": "Plusaufgaben bis 20"}
```

2. Call `add_block` with `sheet_id` 7, `version` 1, `page` 1 and the heading below. The answer gives `version` (2) and `block.h`. Check that `warnings` is empty.

```json
{"type": "text", "props": {"text": "Plusaufgaben bis 20", "size": 20, "align": "left"}, "x": 15, "y": 15, "w": 180, "h": 14}
```

3. Call `add_block` with `version` 2. Place the name line at `y` 34, which is 15 + 14 + 5. The answer gives `version` (3) and `block.h` (18 here).

```json
{"type": "name", "props": {}, "x": 15, "y": 34, "w": 180, "h": 18}
```

4. Call `add_block` with `version` 3. Place the maths block at `y` 57, which is 34 + 18 + 5. Leave out `h`: the server sets the height from the tasks. The answer gives `version` (4), `block.id` and `block.h`. Keep `block.h` for step 5.

```json
{"type": "maths", "props": {"ops": ["+"], "max": 20, "carry": "either", "rest": false, "format": "row", "count": 12, "seed": 42, "columns": 3, "size": 14}, "x": 15, "y": 57, "w": 180}
```

5. Read the answer of step 4. Check that `warnings` is empty and that `block.h` is set. The last block ends at `57 + block.h`. Stop there: the sheet holds three blocks and nothing goes below them.

6. Call `render_preview` with `sheet_id` 7. It answers the page as a picture. Look for blocks that overlap, text that is cut off and anything past the edge of the printable area.

```json render_preview
{"sheet_id": 7, "page": 1}
```

7. Tell the teacher that the sheet is under "Meine Blätter" in Blattomat. She opens it in the editor, changes what she likes and prints it herself. You never print.
