---
type: How-to
title: "Stellenwert-Bild"
description: A heading, a name line, and four Stellenwert-Bilder bis 1000 with Hunderterplatten, Zehnerstangen and Einerwürfel shown, the number to write in a Stellenwerttafel.
tags: [stellenwertbild, stellenwert, zahlen, klasse-2]
covers: [text, name, stellenwertbild]
generated: { by: "human:pgoell", at: 2026-11-06T16:30:00Z }
---

# Stellenwert-Bild

When a teacher asks for: "Ein Arbeitsblatt mit vier Stellenwert-Bildern bis 1000: die Kinder schreiben die Zahl."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the block is the button "Stellenwert-Bild" in the menu "Mathe-Blöcke" in the insert bar.
* A Stellenwert-Bild block shows each task as a picture of pieces: a Hunderterplatte for each hundred, a Zehnerstange for each ten and an Einerwürfel for each one. Under the picture the pupil writes the number in the box.
* `count` is the number of tasks (1 to 12, default 4) and `columns` how many sit side by side (1 to 4, default 2).
* `max` is the Zahlenraum: 1000 (default for this recipe) or 100.
* `task` is "read" (Bild gegeben, Zahl schreiben, the default for this recipe) or "draw" (Zahl gegeben, Bild zeichnen).
* `table` set to true (default) puts a Stellenwerttafel with the places H, Z and E before the number box. It plays a part only with "read".
* `zero` set to false (default) gives numbers without a 0 digit. `bundle` set to false (default) gives pictures with no more than 9 pieces in a place.
* `seed` gives the tasks. The same seed gives the same tasks. Change the seed to change them.
* See [stellenwertbild](../blocks/stellenwertbild.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new tasks and drop the typed numbers.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "5c2e8a17-3f4b-4d9e-9a61-7b0d2e4f8a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Stellenwert-Bild",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "5c2e8a17-3f4b-4d9e-9a61-7b0d2e4f8a02",
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
          "id": "5c2e8a17-3f4b-4d9e-9a61-7b0d2e4f8a03",
          "type": "stellenwertbild",
          "x": 15,
          "y": 60,
          "w": 175,
          "h": 119,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 2,
            "max": 1000,
            "task": "read",
            "table": true,
            "zero": false,
            "bundle": false,
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
