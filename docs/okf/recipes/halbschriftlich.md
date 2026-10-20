---
type: How-to
title: "Halbschriftlich rechnen"
description: A heading, a name line, and six Plusaufgaben bis 1000 for the halbschriftliche Rechnen with the Zehnerübergang in the Einer step, the second number split place by place, with the first and the second number given and the steps and the result to fill in.
tags: [halbschriftlich, zehnerübergang, klasse-2]
covers: [text, name, halbschriftlich]
generated: { by: "human:pgoell", at: 2026-10-20T08:00:00Z }
---

# Halbschriftlich rechnen

When a teacher asks for: "Ein Arbeitsblatt mit sechs Plusaufgaben bis 1000 zum halbschriftlichen Rechnen mit Zehnerübergang."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the fields are the button "Halbschriftlich rechnen" in the menu "Mathe-Blöcke" in the insert bar. A Halbschriftlich block shows each task a + b with the second number added place by place, the highest place first: 345 + 123 is 345 + 100 = 445, 445 + 20 = 465, 465 + 3 = 468.
* `count` is the number of tasks (1 to 12, default 6) and `columns` how many sit side by side (1 to 3, default 2).
* `op` is "+" (Plus, the default) or "-" (Minus).
* `max` is the Zahlenraum, 100 or 1000 (default 1000).
* `digits` is the places of the second number, 1, 2 or 3 (default 3). 3 counts only with max 1000.
* `einer` is the Zehnerübergang: "yes" (every task crosses a ten, as in 348 + 5), "no" (none does) or "any" (default). `zehner` is the same for crossing a hundred, as the Übertrag of written arithmetic (395 + 7 and 385 + 17 cross a hundred); it counts only with max 1000. With one place, "no" at the Einer and "yes" at the Zehner leave no task.
* `head` set to true draws the place letters T H Z E above the numbers. `grid` set to false draws plain boxes instead of Karo. `ops` set to false leaves the signs of the steps out for the pupils to write.
* The block's height follows its tasks. Six tasks in two columns are 146 mm wide and 86 mm tall, the size the insert gives.
* See [halbschriftlich](../blocks/halbschriftlich.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new tasks and drop the typed numbers, and a task whose typed numbers do not fit is marked wrong.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "8f3c0e52-5a16-4b29-9d74-2e0a1c3b0b01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Halbschriftlich rechnen",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "8f3c0e52-5a16-4b29-9d74-2e0a1c3b0b02",
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
          "id": "8f3c0e52-5a16-4b29-9d74-2e0a1c3b0b03",
          "type": "halbschriftlich",
          "x": 15,
          "y": 60,
          "w": 146,
          "h": 86,
          "z": 3,
          "locked": false,
          "props": {
            "count": 6,
            "columns": 2,
            "op": "+",
            "max": 1000,
            "digits": 3,
            "einer": "yes",
            "zehner": "any",
            "grid": true,
            "head": false,
            "tint": false,
            "ops": true,
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
