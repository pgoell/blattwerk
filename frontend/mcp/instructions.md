Blattomat makes worksheets for German primary school (Grundschule).

Page: A4 portrait, 210 x 297 mm (a landscape page is 297 x 210). Units are mm. Keep a margin of 15 mm from the edges.

A doc is `{"pages": [{"blocks": [...]}], "guides": {"x": [], "y": []}, "grid": 0}`. Every block has `id` (a unique string), `type`, `x`, `y` (top left), `w`, `h`, `z` (1 and up, higher lies on top), `locked` (false) and `props`. Blocks must not overlap: stack them, so the next block's y is the last block's y + h + 5.

Block types (the tool schemas list every prop):
- `text`: `text`, `size` (pt), `align`. `shape`: `kind` (rect, rounded, circle, triangle, star, bubble, line, arrow), may hold `text`.
- `ruling` (Lineatur): `kind` (l1, l2, l3, l4, lines, k5, k7). `name` (Namenszeile), `points` (Punkte), `symbol`, `table` (`cells`, `cols`).
- `image`: `upload`, the id of a picture the teacher uploaded (find it on one of their sheets).
- `maths`: `ops`, `max`, `count`, `columns`, `size`. The server makes the exercises and the height.
- `suchsel` (`words`), `zahlenmauer`, `rechendreieck`, `zahlenstrahl`, `hunderterfeld`, `uhr` (`count` clocks), `selbstkontrolle`: their content comes from their settings and `seed`.

Workflow: create_sheet; add_block for each block (it starts as the editor's block of that type, with your props on top, and grows where its content needs room); update_block, move_block, delete_block to change; add_page, set_page, set_words (Lernwörter). Every write takes the version of the last answer. A warning in the answer says a block overlaps another or leaves the page: fix it with move_block. render_preview to look. replace_doc writes a whole doc at once.
