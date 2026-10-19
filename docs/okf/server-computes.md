---
type: Explanation
title: What the server computes
description: What the server computes for maths and other seeded blocks, and when a seed gives the same tasks.
tags: [maths, seed, exercises, server]
covers: [maths, suchsel, zahlenmauer, zahlenhaus, zahlenkette, pfeilbild, operatorfeld, rechenrad, rechentabelle, rechendreieck, zahlenstrahl, hunderterfeld, uhr, selbstkontrolle]
generated: { by: "human:pgoell", at: 2026-10-19T13:00:00Z }
---

# What the server computes

Some blocks draw their content from a `seed`. Maths blocks get their exercises from the server. The other seeded blocks draw theirs in the browser. In both cases you send the limits and the seed, not the content.

## Maths exercises

A maths block takes limits: `ops`, `max`, `count`, `format`, `seed` and the rest, on the [maths](blocks/maths.md) page. The server draws the exercises from them. `columns` and `size` only lay the tasks out: with the limits they set the block's height, and a change to them draws no new tasks.

* `add_block`: leave `exercises` out of `props`. Props may be partial. The answer gives the block as stored, with its exercises and its real `h`. Place the next block from that answer.
* `replace_doc`: a doc must carry every maths field, so pass `"exercises": []` and `"loosen": null`. `replace_doc` fills an empty list from the server. A block that already has exercises keeps them.
* `update_block` with a new limit: the server draws new exercises from the block's seed. Pass a new `seed` for new tasks. The editor's panel does the same.
* Same seed and same limits give the same tasks. A new seed gives new tasks.
* `loosen` says which limit is in the way when fewer tasks came than you asked for. It is `null` when the count is met. Then loosen that limit, or ask for fewer exercises.
* `update_block` refuses a change whose height would reach past the page's foot ([the text](tools/errors-and-limits.md)). Move the block up or ask for fewer exercises, then write again. `add_block` and `replace_doc` only warn that the block leaves the printable area.

## Other seeded blocks

These blocks draw their content in the browser from their seed: [suchsel](blocks/suchsel.md), [zahlenmauer](blocks/zahlenmauer.md), [zahlenhaus](blocks/zahlenhaus.md), [zahlenkette](blocks/zahlenkette.md), [pfeilbild](blocks/pfeilbild.md), [operatorfeld](blocks/operatorfeld.md), [rechenrad](blocks/rechenrad.md), [rechentabelle](blocks/rechentabelle.md), [rechendreieck](blocks/rechendreieck.md), [zahlenstrahl](blocks/zahlenstrahl.md), [hunderterfeld](blocks/hunderterfeld.md) and [uhr](blocks/uhr.md). The same seed gives the same content. Change the seed to change the content.

## Selbstkontrolle

A [selbstkontrolle](blocks/selbstkontrolle.md) reads the results of the maths blocks in its `links`. `links` holds the ids of those maths blocks. Link it to maths blocks on the same sheet.
