---
okf_version: "0.2"
---

# Blattomat

Blattomat makes worksheets (Arbeitsblätter) for German primary school (Grundschule). A teacher asks you for a sheet; you make it in their Blattomat account with the tools, and they open it in the editor, change it and print it.

Language: German for every word that lands on the sheet or that a teacher reads (task texts, headings, the tutorial). English for the reference, the recipes' notes and this index, which are for you.

In brief: a sheet is A4 upright, 210 x 297 mm, and every number is in mm. A block sits at `x`, `y` (its top left) with size `w`, `h`. Keep 15 mm from each edge. Blocks must not overlap: put the next block at the last block's `y + h + 5`. Read [the page model](page-model.md) before your first sheet.

Every file named here is a resource of this server: the link `blocks/uhr.md` is the resource `blattomat://okf/blocks/uhr.md`.

Before you write a block, read its page under [blocks](blocks/index.md): it lists every prop with its values. Before you build a whole sheet, look for a recipe that is close and start from its doc.

Work like this: `create_sheet`; `add_block` for each block, or `replace_doc` with a recipe's doc; read the warnings in each answer (`overlaps block <id>`, `leaves the page's printable area`) and fix them with `move_block`; `render_preview` to look at the page before you say you are done.

# Explanation

* [Page model](page-model.md): How a Blattomat sheet is laid out, A4 in mm, the box of each block, z order, pages, guide lines and the grid.
* [mm and pt](mm-and-pt.md): Lengths are mm from the paper's top left, font sizes are pt, and a text box needs room for its lines.
* [What the server computes](server-computes.md): What the server computes for maths and other seeded blocks, and when a seed gives the same tasks.
* [Versions and the 409 rule](versions.md): How sheet versions work, what a stale write answers, and what to do before you write again.
* [What the teacher does herself](teacher-does.md): What the teacher does herself, such as printing, PDFs, the answer key, variants and locked blocks.

# Reference

* [Blocks](blocks/index.md): one page per block type, generated from the sheet's schema.
* [Tools](tools/index.md): each tool's errors and limits.

# How-to

* [Recipes](recipes/index.md): whole sheets for common tasks, each a doc that passes the schema.

# Tutorial

* [Tutorials](tutorials/index.md): for teachers, in German.
