---
type: Explanation
title: What the server computes
description: What the server computes for maths and other seeded blocks, and when a seed gives the same tasks.
tags: [maths, seed, exercises, server]
covers: [maths, suchsel, zahlenmauer, zahlenhaus, zahlenkette, pfeilbild, operatorfeld, rechenrad, rechentabelle, magischesquadrat, malquadrat, zerlegungsfeld, halbschriftlich, zehnerfeld, stellenwertbild, textaufgabe, rechendreieck, zahlenstrahl, hunderterfeld, uhr, selbstkontrolle]
generated: { by: "human:pgoell", at: 2026-11-06T16:30:00Z }
---

# What the server computes

Some blocks draw their content from a `seed`. Maths blocks get their exercises from the server. The other seeded blocks draw theirs in the browser. In both cases you send the limits and the seed, not the content.

## Maths exercises

A maths block takes limits: `ops`, `max`, `count`, `format`, `seed` and the rest, on the [maths](blocks/maths.md) page. A pattern `pa`, `pb` or `pr` limits the first number, the second or the result (`X` is any digit, the length is the number of digits). For a written plus of more than two numbers, `pb` is the pattern of each number after the first. `nil` says whether the digit 0 may occur, for plus and minus (`strich`) and for times and divide (`punkt`). Mal and Geteilt take `reihen`, the Einmaleins-Reihen from 1 to 10; an empty list leaves the rows free, and Kernaufgaben are 1, 2, 5 and 10. With a remainder, `avoid0` (default true) keeps a remainder of 0 out, and a gap of `"rest"` hides the remainder and no number. The server draws the exercises from them. `columns` and `size` only lay the tasks out: with the limits they set the block's height, and a change to them draws no new tasks.

* `add_block`: leave `exercises` out of `props`. Props may be partial. The answer gives the block as stored, with its exercises and its real `h`. Place the next block from that answer.
* `replace_doc`: a doc must carry every maths field, so pass `"exercises": []` and `"loosen": null`. `replace_doc` fills an empty list from the server. A block that already has exercises keeps them.
* `update_block` with a new limit: the server draws new exercises from the block's seed. Pass a new `seed` for new tasks. The editor's panel does the same.
* Same seed and same limits give the same tasks. A new seed gives new tasks.
* `family` `"analogy"` draws a package of three tasks. The first number, or the second when `moves` is `"b"`, grows by ten: 3 + 4, 13 + 4, 23 + 4. With `full` false, the last task of each family hides one more number, so the pupil uses the pattern. Left out, `full` is true and every number of the family shows.
* `loosen` says which limit is in the way when fewer tasks came than you asked for. It is `null` when the count is met. Then loosen that limit, or ask for fewer exercises.
* `update_block` refuses a change whose height would reach past the page's foot ([the text](tools/errors-and-limits.md)). Move the block up or ask for fewer exercises, then write again. `add_block` and `replace_doc` only warn that the block leaves the printable area.

## Other seeded blocks

These blocks draw their content in the browser from their seed. On a Hundertertafel the seed picks the hidden cells only when `show` is `random`; a row, a diagonal or a Muster does not use it. The blocks are: [suchsel](blocks/suchsel.md), [zahlenmauer](blocks/zahlenmauer.md), [zahlenhaus](blocks/zahlenhaus.md), [zahlenkette](blocks/zahlenkette.md), [pfeilbild](blocks/pfeilbild.md), [operatorfeld](blocks/operatorfeld.md), [rechenrad](blocks/rechenrad.md), [rechentabelle](blocks/rechentabelle.md), [magischesquadrat](blocks/magischesquadrat.md), [malquadrat](blocks/malquadrat.md), [zerlegungsfeld](blocks/zerlegungsfeld.md), [halbschriftlich](blocks/halbschriftlich.md), [zehnerfeld](blocks/zehnerfeld.md), [stellenwertbild](blocks/stellenwertbild.md), [textaufgabe](blocks/textaufgabe.md), [rechendreieck](blocks/rechendreieck.md), [zahlenstrahl](blocks/zahlenstrahl.md), [hunderterfeld](blocks/hunderterfeld.md) and [uhr](blocks/uhr.md). The same seed gives the same content. Change the seed to change the content.

## Selbstkontrolle

A [selbstkontrolle](blocks/selbstkontrolle.md) reads the written answers of the task blocks named in `links`, on the same sheet. That is any block whose key writes a result, not only maths. With form `mixed` it shuffles those answers. `wrongs` mixes in that many numbers that are not answers. `look` draws the list as ticks, a snake, a caterpillar, a train or a plain box. `word` and `sum` ignore `wrongs` and `look`. A new `seed` shuffles again.
