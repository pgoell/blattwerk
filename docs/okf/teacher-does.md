---
type: Explanation
title: What the teacher does herself
description: What the teacher does herself, such as printing, PDFs, the answer key, variants and locked blocks.
tags: [editor, print, pdf, answers, variants, locked]
covers: [text, selbstkontrolle]
generated: { by: "human:pgoell", at: 2026-10-19T12:45:00Z }
---

# What the teacher does herself

Claude makes and changes sheets. Claude never prints and never downloads a PDF. When the teacher needs one of these, tell her which button to press.

## Print and PDF

The teacher prints the sheet herself.

The download "PDF" saves the sheet as a PDF. The download "Lösungen" saves the same sheet with the answers. Its file name ends in " Lösungen.pdf". The plain PDF has no answers.

## The answers on screen

The button "Lösungen zeigen" shows the answers on the sheet. Press it again to hide them.

The answers show: maths results, filled gaps, Zahlenmauer and Rechendreieck numbers (in red), Zahlenstrahl boxes, Uhr times, Suchsel words ringed and table cells. A text gap shows its word. A pupil sees a line there.

## Varianten

The button "Varianten drucken" opens a dialog. The teacher picks how many variants to print, letters A to D, so neighbours cannot copy. The answers carry the letter: "Die Lösungen tragen den Buchstaben immer." Nothing is stored.

Variant A is the stored sheet. Letters B to D draw new content from each block's own seed and the letter. The same letter gives the same content on every run.

* Changes: maths (new exercises), suchsel, zahlenmauer, zahlenhaus, zahlenkette, pfeilbild, operatorfeld, rechenrad, rechentabelle, rechendreieck, zahlenstrahl, hunderterfeld, uhr, selbstkontrolle (their seed), text and shape (mix, bank, holeSeed), and table (bank).
* Stays: a block without a seed prints the same on every letter. Give every block that should change a whole-number seed: `seed` on the seeded blocks; `mix`, `bank` or `holeSeed` on a text or shape; `bank` on a table.
* Numbers the teacher typed into stones or fields (`typed`) and operators typed onto a Pfeilbild's arrows (`typedOps`) are dropped in B to D.

If a variant cannot fill a maths block, the dialog names the block and its page and asks for a new roll, looser limits or fewer variants. Then give that block a new seed with `update_block`, loosen its limits, or tell the teacher to print fewer variants.

## Locked blocks

A block with `locked: true` belongs to the teacher. The tools refuse to move, change or delete it ([the text](tools/errors-and-limits.md)). Leave it where it is. Work around it on the rest of the sheet.

See [text](blocks/text.md) and [selbstkontrolle](blocks/selbstkontrolle.md) for the blocks that carry answers and seeds.
