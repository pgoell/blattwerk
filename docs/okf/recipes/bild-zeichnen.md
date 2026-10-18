---
type: How-to
title: "Ein Bild zeichnen und platzieren"
description: A heading, a name line, one simple line drawing made as SVG and uploaded, and three labels to write on the picture.
tags: [bild, svg, sachunterricht, klasse-1]
covers: [text, image]
generated: { by: "human:pgoell", at: 2026-10-18T04:30:00Z }
---

# Ein Bild zeichnen und platzieren

When a teacher asks for a picture, such as a flower, a tree or a house for Sachunterricht, draw it yourself. Do not look for a picture elsewhere: the server cannot fetch one.

* Draw a simple black line drawing as SVG. Use `xmlns`, a `viewBox`, black strokes of 2 to 4 wide, and `fill="none"` or a light grey fill.
* Put no text in the SVG. Write the labels as text blocks.
* Leave out script, links, external pictures and fonts. The server removes them.
* Call `upload_picture` with the SVG text. It answers the upload id and the ratio.
* Call `add_block` with `type: "image"` and `props.upload` set to that id. Place it with `x` and `y` at least 15 mm from the edge.
* Add the heading and the labels as text blocks.
* Call `render_preview` and check the page.

Example, a flower with a stem and two leaves. The viewBox is square, so the ratio is 1:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none" stroke="#000" stroke-width="3">
  <circle cx="50" cy="14" r="8" fill="#eee"/>
  <circle cx="64" cy="28" r="8" fill="#eee"/>
  <circle cx="50" cy="42" r="8" fill="#eee"/>
  <circle cx="36" cy="28" r="8" fill="#eee"/>
  <circle cx="50" cy="28" r="6" fill="#fff"/>
  <path d="M50 42 V92"/>
  <path d="M50 76 C38 70 30 62 28 52 C40 56 48 64 50 76 Z"/>
  <path d="M50 66 C60 60 70 52 74 42 C62 46 54 56 50 66 Z"/>
</svg>
```

* The `upload_picture` answer gives the id, for example `{"upload": 1, "ratio": 1}`. The ratio is the width over the height of the picture.
* Set `w` and `h` so the ratio holds: a square picture at 100 mm wide is 100 mm high.
* In the editor a teacher puts a picture of their own on the sheet with the button "Bild" in the insert bar, group "Einfügen".
* See [image](../blocks/image.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. The `upload` prop is the id that `upload_picture` answered. Upload 1 is only an example: use the id you got.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "3e8f1a02-6b4c-4d1e-8a2f-5c9b7d0e4f01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Die Blume",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3e8f1a02-6b4c-4d1e-8a2f-5c9b7d0e4f02",
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
          "id": "3e8f1a02-6b4c-4d1e-8a2f-5c9b7d0e4f03",
          "type": "image",
          "x": 55,
          "y": 60,
          "w": 100,
          "h": 100,
          "z": 3,
          "locked": false,
          "props": {
            "upload": 1,
            "ratio": 1,
            "cut": [0, 0, 0, 0]
          }
        },
        {
          "id": "3e8f1a02-6b4c-4d1e-8a2f-5c9b7d0e4f04",
          "type": "text",
          "x": 160,
          "y": 75,
          "w": 35,
          "h": 10,
          "z": 4,
          "locked": false,
          "props": {
            "text": "Blüte",
            "size": 14,
            "align": "left"
          }
        },
        {
          "id": "3e8f1a02-6b4c-4d1e-8a2f-5c9b7d0e4f05",
          "type": "text",
          "x": 160,
          "y": 125,
          "w": 35,
          "h": 10,
          "z": 5,
          "locked": false,
          "props": {
            "text": "Stängel",
            "size": 14,
            "align": "left"
          }
        },
        {
          "id": "3e8f1a02-6b4c-4d1e-8a2f-5c9b7d0e4f06",
          "type": "text",
          "x": 15,
          "y": 120,
          "w": 35,
          "h": 10,
          "z": 6,
          "locked": false,
          "props": {
            "text": "Blatt",
            "size": 14,
            "align": "left"
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
