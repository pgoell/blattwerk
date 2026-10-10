# Teacher run

You stand in for a primary school teacher who uses Blattomat, a worksheet editor with a German interface. You build five fixed worksheets, export each as a PDF, read each PDF beside the screen, and then spend 15 minutes trying to break what the last five pull requests changed. You open an issue for each fault, 8 at most.

The bar is a teacher's eyes. A fault is anything a teacher would trip over: a click that does nothing, a print that differs from the screen, lost work, a word cut off, a step that PowerPoint or Word make easy and this app makes hard. You have never seen the code and you must not look at it.

Time: about 45 minutes in all. The five sheets take about 25, the pull requests 15, the rest is start, issues and clean up. Run `date` at the start and before each part, and keep to the boxes. A sheet that takes more than 7 minutes is a finding: note it and go on.

## Rules

Allowed:

- The `chrome-devtools` tools `new_page`, `list_pages`, `navigate_page`, `click`, `fill`, `type_text`, `press_key`, `hover`, `drag`, `upload_file`, `handle_dialog`, `take_snapshot`, `take_screenshot`, `wait_for`, `resize_page`, `emulate`, `close_page`. Real clicks and keys only.
- The shell commands this brief spells out, `date`, and `ls`, `rm` and `pdftoppm` on your own files in `/tmp/teacher-run` and on the `TR*.pdf` files in `~/Downloads`.
- `gh pr list`, `gh issue list` and `gh issue create` as written below. Of a pull request you read the title and the body only.

Forbidden:

- `evaluate_script` and any other script in the page.
- `curl` or any other direct call to `/api`.
- Any docker command.
- The page `/admin`.
- Anything under `~/.local/share`.
- Reading any file under `/home/pascal/Code/blattwerk`: source, tests, other docs.
- `gh pr diff` and `gh pr view --json files`.
- The live site `blattwerk.pgoell.com`.

The browser is shared with other sessions. Open your own page with `new_page` and act on that page only. Never select, navigate or close a page you did not open. If a call says "Could not connect to Chrome" or "browser is already running", do not kill or restart Chrome: stop the stage (see "Clean up") and end your report with the line `BLOCKED teacher-run: <reason>`. Do the same if the stage does not start or the sign-in fails twice.

## Start the stage

1. Make your folder and clear old exports:

   ```sh
   rm -rf /tmp/teacher-run && mkdir /tmp/teacher-run && rm -f ~/Downloads/TR*.pdf
   ```

2. Start a fresh stage, also if one seems to run already:

   ```sh
   mise -C /home/pascal/Code/blattwerk run stage:up
   ```

   It starts a copy of the live app on a copy of the live data. Its last three lines are:

   ```
   URL: http://127.0.0.1:8220
   E-Mail: teacher-run@stage.invalid
   Passwort: <a fresh password each time>
   ```

   Only this machine reaches the stage. The test teacher is a new account with no sheets and no templates of its own, and it is no admin.

## Sign in

1. `new_page` with `http://127.0.0.1:8220`, then `resize_page` to 1280 by 1024. Signed out, every path shows the form `Anmelden`.
2. Fill `E-Mail` and `Passwort` with the two values the stage printed and click `Anmelden`.
3. You land on `Meine Blätter` with the line "Noch kein Blatt. Leg dein erstes an."

## How the editor works

- `Neues Blatt` on `Meine Blätter` opens an empty sheet in the editor. The logo at the top left leads back to `Meine Blätter`.
- A tour (`Rundgang`) may open on the first sheet. Close it with `Beenden`.
- The window is 1280 px wide. The bar at the top holds the tabs `Start`, `Ansicht` and `Vorlagen`, the field `Titel`, `Rückgängig`, `Wiederholen`, and at the right `Lösungen` and `PDF`. The left panel starts with `Mehrere`, which lets you pick several blocks, and then holds what you can put on the sheet: `Text`, `Überschrift`, `Bild`, `Symbol`, `Tabelle`, `Lineatur`, `Namenszeile`, `Punkte`, `Rechnen`, `Strecke`, shapes, and `Neue Seite`. The right panel shows the settings of the block you picked; the button `Format und Ansicht` shows and hides it. If the bar has no tabs, the button `Seiten und Vorlagen` opens pages and templates, and the right panel has the tabs `Format` and `Ansicht`.
- Many buttons are icons. A screenshot does not show their names; `take_snapshot` does, and so does `hover`. Find a control by its name in the snapshot.
- A new block lands at the top of the page and is picked. Drag it, or move it with the arrow keys, so that the blocks stand below one another in the order of the recipe and none overlaps.
- A new `Text` or `Überschrift` is open for typing. Type, then press Escape. A double click opens a text, a table cell or a Lineatur again.
- The sheet saves by itself. The bar says `Gespeichert` when it has.
- Type each sheet's name into `Titel` before you export: the PDF file takes that name.

## Export and compare

Do this for every sheet.

1. Wait for `Gespeichert`. `take_screenshot` of the editor with the whole page in view (for a sheet of two pages, one per page). Save it as `/tmp/teacher-run/<n>-screen.png`.
2. Click `PDF`. The page stays where it is and the browser saves `~/Downloads/<Titel>.pdf`. Wait until `ls ~/Downloads` shows it. If no file comes within 30 seconds, that is a fault.
3. Turn the PDF into pictures, one per page, and delete the PDF:

   ```sh
   pdftoppm -png -r 60 ~/Downloads/"TR1 Rechnen.pdf" /tmp/teacher-run/1-pdf && rm ~/Downloads/"TR1 Rechnen.pdf"
   ```

   This writes `/tmp/teacher-run/1-pdf-1.png`, and `1-pdf-2.png` for a second page. Change the title and the number for the other sheets.
4. Open the pictures with your Read tool and hold them beside the screenshot. Check, block by block:
   - the same number of pages, in the same order, each upright or on its side as on screen;
   - each block at the same place and of the same size;
   - the same words, with the same line breaks, the same font and size;
   - the same borders, lines and colours;
   - nothing cut off at a block's edge or the page's edge, and nothing missing or added.
5. Write down each difference with the sheet, the block and what differs.

## The five sheets

Build each one on a new sheet from `Meine Blätter`, in this order, with exactly this content. If a step cannot be done as written with clicks and keys, note it as a fault and go on.

### 1. Maths sheet, title `TR1 Rechnen`

1. Click `Namenszeile`.
2. Click `Überschrift`, type `Plus und Minus`.
3. Click `Rechnen`. Twelve plus exercises up to 20 land on the sheet in 3 columns.
4. With the exercises picked, set in the right panel: under `Rechenart` turn `−` on beside `+`; `Zahlenraum` to `bis 100`; `Übertrag` to `Mit`; click `Eine Aufgabe mehr` until it says `16 Aufgaben`; click `Eine Spalte mehr` once, so it says `4 Spalten`.
5. Check on screen: 16 exercises, 4 columns, only plus and minus, no number and no result above 100, no result below 0, each with a carry. The numbers differ from run to run.
6. Export and compare.
7. The answer key: click `Lösungen zeigen` in the bar (it may lie under `Mehr`). The results show on screen. Take a screenshot, then click `Lösungen`, which saves `~/Downloads/TR1 Rechnen Lösungen.pdf`. Turn it into a picture as above. Check that the key holds the same 16 exercises as the sheet, that every result is right (work each one out), and that the plain PDF from step 6 shows no result. Turn `Lösungen zeigen` off again.

### 2. Lineatur writing sheet, title `TR2 Schreiben`

1. Click `Namenszeile`.
2. Click `Überschrift`, type `Schreibe den Satz ab`.
3. Click `Lineatur`. In the right panel set `Art der Lineatur` to `Lineatur 2 (Klasse 2)`, click `Eine Zeile mehr` until it says `8 Zeilen`, and click the `Seitenbreite` of the right panel (the zoom has a button of the same name).
4. Double-click the Lineatur and type `Oma malt im Garten.` Press Escape. Turn `Nachspurtext` on.
5. Check on screen: 8 rows, each with its four lines, the sentence on the first row between the lines, in grey to trace over.
6. Export and compare. Look hard at where the letters sit on the lines.

### 3. Picture with table, title `TR3 Bild und Tabelle`

1. Make the picture, a red and a blue half in a dark frame, 240 by 160:

   ```sh
   python3 -c "import zlib,struct;w,h=240,160;row=lambda y:b'\0'+b''.join((b'\x22\x22\x22' if x<6 or y<6 or x>=w-6 or y>=h-6 else b'\xd0\x30\x30' if x<w//2 else b'\x30\x60\xd0') for x in range(w));c=lambda t,d:struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d));open('/tmp/teacher-run/bild.png','wb').write(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+c(b'IDAT',zlib.compress(b''.join(row(y) for y in range(h))))+c(b'IEND',b''))"
   ```

2. Click `Überschrift`, type `Mein Haustier`.
3. `upload_file` on the button `Bild` with `/tmp/teacher-run/bild.png`. The picture lands on the sheet.
4. Click `Tabelle`. It has 3 rows and 3 columns. In the right panel click `Eine Zeile mehr` once, so it says `4 Zeilen`, and turn `Kopfzeile` on.
5. Double-click a cell to write in it. First row: `Tier`, `Farbe`, `Beine`. Second row: `Hund`, `braun`, `4`. Leave the other rows empty.
6. Check on screen: the picture whole, red left and blue right, the frame on all four sides; the table below it with 4 rows and 3 columns.
7. Export and compare. Look at the picture's frame and at the table's lines and words.

### 4. Two pages, title `TR4 Zwei Seiten`

1. Click `Überschrift`, type `Seite eins`. Click `Text`, type `Lies den Text und male ein Bild dazu.`
2. Click `Neue Seite`. A second, empty page comes and is the one in use.
3. On page 2: click `Überschrift`, type `Seite zwei`. Click `Punkte`.
4. Click the tab `Ansicht`. Under `Format, Raster und Hilfslinien für` pick `Nur diese Seite`, then under `Format` pick `Quer`. Page 2 now lies on its side and page 1 stands upright.
5. Export and compare. The PDF must have two pages: the first upright with `Seite eins`, the second on its side with `Seite zwei` and the points box.

### 5. Copy of a template, title `TR5 Kopie`

Three templates are built in for everyone: `Arbeitsblatt`, `Klassenarbeit`, `Beschriftungsblatt`. A teacher's own templates stand under `Meine Vorlagen`, and only that teacher sees them. A click on a template puts it in place of the whole sheet; `Rückgängig` brings the sheet back. That is how the app is meant to work.

1. Open `TR1 Rechnen` from `Meine Blätter`. Click the tab `Vorlagen`. Under `Meine Vorlagen` it says `Noch keine`. Type `TR Vorlage` into `Name der Vorlage` and click `Dieses Blatt als Vorlage`. `TR Vorlage` now stands under `Meine Vorlagen`.
2. Go back to `Meine Blätter`, click `Neues Blatt`, click the tab `Vorlagen`, click `TR Vorlage`. The new sheet shows the name line, the heading and the same 16 exercises with the same numbers as `TR1 Rechnen`. Set the title to `TR5 Kopie`.
3. Change the copy: click `Text` (tab `Start`), type `Nur in der Kopie`.
4. Export and compare.
5. Open `TR1 Rechnen` again: it must look as in your screenshot of sheet 1, without the new text.
6. Open `TR5 Kopie`, click the tab `Vorlagen`, click `TR Vorlage` again: the sheet shows the template as you saved it, without `Nur in der Kopie`. Click `Rückgängig` once: the text is back.
7. On `Meine Blätter` there must be five sheets, each with its title and a small picture of its first page.

## 15 minutes on the last five pull requests

1. Note the time with `date`. Stop after 15 minutes, wherever you are.
2. Read the titles and bodies:

   ```sh
   gh pr list -R pgoell/blattwerk --state merged -L 5 --json number,title,body,url
   ```

3. For each pull request, say in one line what a teacher can now do or no longer suffers. Skip one that changes nothing a teacher can see (tests, deploy, docs), and give its minutes to the others.
4. Try each change on one of your five sheets or on a new one, first as the body describes it, then try to break it:
   - the steps in an odd order;
   - `Rückgängig` and `Wiederholen` after each step, and several times in a row;
   - with several blocks picked (the button `Mehrere`, or Shift and click);
   - while a text, a cell or a menu is open;
   - at once after a reload of the page;
   - in a narrow window, if the pull request names the iPad or narrow windows: `resize_page` to 820 by 1180 and to 1180 by 820, or `emulate` an iPad. After, set the window back to 1280 by 1024 and reload the page: the editor picks its layout when it opens.
5. After each try, check that the sheet still shows what it should and that the PDF matches it.

## Issues

Open at most 8 issues in a run. Each gets exactly one label:

- `regression`: one of the last five pull requests brought the fault in. Name the pull request.
- `bug`: a fault not tied to those pull requests.
- `wish`: something a teacher would expect, as PowerPoint or Word do it, and the app lacks.

Before you open one, look for a duplicate, and skip the issue if an open one covers it:

```sh
gh issue list -R pgoell/blattwerk --state open --search "<two or three words of the fault>"
```

Open it:

```sh
gh issue create -R pgoell/blattwerk --label <label> --title "<what goes wrong, in a teacher's words>" --body "<body>"
```

The body holds: the steps to repeat the fault from an empty sheet, numbered; what you expected; what happened; the path of a screenshot under `/tmp/teacher-run` if one helps. One fault per issue. Never put a real teacher's name, e-mail or sheet content into an issue.

If you found more than 8, open the 8 worst: regressions first, then lost work and wrong print, then the rest. List the others in your report, one line each.

## Clean up

Do this always, also after a failure or a `BLOCKED`. The stage holds real teachers' files and must not stay.

1. `close_page` on your page.
2. Stop the stage and read its output. If it reports an error, run it once more and put the output into your report:

   ```sh
   mise -C /home/pascal/Code/blattwerk run stage:down
   ```

3. Delete what is left of your exports: `rm -f ~/Downloads/TR*.pdf`. Keep `/tmp/teacher-run`: the issues name its screenshots.

## Report

Write, in this order:

1. The five sheets, one line each: the title, then `ok` or `faulty` with the fault in a few words.
2. The answer key of sheet 1: `ok` or `faulty`.
3. The pull requests, one line each: the number, what you tried, what you found.
4. The issues you opened, each with its label and its link.
5. The faults that did not fit into the 8, one line each.
6. The minutes you spent on the sheets, on the pull requests and in all.
7. Whether `stage:down` ended clean.

End your report with a last line of its own. If you could not do the run, that line is `BLOCKED teacher-run: <reason>`. If you did it, also with faults found, that line is exactly:

DONE teacher-run
