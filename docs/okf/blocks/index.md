# Blocks

Each page lists one block type's props, generated from the sheet's schema by `frontend/okf.mjs`. Do not edit them by hand: run `mise run schema`.

* [text](text.md): The text box's words and look.

* [shape](shape.md): The shape's form, fill and border, and the text it may hold: every field of a text block may stand here too.

* [ruling](ruling.md): The Lineatur's kind and colour, and the words it may show on its rows.

* [name](name.md): The line the pupil writes their name (and date, class) on.

* [points](points.md): A box the teacher writes the points scored in, beside the most there are.

* [symbol](symbol.md): Which symbol (a pictogram such as a pencil or scissors) the block shows, scaled to the box.

* [image](image.md): Which uploaded picture the block shows, and how it is cropped.

* [maths](maths.md): The maths block's limits, layout and exercises.

* [table](table.md): The table's text, layout and lines.

* [suchsel](suchsel.md): The word search's settings: the grid, the words and how they run.

* [zahlenmauer](zahlenmauer.md): The wall block's settings: the stones, the walls and the numbers shown.

* [rechendreieck](rechendreieck.md): The calculation triangles (Rechendreiecke) and which of their fields are given.

* [zahlenhaus](zahlenhaus.md): The number houses (Zahlenhäuser): a roof number and floors of two boxes that add up to it, and which boxes are given.

* [zahlenkette](zahlenkette.md): The number chains (Zahlenketten): rings in a row, each step adding or taking away the same number, and which rings are given.

* [pfeilbild](pfeilbild.md): The arrow pictures (Pfeilbilder): boxes joined by arrows, each arrow labelled with an operator, and which boxes and operators are given.

* [operatorfeld](operatorfeld.md): The operator fields (Operatorfelder): number boxes joined by operators, in a ring or around a centre, and which numbers and operators are given.

* [rechenrad](rechenrad.md): The calculation wheels (Rechenräder): a centre with an operator and a number, and rings of segments where each ring's number worked with the centre gives the next ring's, and which ring or boxes are empty.

* [rechentabelle](rechentabelle.md): The calculation tables (Plus-, Minus-, Mal- and Geteilt-Tabellen): row values down the left, column values along the top, the operator in the corner, and each result cell the row value worked with the column value; which values and cells are given.

* [magischesquadrat](magischesquadrat.md): The magic squares (Magische Quadrate): 3×3 or 5×5 squares where every row, column and both diagonals have the same sum, the Zielzahl; which cells are given, and optionally the Zielzahl above.

* [zahlenstrahl](zahlenstrahl.md): The number line (Zahlenstrahl): its range, ticks and the tasks on it.

* [hunderterfeld](hunderterfeld.md): The hundred square (Hunderterfeld or Hundertertafel) and what the pupil fills in.

* [uhr](uhr.md): The clock faces, their times and the task: read the time or draw the hands.

* [selbstkontrolle](selbstkontrolle.md): The self-check (Selbstkontrolle): a key that tells the pupil whether the answers of the linked blocks are right.
