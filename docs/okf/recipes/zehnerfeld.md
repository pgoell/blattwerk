---
type: How-to
title: "Zehnerfeld"
description: A heading, a name line, and four Plusaufgaben bis 20 on a Zwanzigerfeld with the Zehnerübergang, the dots given and the sums to write.
tags: [zehnerfeld, zehnerübergang, klasse-1]
covers: [text, name, zehnerfeld]
generated: { by: "human:pgoell", at: 2026-10-20T10:00:00Z }
---

# Zehnerfeld

When a teacher asks for: "Ein Arbeitsblatt mit vier Plusaufgaben im Zwanzigerfeld bis 20 mit Zehnerübergang."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the field is the button "Zehnerfeld" in the menu "Mathe-Blöcke" in the insert bar. A Zehnerfeld block shows each task as a field of dots with the task line [a] + [b] = [r] under it. The dots of a are in colour 1, the dots of b in colour 2, and the sum is written in the box.
* `count` is the number of tasks (1 to 12, default 4) and `columns` how many sit side by side (1 to 4, default 2).
* `field` is the Typ: "zwanzig" Zwanzigerfeld 2 × 10 (default for this recipe), "zehn" Zehnerfeld 1 × 10, "zehn2" Zehnerfeld 2 × 5 or "hundert" Hunderterfeld 10 × 10.
* `op` is "+" (Plus, the default) or "-" (Minus).
* `task` is the Aufgabentyp: "dots" (Punkte gegeben, the default for this recipe), "write" (Aufgabe gegeben, Punkte malen) or "mixed" (gemischt).
* `max` is the Zahlenraum: 5, 10, 20, 50 or 100 (default 20 here), at most the field's size.
* `cross` is the Zehnerübergang: "yes" (every task crosses a ten, as in 8 + 5), "no" (none does, as in 6 + 4) or "any" (default). It counts only on the Zwanzigerfeld and the Hunderterfeld. For this recipe use "yes".
* `lines` set to true (default) draws a strong line after each five dots. `colors` is "color" (default), "grey" for a black and white copy, or "own" with `color1` and `color2`.
* `manual` set to true lets the teacher set the dots by hand in `marks`, and the number boxes stay empty for the pupil.
* The block's height follows its tasks. Four tasks in two columns are 127 mm wide and 53 mm tall, the size the insert gives.
* See [zehnerfeld](../blocks/zehnerfeld.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new tasks and drop the typed numbers, and the dots set by hand (`marks`) stay. A task whose typed numbers do not fit is marked wrong and shows no dots and no numbers.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "9a4d1f63-6b27-4c3a-8e85-3f1d2c4c4c01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zehnerfeld",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "9a4d1f63-6b27-4c3a-8e85-3f1d2c4c4c02",
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
          "id": "9a4d1f63-6b27-4c3a-8e85-3f1d2c4c4c03",
          "type": "zehnerfeld",
          "x": 15,
          "y": 60,
          "w": 127,
          "h": 53,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 2,
            "field": "zwanzig",
            "op": "+",
            "task": "dots",
            "max": 20,
            "cross": "yes",
            "lines": true,
            "colors": "color",
            "manual": false,
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
