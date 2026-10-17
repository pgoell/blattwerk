---
type: How-to
title: "Sprechblase und Rahmen"
description: A heading, a name line, a speech bubble with a question inside, and a frame to write the answer in.
tags: [form, sprechblase, rahmen, klasse-1]
covers: [text, name, shape]
generated: { by: "human:pgoell", at: 2026-10-17T16:00:00Z }
---

# Sprechblase und Rahmen

When a teacher asks for: "Ein Blatt mit einer Sprechblase als Frage und einem Rahmen für die Antwort."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor these are the buttons "Sprechblase" and "Rechteck" in the group "Formen" under Einfügen. The bubble holds the question in its `text` prop, the frame holds the pupil's answer.
* See [shape](../blocks/shape.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the words of the question for another task.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "5e2b9c41-8a7d-4f3e-9c16-3b1a0d7e4f01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Sprechblase und Rahmen",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "5e2b9c41-8a7d-4f3e-9c16-3b1a0d7e4f02",
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
          "id": "5e2b9c41-8a7d-4f3e-9c16-3b1a0d7e4f03",
          "type": "shape",
          "x": 15,
          "y": 60,
          "w": 120,
          "h": 50,
          "z": 3,
          "locked": false,
          "props": {
            "kind": "bubble",
            "fill": "none",
            "stroke": "#222222",
            "strokeWidth": 0.5,
            "inside": true,
            "floor": true,
            "text": "Wie viele Äpfel liegen auf dem Tisch?",
            "size": 14,
            "align": "center",
            "valign": "middle"
          }
        },
        {
          "id": "5e2b9c41-8a7d-4f3e-9c16-3b1a0d7e4f04",
          "type": "shape",
          "x": 15,
          "y": 120,
          "w": 180,
          "h": 60,
          "z": 4,
          "locked": false,
          "props": {
            "kind": "rect",
            "fill": "none",
            "stroke": "#222222",
            "strokeWidth": 0.5,
            "inside": true,
            "floor": true,
            "text": "Antwort:",
            "size": 14,
            "align": "left",
            "valign": "top"
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
