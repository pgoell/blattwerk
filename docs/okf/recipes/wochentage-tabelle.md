---
type: How-to
title: "Wochentage als Tabelle"
description: A heading, a name line, and a table with the weekdays Montag to Freitag in a bold head row.
tags: [tabelle, wochentage, klasse-1]
covers: [text, name, table]
generated: { by: "human:pgoell", at: 2026-10-18T04:30:00Z }
---

# Wochentage als Tabelle

When a teacher asks for: "Ein Blatt mit einer Tabelle für die Wochentage, Montag bis Freitag."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the table is the button "Tabelle" in the insert bar, group "Einfügen". Its `cells` hold the text of each cell, row by row, and `cols` the width share of each column. `head` true sets the first row in bold.
* See [table](../blocks/table.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the cells for other words.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "d4a9c2e6-1f7b-4e8d-b3a2-6c5e0f9d8a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Die Wochentage",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "d4a9c2e6-1f7b-4e8d-b3a2-6c5e0f9d8a02",
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
          "id": "d4a9c2e6-1f7b-4e8d-b3a2-6c5e0f9d8a03",
          "type": "table",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 30,
          "z": 3,
          "locked": false,
          "props": {
            "cells": [
              ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"],
              ["", "", "", "", ""]
            ],
            "cols": [1, 1, 1, 1, 1],
            "rows": [10, 20],
            "size": 14,
            "align": "center",
            "line": "#222222",
            "head": true
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
