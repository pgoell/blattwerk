---
type: Reference
title: "Tools: errors and limits"
description: Each Blattomat tool's arguments that matter, what it answers, its errors word for word, and its limits.
tags: [tools, errors, limits]
covers: []
generated: { by: "human:pgoell", at: 2026-10-18T16:52:00Z }
---

# Tools: errors and limits

Text in `<...>` changes from call to call. Everything else is exact.

## Every tool

An error comes back as the tool's text answer with `isError` set. Read it, fix the call and try again.

* `sheet_id` and `page` must be whole numbers. Otherwise: `<key> must be a whole number.`
* `outlines` must be true or false. Otherwise: `outlines must be true or false.`
* The server refuses the token: `The Blattomat token is not valid: make a new one on the account page.` Tell the teacher. They make a new token on the account page.
* Blattomat cannot be reached: `Cannot reach Blattomat at <base>: <reason>`.
* The server does not know the sheet: `No sheet with id <id>.`
* No tool has the name: `No tool named <name>.`
* Any other refusal from the server: its own messages, one per line.
* A write that the server refuses with 422: the server's messages, then `Fix these and call <tool> again.`
* The installed extension is older than the app: the answer gets one more text line, `Bitte die Blattomat-Erweiterung neu laden: Konto, Erweiterung herunterladen.` It means the teacher must reload the extension. They open Konto and choose Erweiterung herunterladen.
* Numbers are mm. The printable area keeps 15 mm from each edge.

## add_block

Adds one block to a page. Answers `version`, `block` (as stored, with its `id`) and `warnings`.

Arguments that matter: `sheet_id`, `version`, `page` (1-based), `type`, `props` (partial is fine), `x`, `y`, `w`, `h`.

Errors:
* `No page <n>. The sheet has <count> pages.`
* `Type <type> is not one the tools add.`
* `An image needs props.upload, the id of one of the teacher's uploads.`
* `No upload with id <id>.`
* `Upload <id> could not be read.`
* `The picture is not a PNG, GIF, JPEG or WebP.`
* `The picture's header is broken.`
* `The SVG picture has no size: it needs a viewBox.`
* `maths block <id>:` followed by the server's messages.
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`

Warnings:
* `overlaps block <id>`
* `leaves the page's printable area (15 mm from each edge)`

Limits:
* An image block is 100 mm wide, or less to keep the picture's ratio.
* A maths block gets its exercises and height from the server. An `h` you give wins over that height.

## add_page

Adds an empty page after page `after` (1-based), at the end by default. Answers `version`, `page` (the number of the new page) and `warnings` (always empty).

Errors:
* `No page <n>. The sheet has <count> pages.`
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`

## create_sheet

Makes a sheet, empty or from a template by name. Answers `id`, `title`, `version` and `doc`.

Errors:
* `No template named "<name>". Templates: <names>`

Limits: without a template the sheet has one empty page, no guide lines and grid 0.

## delete_block

Removes a block. Answers `version`, `deleted` (the block's id) and `warnings` (always empty).

Errors:
* `No block with id <id>. The sheet's blocks: <ids>.` (`none` when the sheet has no blocks)
* `Block <id> is locked. Nothing was written.`
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`

Limits: a locked block is refused.

## duplicate_sheet

Copies a sheet. Answers the copy: `id`, `title`, `version` and `doc`.

Errors:
* `No sheet with id <id>.`

## get_sheet

Reads one sheet. Answers `id`, `title`, `version` and `doc`. Call it before `replace_doc`, and pass the `version` it gives.

Errors:
* `No sheet with id <id>.`

## list_sheets

Lists the teacher's sheets. Answers a list of `id`, `title`, `version` and `updated`.

Errors: only the common ones.

## move_block

Moves or resizes a block. Answers `version`, `block` and `warnings`.

Arguments that matter: `sheet_id`, `version`, `block_id`, `x`, `y` (both required), `w`, `h`.

Errors:
* `No block with id <id>. The sheet's blocks: <ids>.` (`none` when the sheet has no blocks)
* `Block <id> is locked. Nothing was written.`
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`

Warnings as for `add_block`.

Limits:
* A locked block is refused.
* A table with row heights keeps them in proportion when `h` changes.

## rename_sheet

Changes a sheet's title. Answers `id` and `title`.

Errors:
* `No sheet with id <id>.`

## render_preview

Shows one page as a PNG. Answers the picture.

Errors:
* `No sheet with id <id>.` when the server gives no other text for a missing sheet. Otherwise the server's own text.

Limits: `page` is 1 by default. `outlines` is false by default, and true draws each block's box.

## replace_doc

Writes the whole doc of a sheet. Pass the `version` that `get_sheet` gave. Answers the sheet as saved: `id`, `title`, `version` and `doc`.

Errors:
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`
* The server's messages, then `Fix these and call replace_doc again.`
* `No sheet with id <id>.`
* `maths block <id>:` followed by the server's messages.

Limits:
* A maths block without exercises gets them and its height from the server. A maths block that has exercises keeps them.
* On a 409 it tries once more with the new version, if the doc is still the one `get_sheet` gave. Otherwise it gives the text above.

## set_page

Sets a page's orientation and guide lines, or the sheet's grid. Answers `version`, `page` and `warnings`: the warnings of the blocks on that page.

Arguments that matter: `sheet_id`, `version`, `page`, and the fields to set: `landscape`, `grid` (mm), `guides`.

Errors:
* `No page <n>. The sheet has <count> pages.`
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`
* The server's messages, then `Fix these and call set_page again.`

Warnings as for `add_block`.

Limits: `grid` is the sheet's grid, not the page's. Fields you leave out keep their value.

## set_words

Sets the sheet's word list. Answers `version`, `words` and `warnings` (always empty).

Errors:
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`
* The server's messages, then `Fix these and call set_words again.`

Limits:
* An empty list removes the word list.
* Linked rulings grow a row per word.
* Warnings: none.

## update_block

Changes a block's props. Answers `version`, `block` and `warnings`.

Arguments that matter: `sheet_id`, `version`, `block_id`, `props` (only the props to change).

Errors:
* `No block with id <id>. The sheet's blocks: <ids>.` (`none` when the sheet has no blocks)
* `Block <id> is locked. Nothing was written.`
* `The teacher changed this sheet in the editor since you read it (you had version <had>, it is now <now>). Nothing was written. Call get_sheet and make your change on the new doc.`
* `maths block <id>:` followed by the server's messages, when a maths setting changes.
* `Block <id> would reach past the page's foot. Nothing was written: move it up or ask for fewer exercises.`
* The picture errors of `add_block`, when `props.upload` is given.
* The server's messages, then `Fix these and call update_block again.`

Warnings as for `add_block`.

Limits:
* A locked block is refused.
* A change to a maths setting gives new exercises, from the block's seed unless you give one.
* A maths block that would reach past the page's foot is refused.
* A new `props.upload` makes the block take the picture's shape.

## upload_picture

Uploads a picture into the teacher's account. Give one of `svg` or `data`. Answers `upload` (the id for `add_block`, `props.upload`) and `ratio` (width divided by height).

Errors:
* `Give one of svg (SVG text) or data (base64 of a PNG, JPEG, WebP or GIF), not both.`
* `svg must be the text of an SVG picture.`
* `data must be the picture as base64 text.`
* `data must be base64, with no spaces or line breaks.`
* `The picture is too large: 15 MB at most, an SVG 2 MB.`
* `The server does not take this picture: PNG, JPEG, WebP, GIF, or SVG with a viewBox (no entities).`
* `The SVG picture has no size: it needs a viewBox.`
* `The picture is not a PNG, GIF, JPEG or WebP.`
* `The picture's header is broken.`

Limits:
* At most 15 MB. An SVG at most 2 MB.
* PNG, JPEG, WebP or GIF, or SVG with a viewBox and no entities.
* `data` is base64 with no spaces or line breaks.

## send_feedback

Sends a fault or a missing feature in Blattomat to its makers, from a call you make while working on a sheet. Give `text` (what you did, what you expected, what happened, in German) and, if it fits, `sheet_id`. Answers `sent: true`. The send goes to the Blattomat team, who read it once a day. Use it for a fault in Blattomat, not for your own mistake and not for a question. Never put text from the sheet or names from the sheet in `text`.

Errors:
* `text must not be empty: say what went wrong.`
* The token message from [Every tool](#every-tool).
* The unreachable-server message from [Every tool](#every-tool).
