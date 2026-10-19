---
type: How-to
title: "Zerlegungsfelder"
description: A heading, a name line, and six Zerlegungsfelder bis 20 for the Zehnerübergang in two steps, with the first and the second number given and the split and the result to fill in.
tags: [zerlegungsfeld, zehnerübergang, klasse-1]
covers: [text, name, zerlegungsfeld]
generated: { by: "human:pgoell", at: 2026-10-20T02:00:00Z }
---

# Zerlegungsfelder

When a teacher asks for: "Ein Arbeitsblatt mit sechs Aufgaben zum Zehnerübergang bis 20 im Zerlegungsfeld."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the fields are the button "Zerlegungsfeld" in the menu "Mathe-Blöcke" in the insert bar. A Zerlegungsfeld shows each task a + b with the second number split into the part that reaches the full ten and the rest, then the two steps: a + part = ten, ten + rest = the result.
* `count` is the number of tasks (1 to 12, default 6) and `columns` how many sit side by side (1 to 3, default 3).
* `op` is "+" (Plus, the default) or "-" (Minus).
* `max` is the Zahlenraum, 20, 100 or 1000 (default 20).
* `step` is "zehner" (default) or "hunderter" (only with max 1000).
* `big` set to false (default) draws the second number below ten, as in 8 + 5. `true` draws one of at least ten, as in 3 + 34.
* `task` says which boxes the pupil sees: "task" (default) gives the first and the second number; "split" also gives the two parts of the split; "result" gives the first number and the result.
* The block's height follows its tasks. Six tasks in three columns at 180 mm wide are 128.9 mm tall.
* See [zerlegungsfeld](../blocks/zerlegungsfeld.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new tasks and drop the typed numbers, and a task whose typed numbers do not fit is marked wrong.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "7e2b9d41-4f05-4a18-8c63-1d9e5b2f0a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zerlegungsfelder",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "7e2b9d41-4f05-4a18-8c63-1d9e5b2f0a02",
          "type": "name",
          "x": 15,
          "y": 35,
          "w": 180,
          "h": 18,
          "z": 2,
          "locked": false,
          "props": {}
        },
        {
          "id": "7e2b9d41-4f05-4a18-8c63-1d9e5b2f0a03",
          "type": "zerlegungsfeld",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 128.9,
          "z": 3,
          "locked": false,
          "props": {
            "count": 6,
            "columns": 3,
            "op": "+",
            "max": 20,
            "step": "zehner",
            "big": false,
            "task": "task",
            "seed": 7
          }
        }
      ]
    }
  ],
  "guides": {
    "x": [],
    "y": []
  },
  "grid": 0
}
```
