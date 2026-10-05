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
| Features are hard to find | One toolbar, a block panel, nothing hidden in menus |
| Keep: fonts, Lineaturen, numbering, symbols, fields that move freely | All in v0 |
| Too few pictures for Sachunterricht | v1, AI pictures. v0 takes uploads |

## The test

v0 is done when she rebuilds one real sheet from her week in Blattwerk, on the iPad, prints it, and says she would do the next one there too.

## Scope

### 1. Canvas

- A4 portrait pages, measured in mm. A sheet has one or more pages.
- Blocks can be dragged, resized and deleted, and kept in place with a lock.
- Snap to page margins, the page centre and other blocks' edges and centres, with guide lines shown while dragging.
- Multi-select by tap-and-hold then tap (iPad), shift-click or a drag box (laptop).
- Copy, paste, duplicate, align (left, centre, right, top, middle, bottom), distribute, bring forward and send back.
- Undo and redo.
- Zoom to fit page width, pinch zoom on the iPad.
- Touch first: handles at least 44 px, no hover-only controls.

### 2. Blocks

| Block | Settings |
|---|---|
| Text | font, size, bold, italic, underline, colour, alignment, line spacing |
| Heading | text block preset |
| Lineatur | type (Lineatur 1 to 4, Karo 5 mm, Karo 7 mm, plain lines), row count, colour |
| Maths exercises | the generator below, number of columns, numbering style |
| Image | upload from the device, crop, keep ratio |
| Shape | rectangle, rounded box, circle, line, arrow; fill and border |
| Symbol | a searchable symbol set (pencil, scissors, glue, partner work, ear, eye, stars) |
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
  - Written method (schriftlich): stacked on Karo, with a row for carries
- **Count**, and no repeated exercise in one block.
- **Reroll**: new numbers, same settings. A seed is stored, so a sheet reopens with the same numbers.
- **Answer key**: generated with the exercises.

If the limits leave no valid exercise, the panel says so and names the limit to loosen.

### 5. Templates

Start points, not locked layouts. Every block in a template can move.

- **Arbeitsblatt**: name header, title, two empty areas.
- **Klassenarbeit**: name header with points total on each page, numbered task blocks with points boxes, three pages.
- **Beschriftungsblatt**: title, a large image area, label lines with arrows.

Any sheet can be saved as a new template.

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
- iOS keeps a home-screen app's storage apart from Safari's, so login lives in the URL the app opens with (see Access).

### 9. Access

One user for now. A secret link, as for the interview form, opens the app. The manifest is served per link, so the installed app starts at that link and needs no login. Any other path is a 404.

## Not in v0

- AI pictures for Sachunterricht (v1, the place she says AI already works)
- AI layout: it is what failed her with Gemini
- Deutsch generators (Silbenbögen, Lückentexte, word lists)
- Sharing between teachers, accounts, payment
- Offline editing
- Handwriting with the Apple Pencil

## Architecture

| Part | Choice | Why |
|---|---|---|
| Frontend | TypeScript, React, Vite | The editor is most of the work, and the best canvas libraries for it target React |
| Canvas | Each block is an HTML element placed in mm on an A4 page; drag, resize, snap and multi-select from `moveable` and `selecto` | Sharp text in the PDF, native text editing on the iPad, the same markup renders the PDF |
| Backend | FastAPI, the app already in this repo | |
| Storage | SQLite file on the data volume; a sheet is one JSON document | One user, no server to run |
| Uploads | Files on the data volume, served through the app | |
| PDF | Playwright with Chromium in the container, prints the sheet's render URL | The screen and the PDF use the same markup |
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
          "props": { "operation": "+", "max": 100, "carry": "none", "format": "row",
                     "count": 12, "columns": 3, "seed": 4182, "places": { "…": "…" } } }
      ]
    }
  ]
}
```

Positions and sizes in mm from the page's top-left corner.

## Milestones

1. **Canvas**: one page, text and shape blocks, drag, resize, snap, multi-select, undo. Runs on the iPad.
2. **Sheets**: save, list, reopen on another device. Secret-link access. PWA install.
3. **School blocks**: Lineatur, fonts, name header, points box, symbols, images, numbering.
4. **Maths generator**: all settings, the three formats, answer key.
5. **Export and templates**: PDF and answer-key PDF, the three templates.
6. **The test**: she builds one real sheet. Fix what she trips on.

## Open questions

- Which symbol set: OpenMoji (CC BY-SA) or a smaller set drawn for this?
- Does she want the written method for × and ÷ in v0, or only for + and −?
