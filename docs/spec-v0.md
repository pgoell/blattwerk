# Blattwerk v0

A worksheet editor for Grundschule teachers: an A4 canvas like PowerPoint, with blocks made for school sheets, a maths generator with exact limits, and a PDF that matches the screen. It runs in the browser and installs on an iPad from Safari.

## Who it is for

One teacher first: Grundschule, Mathe, Deutsch and Sachunterricht, a sheet a week plus Klassenarbeiten. A laptop at home, an iPad at school. Today she uses Worksheet Crafter, which the school pays for.

What she told us (interview, 2026-10-05):

| She said | v0 answer |
|---|---|
| The generators are too rough. Maths needs limits per place value and Zahlenraum | The maths generator below |
| Worksheet Crafter does not run on the iPad | Web app, installed as a PWA |
| Copying several fields is clumsy | Multi-select, copy, paste, duplicate |
| Features are hard to find | A ribbon with three tabs (Start, Ansicht, Vorlagen) and a format panel for what is selected |
| Keep: fonts, Lineaturen, numbering, symbols, fields that move freely | All in v0 |
| Too few pictures for Sachunterricht | v1, AI pictures. v0 takes uploads |

## The test

v0 is done when she rebuilds one real sheet from her week in Blattwerk, on the iPad, prints it, and says she would do the next one there too.

## Scope

### 1. Canvas

- A4 pages, measured in mm. A sheet has one or more pages. The sheet is portrait or landscape, and a page can have a format of its own.
- Blocks can be dragged, resized and deleted, and kept in place with a lock.
- Resize handles sit on the corners and, as in PowerPoint, on the edges, each of which moves alone. A picture or a symbol keeps its shape and has corner handles only.
- Snap to page margins, the page centre and other blocks' edges and centres, with guide lines shown while dragging.
- A grid of 5, 10 or 20 mm can be shown on the page; blocks snap to it.
- Own guide lines: added from the Ansicht tab, moved by their tab at the page's edge, removed by dragging them off the page.
- Keys during a drag work as in PowerPoint. Shift keeps a block's shape on resize, keeps a move level or upright, and turns a line in steps of 45 degrees. Ctrl (Option on Apple) resizes about the centre and leaves a copy behind a move. Alt (Command on Apple) switches snapping off.
- Arrow keys move the selection by 1 mm, or by one grid cell when the page shows a grid, and by 10 mm with Shift. A run of presses is one undo step.
- Multi-select by tap-and-hold then tap (iPad), shift-click or a drag box (laptop).
- Copy, paste, duplicate, align (left, centre, right, top, middle, bottom), distribute, bring forward and send back.
- Undo and redo.
- Zoom to fit page width, pinch zoom on the iPad.
- Touch first: no hover-only controls.

### 2. Blocks

| Block | Settings |
|---|---|
| Text | font, size, bold, italic, underline, colour, alignment, line spacing |
| Heading | text block preset |
| Lineatur | type (Lineatur 1 to 4, Karo 5 mm, Karo 7 mm, plain lines), row count, colour |
| Maths exercises | the generator below, number of columns, numbering style |
| Image | upload from the device, crop, keep ratio |
| Shape | rectangle, rounded box, circle, line, arrow; fill and border |
| Symbol | OpenMoji, searchable by German and English name (pencil, scissors, glue, partner work, ear, eye, stars) |
| Name header | Name, Datum, Klasse fields with lines |
| Points box | "/ n Punkte" box for Klassenarbeiten |

Numbering: 1., a), (1), or a symbol, added to any block.

### 3. Fonts

The four German school scripts from Google Fonts, all under the SIL Open Font License:

- Playwrite DE Grund (Grundschrift)
- Playwrite DE VA (Vereinfachte Ausgangsschrift)
- Playwrite DE SAS (Schulausgangsschrift)
- Playwrite DE LA (Lateinische Ausgangsschrift)

Plus one clear print font for headings. Fonts are self-hosted, so the PWA works without Google and the PDF matches the screen.

### Symbols

OpenMoji (hfg-gmuend/openmoji), CC BY-SA 4.0, license read from the repo's `LICENSE.txt`. Self-hosted SVGs. Attribution goes in the app's About page and in `NOTICE`. Symbols are used unchanged; any symbol we edit stays CC BY-SA.

### 4. Maths generator

Generates exercises into a maths block. Every setting is visible in one panel.

- **Operation**: +, −, ×, ÷, or mixed.
- **Zahlenraum**: 10, 20, 100, 1,000, 1,000,000, or a free maximum.
- **Per operand, per place value**: a range of digits allowed (for example units 5 to 9, tens 1 to 4, hundreds 0).
- **Carrying and borrowing** (Übertrag): none, required, or either.
- **Result**: within the Zahlenraum, never negative; division with or without remainder.
- **Format**:
  - Row: `34 + 25 = ___`
  - Gap: `34 + ___ = 59`
  - Written method (schriftlich) for all four operations, on Karo: stacked addition and subtraction with a carry row, long multiplication with partial products, long division with the working shown
- **Count**, and no repeated exercise in one block.
- **Reroll**: new numbers, same settings. A seed is stored, so a sheet reopens with the same numbers.
- **Answer key**: generated with the exercises.

If the limits leave no valid exercise, the panel says so and names the limit to loosen.

### 5. Templates

Start points, not locked layouts. Every block in a template can move.

- **Arbeitsblatt**: name header, title, two empty areas.
- **Klassenarbeit**: name header with points total on each page, numbered task blocks with points boxes, three pages.
- **Beschriftungsblatt**: title, a large image area, label lines with arrows.

Any sheet can be saved as a new template. A template keeps the blocks, the guide lines and the grid.

### 6. Export

- **PDF** rendered on the server by headless Chromium from the same page markup, so it matches the screen on any device. A4, print margins respected.
- **Answer key PDF**: the same sheet with the solutions filled in, marked "Lösungen".

### 7. Sheets and storage

- Sheets are saved on the server, automatically, every few seconds after a change.
- A list of sheets with title, date and a thumbnail; rename, duplicate, delete.
- The same sheet opens on the iPad and on the laptop.

### 8. PWA

- Web app manifest with name, icon and `display: standalone`.
- Installed from Safari: Share, then "Zum Home-Bildschirm".
- iOS keeps a home-screen app's storage apart from Safari's, so she logs in once inside the installed app; a login in Safari does not carry over.

### 9. Accounts

Every teacher has their own space from the start.

- **Login** with email and password. Passwords hashed with Argon2. A session cookie, `HttpOnly`, `Secure`, `SameSite=Lax`, valid for 90 days so the iPad app rarely asks again.
- **Sign-up by invite only.** An admin makes an invite link; the link lets one person create an account. No open registration in v0.
- **Own space.** Sheets, uploads and saved templates belong to one user. Every query is scoped by user id, and a request for someone else's item gets a 404, not a 403. A test checks this for every endpoint.
- **Built-in templates** are shared by all users; templates a user saves are theirs alone.
- **Password reset** without email in v0: an admin makes a one-time reset link and sends it by hand.
- **Admin** is a flag on the user. A small admin page lists users and makes invite and reset links. No other admin powers.
- **Delete account** removes the user, their sheets and their uploads.
- Logins are rate-limited per email and per IP.

## Not in v0

- AI pictures for Sachunterricht (v1, the place she says AI already works)
- AI layout: it is what failed her with Gemini
- Deutsch generators (Silbenbögen, Lückentexte, word lists)
- Sharing between teachers, payment
- Email (sign-up and reset links go out by hand)
- Offline editing
- Handwriting with the Apple Pencil

## Architecture

| Part | Choice | Why |
|---|---|---|
| Frontend | TypeScript, React, Vite | The editor is most of the work, and the best canvas libraries for it target React |
| Canvas | Each block is an HTML element placed in mm on an A4 page; drag, resize, snap and multi-select from `moveable` and `selecto` | Sharp text in the PDF, native text editing on the iPad, the same markup renders the PDF |
| Backend | FastAPI, the app already in this repo | |
| Storage | SQLite file on the data volume, tables for users, sessions, invites, sheets, templates, uploads; a sheet is one JSON document | A few users, no database server to run; Postgres on the box if it outgrows that |
| Uploads | Files on the data volume under a folder per user, served through the app after an owner check | |
| PDF | Playwright with Chromium in the container, prints the sheet's render URL with a short-lived signed token for that one sheet | The screen and the PDF use the same markup |
| Generator | Pure Python module, tested on its own | The part with the most rules; property tests check every limit holds |

### Sheet document

```json
{
  "id": "…",
  "title": "Plusaufgaben bis 100",
  "pages": [
    {
      "blocks": [
        { "id": "…", "type": "maths", "x": 15, "y": 60, "w": 180, "h": 90, "z": 2,
          "locked": false,
          "props": { "ops": ["+"], "max": 100, "carry": "none", "rest": false, "format": "row",
                     "count": 12, "columns": 3, "size": 14, "seed": 4182,
                     "a": [[0, 9], [1, 4], [0, 0]], "b": [[5, 9], [0, 9], [0, 0]],
                     "exercises": [{ "op": "+", "a": 34, "b": 25, "result": 59, "rest": 0 }],
                     "loosen": null } }
      ]
    }
  ]
}
```

A maths block keeps its limits and the exercises the server made from them, so a sheet draws without the generator. `a` and `b` hold the lowest and highest digit of each place, units first. `ops` holds one operation or several to mix. `loosen` is null, or with fewer exercises than asked for the limits that stand in the way.

Positions and sizes in mm from the page's top-left corner. A line or arrow shape runs from the corner of its box named in `props.from` (`nw`, `ne`, `sw` or `se`, `nw` when absent) to the opposite corner; a level line has `h` 0.

## Milestones

1. **Canvas**: one page, text and shape blocks, drag, resize, snap, multi-select, undo. Runs on the iPad.
2. **Accounts and sheets**: invite, sign-up, login, admin page; save, list, reopen on another device, scoped per user. PWA install.
3. **School blocks**: Lineatur, fonts, name header, points box, symbols, images, numbering.
4. **Maths generator**: all settings, the three formats including the written method for all four operations, answer key.
5. **Export and templates**: PDF and answer-key PDF, the three templates.
6. **The test**: she builds one real sheet. Fix what she trips on.

## Open questions

- Other teachers' data on the server needs an Impressum and a Datenschutzerklärung before the first invite outside the family.
- Backups: the hourly archive of the data volume (`server-infra/backup/blattwerk-backup.sh`) stays on the same disk. It needs an off-site copy.
