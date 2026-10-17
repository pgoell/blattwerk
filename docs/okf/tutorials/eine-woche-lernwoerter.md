---
type: Tutorial
title: A week of Lernwörter sheets
description: For Claude. One Montag sheet with a word list and a trace ruling, copied for Dienstag to Freitag, each copy with its own words.
tags: [tutorial, lernwoerter, silbenboegen, klasse-1]
covers: [text, name, ruling]
generated: { by: "human:pgoell", at: 2026-10-17T20:50:00Z }
---

# A week of Lernwörter sheets

For Claude. Build one sheet for Montag, then copy it for the other four days and set each copy's words. Each step is one tool call. Read each answer before the next call.

The word list belongs to the sheet. `set_words` changes it, and a linked ruling (Lineatur) follows it: one row for each word. Every write needs the `version` of the last answer.

1. Call `create_sheet` with the title `"Montag"`. The answer gives `id` (here 7) and `version` (here 1).

```json create_sheet
{"title": "Montag"}
```

2. Call `add_block` with `sheet_id` 7, `version` 1, `page` 1 and the heading below. The answer gives `version` (2).

```json
{"type": "text", "props": {"text": "Lernwörter Montag", "size": 20, "align": "left"}, "x": 15, "y": 15, "w": 180, "h": 14}
```

3. Call `add_block` with `version` 2. The name line goes at `y` 34. The answer gives `version` (3) and `block.h` (18 here).

```json
{"type": "name", "props": {}, "x": 15, "y": 34, "w": 180, "h": 18}
```

4. Call `set_words` with `version` 3 and the five words. The answer gives `version` (4).

```json set_words
{"sheet_id": 7, "version": 3, "words": ["Schule", "Hund", "Katze", "Ball", "Maus"]}
```

5. Call `add_block` with `version` 4. The ruling goes at `y` 57, which is 34 + 18 + 5. `list` `"trace"` writes each word in grey for the child to write over. `syllables` `true` draws a bow under each syllable. The answer gives `version` (5) and `block.h`. Use `block.h` for the next step.

```json
{"type": "ruling", "props": {"kind": "l2", "color": "#222222", "list": "trace", "syllables": true}, "x": 15, "y": 57, "w": 180, "h": 60}
```

6. Call `render_preview` with `sheet_id` 7. Check that the five words sit on the ruling with a bow under each syllable.

```json render_preview
{"sheet_id": 7, "page": 1}
```

7. Call `duplicate_sheet` with `sheet_id` 7. The copy gets its own `id` (here 8) and `version` (here 1). Do this from Montag each time, never from a copy.

```json duplicate_sheet
{"sheet_id": 7}
```

8. Call `rename_sheet` with `sheet_id` 8 and the title `"Dienstag"`. The `version` stays 1, because a rename does not change the doc.

```json rename_sheet
{"sheet_id": 8, "title": "Dienstag"}
```

9. Call `get_sheet` with `sheet_id` 8. Use the `version` it gives (here 1) in the next call.

```json get_sheet
{"sheet_id": 8}
```

10. Call `set_words` with `sheet_id` 8 and that `version`, and the Dienstag words. The answer gives the new `version` (2).

```json set_words
{"sheet_id": 8, "version": 1, "words": ["Baum", "Haus", "Tisch", "Stuhl", "Lampe"]}
```

The copy's heading still says "Lernwörter Montag". Call `update_block` with that `version` (2) and the heading's `id` from the `doc` that `get_sheet` gave. The answer gives `version` (3).

```json update_block
{"sheet_id": 8, "version": 2, "block_id": "<the heading's id>", "props": {"text": "Lernwörter Dienstag"}}
```

11. Repeat steps 7 to 10 and the heading for the other days. Each copy is made from sheet 7, so each new copy has its own id. Use the id and `version` that each answer gives. Take the words from this list:

* Mittwoch: `"Blume", "Auto", "Fisch", "Tasse", "Wolke"`
* Donnerstag: `"Apfel", "Birne", "Eule", "Igel", "Boot"`
* Freitag: `"Ente", "Fuchs", "Kuh", "Pferd", "Regen"`

12. Call `render_preview` with the `sheet_id` of Dienstag (here 8). The ruling has five rows and the new words. It follows the list: no row was drawn by hand.

```json render_preview
{"sheet_id": 8, "page": 1}
```

13. Tell the teacher that the five sheets are under "Meine Blätter" in Blattomat, one for each day. She opens each in the editor and prints it herself. You never print.
