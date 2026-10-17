---
type: Explanation
title: Versions and the 409 rule
description: How sheet versions work, what a stale write answers, and what to do before you write again.
tags: [versions, conflicts, editor, tools]
covers: []
generated: { by: "human:pgoell", at: 2026-10-17T17:00:00Z }
---

# Versions and the 409 rule

Every sheet has a `version`. `get_sheet` gives it. Every write takes the version you have and answers the new one. Write with the newest version you hold.

Only a write of the doc moves the version on. `rename_sheet` changes the title and leaves the version as it is.

## The fine tools

`add_block`, `update_block`, `move_block`, `delete_block`, `add_page`, `set_page` and `set_words` read the sheet first. If its version is not the one you passed, they write nothing and say so, with both versions ([the text](tools/errors-and-limits.md)).

## replace_doc

`replace_doc` takes the whole doc and the version that `get_sheet` gave. On the same refusal it tries once more with the new version. It does that only when you passed the version of this session's last read or write of the sheet and the doc on the server is still that one: the version moved, the content did not. Otherwise it gives the same refusal and writes nothing.

## What to do

Call `get_sheet`. Make your change on the new doc. Write it with the new version.

Never write an old doc back over the teacher's change. The old doc drops her edit.

## Why it happens

The editor saves itself. The teacher has no save button to press: the editor says "Speichern musst du nie". So she can change a sheet while you work on it. The version can move between your `get_sheet` and your write, at any time.

See the [errors and limits](tools/errors-and-limits.md) of each tool for its exact refusal text.
