Blattomat makes worksheets for German primary school (Grundschule).

Page: A4 portrait, 210 x 297 mm. Units are mm. Keep a margin of 15 mm from the edges.

Every block has x, y (top left), w, h and z. Blocks must not overlap: stack them, so the next block's y is the last block's y + h + 5.

Three block types in this version:
- `text`: props `text`, `size` (pt), `align` (left, center, right).
- `maths`: props `ops` (["+", "-", "*", "/"]), `max` (Zahlenraum), `count`, `columns` (1 to 6), `size` (pt). Leave out `exercises`: the server fills them and sets the block's height.
- `ruling` (Lineatur): props `kind` (l1, l2, l3, l4, lines, k5, k7), `color` ("#222222"). For a name line use a ruling of kind "l4", about 10 mm high, or a text "Name: ____".

Workflow: create_sheet, get_sheet for the version, replace_doc with the whole doc, render_preview to look, fix overlaps.
