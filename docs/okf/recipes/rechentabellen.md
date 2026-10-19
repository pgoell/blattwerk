---
type: How-to
title: "Rechentabellen"
description: A heading, a name line, and a Maltabelle of the 2er, 5er and 10er Reihe with the row values given and the result cells to fill in.
tags: [rechentabelle, einmaleins, klasse-2]
covers: [text, name, rechentabelle]
generated: { by: "human:pgoell", at: 2026-10-19T12:45:00Z }
---

# Rechentabellen

When a teacher asks for: "Ein Arbeitsblatt mit einer Maltabelle für die 2er-, 5er- und 10er-Reihe."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the tables are the button "Rechentabelle" in the menu "Mathe-Blöcke" in the insert bar. A Rechentabelle is a grid: row values down the left, column values along the top, the operator in the corner, and each result cell the row value worked with the column value.
* `op` picks the Rechenart: "+" (Plustabelle), "-" (Minustabelle), "*" (Maltabelle, Einmaleins-Tabelle) or ":" (Geteilt-Tabelle).
* Plus and Minus: `max` is the Zahlenraum (10, 20, 100 or 1000) and `carry` the Übertrag ("none", "required" or "either", the default).
* Mal and Geteilt: `reihen` lists the Einmaleins-Reihen as the column values, `order` puts them in "related" order (default) or "random", and `first` picks the row values: "all" (1 to 10, the default), "kings" (1, 2, 5, 10) or "near" (3, 4, 6, 9).
* `rows` and `cols` are the number of row and column values per table, 2 to 10.
* `hideRows` and `hideCols` hide that many row and column values; a result cell in each hidden value's row or column is given, so the pupils work the value back. Use them for "Werte rückwärts finden".
* `tint` colours the value cells: "none" (default), "blue", "green", "yellow", "red" or "purple".
* `count` is the number of tables (1 to 4) and `columns` how many sit side by side (1 to 3).
* The block's height follows its tables: two tables side by side at 180 mm wide with 10 rows are 183.30 mm tall.
* See [rechentabelle](../blocks/rechentabelle.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. A typed number stays fixed in every Variante, and a table whose typed numbers do not fit is marked wrong.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tables.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "7c1d9e42-5b6a-4f3e-8a21-d0b4e6f93a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Rechentabellen",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "7c1d9e42-5b6a-4f3e-8a21-d0b4e6f93a02",
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
          "id": "7c1d9e42-5b6a-4f3e-8a21-d0b4e6f93a03",
          "type": "rechentabelle",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 183.3,
          "z": 3,
          "locked": false,
          "props": {
            "count": 2,
            "columns": 2,
            "rows": 10,
            "cols": 3,
            "op": "*",
            "max": 20,
            "carry": "either",
            "reihen": [2, 5, 10],
            "order": "related",
            "first": "all",
            "hideRows": 0,
            "hideCols": 0,
            "tint": "none",
            "seed": 5
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
