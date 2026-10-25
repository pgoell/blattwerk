## Export and compare

Do this for every sheet.

1. Wait for `Gespeichert`. Click `Ganze Seite` in the bar first: the editor opens at 88 % and cuts the page off at the bottom. The zoom has no 100 %: its steps are 77, 88, 110 and 138 %. Compare at `Ganze Seite` only. Then `take_screenshot` of the editor with the whole page in view. Save it as `/tmp/teacher-run/<n>-screen.png`. A sheet of two pages gets one screenshot per page, from the tool's window: see sheet 4.
2. Click `PDF`. The page stays where it is and the browser saves `~/Downloads/<Titel>.pdf`. Wait until `ls ~/Downloads` shows it. If no file comes within 30 seconds, that is a fault.
3. Turn the PDF into pictures, one per page, and delete the PDF:

   ```sh
   pdftoppm -png -r 60 ~/Downloads/"TR1 Rechnen.pdf" /tmp/teacher-run/1-pdf
   ```

   ```sh
   rm ~/Downloads/"TR1 Rechnen.pdf"
   ```

   This writes `/tmp/teacher-run/1-pdf-1.png`, and `1-pdf-2.png` for a second page. Change the title and the number for the other sheets. To check the font, run `pdffonts` on the PDF before the `rm`.
4. Open the pictures with your Read tool and hold them beside the screenshot. Check, block by block:
   - the same number of pages, in the same order, each upright or on its side as on screen;
   - each block at the same place and of the same size;
   - the same words, with the same line breaks, the same font and size;
   - the same borders, lines and colours;
   - nothing cut off at a block's edge or the page's edge, and nothing missing or added.
5. Write down each difference with the sheet, the block and what differs.

In the tool's window steps 1 to 3 are, for sheet 3: `where "Gespeichert"` until it prints a match, `click "Ganze Seite"`, `screenshot 3-screen`, `pdf`, and then, with the path that `pdf` printed:

```sh
pdftoppm -png -r 60 "/tmp/teacher-run/TR3 Bild und Tabelle.pdf" /tmp/teacher-run/3-pdf
```

## The five sheets

Build each one on a new sheet from `Meine Blätter`, in this order, with exactly this content. A sheet may be built in either window, as long as it is open in one window at a time. If a step cannot be done as written with clicks and keys, note it as a fault and go on.

### 1. Maths sheet, title `TR1 Rechnen`

1. Click `Namenszeile`.
2. Click `Überschrift`, type `Plus und Minus`.
3. Click `Rechnen`. Twelve plus exercises up to 20 land on the sheet in 3 columns.
4. With the exercises picked, set in the right panel: under `Rechenart` turn `−` on beside `+`; `Zahlenraum` to `bis 100`; `Übertrag` to `Mit`; click `Eine Aufgabe mehr` until it says `16 Aufgaben`; click `Eine Spalte mehr` once, so it says `4 Spalten`.
5. Check on screen: 16 exercises, 4 columns, only plus and minus, no number and no result above 100, no result below 0, each with a carry. The numbers differ from run to run.
6. Export and compare.
7. The answer key: `Lösungen zeigen` turns it on screen. In the window of 1280 px it lies under `Mehr` at the bar's right: in the tool's window `click "Mehr"`, then `click "Lösungen zeigen"`; in the MCP page click `Mehr`, `take_snapshot`, and click the item `Lösungen zeigen` by its uid, since the snapshot shows it only while the menu is open. A wider window has it in the bar as the eye icon. The results show on screen. Take a screenshot, then click `Lösungen`, which saves `~/Downloads/TR1 Rechnen Lösungen.pdf`. Turn it into a picture as above. Check that the key holds the same 16 exercises as the sheet, that every result is right (work each one out), and that the plain PDF from step 6 shows no result. Turn `Lösungen zeigen` off again.

### 2. Lineatur writing sheet, title `TR2 Schreiben`

1. Click `Namenszeile`.
2. Click `Überschrift`, type `Schreibe den Satz ab`.
3. Click `Lineatur`. In the right panel set `Art der Lineatur` to `Lineatur 2 (Klasse 2)`, click `Eine Zeile mehr` until it says `8 Zeilen`, and click `Seitenbreite`. With the zoom's list shut that is the right panel's button: the zoom's own button is `Zoom`, and its list shows `Seitenbreite` only while the list is open.
4. Double-click the Lineatur and type `Oma malt im Garten.` Press Escape. `click "Nachspurtext"`, then `key ArrowDown` once, so it says Grau. Do not press Enter: another Enter opens the Lineatur's text.
5. Check on screen: 8 rows, each with its four lines, the sentence on the first row between the lines, in grey to trace over.
6. Export and compare. Look hard at where the letters sit on the lines.

### 3. Picture with table, title `TR3 Bild und Tabelle`

1. Make the picture, a red and a blue half in a dark frame, 240 by 160:

   ```sh
   python3 -c "import zlib,struct;w,h=240,160;row=lambda y:b'\0'+b''.join((b'\x22\x22\x22' if x<6 or y<6 or x>=w-6 or y>=h-6 else b'\xd0\x30\x30' if x<w//2 else b'\x30\x60\xd0') for x in range(w));c=lambda t,d:struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d));open('/tmp/teacher-run/bild.png','wb').write(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+c(b'IDAT',zlib.compress(b''.join(row(y) for y in range(h))))+c(b'IEND',b''))"
   ```

2. In the MCP page: set `Titel` to `TR3 Bild und Tabelle` first, since the tool's window finds the sheet by it. Click `Überschrift`, type `Mein Haustier`.
3. `upload_file` on the button `Bild` with `/tmp/teacher-run/bild.png` (in the tool's window, `upload bild.png "Bild"` does the same). The picture lands on the sheet, picked and on top of the heading. Move it below: `fill` the field `Y` with `40`, then `press_key` Enter.
4. Click `Tabelle`. It has 3 rows and 3 columns. In the right panel click `Eine Zeile mehr` once, so it says `4 Zeilen`, and turn `Kopfzeile` on. Place the table below the picture: `fill` the field `Y` with `115`, then `press_key` Enter.
5. Change windows: the cells are not in the snapshot and want a double click. In the MCP page `wait_for` `Gespeichert`, click the logo, `wait_for` `Neues Blatt`. In the tool's window: `open /`, `click "TR3 Bild und Tabelle"`, and `click "Beenden"` if the tour opens.
6. Read the first cell's place off the screenshot. `double-click X,Y` on it, then `type "Tier"`, `key Tab`, `type "Farbe"`, `key Tab`, `type "Beine"`, `key Tab`, `type "Hund"`, `key Tab`, `type "braun"`, `key Tab`, `type "4"`, `key Escape`. Tab goes to the next cell, and from a row's last cell to the next row's first. Leave the other rows empty.
7. Check on screen: the picture whole, red left and blue right, the frame on all four sides; the table below it with 4 rows and 3 columns, `Tier`, `Farbe`, `Beine` in the first row and `Hund`, `braun`, `4` in the second.
8. Export and compare. Here in the tool's window, as "Export and compare" ends. Look at the picture's frame and at the table's lines and words. Then `open /`: the sheet is open in no window, and sheet 4 starts in the MCP page.

### 4. Two pages, title `TR4 Zwei Seiten`

1. Click `Überschrift`, type `Seite eins`. Click `Text`, type `Lies den Text und male ein Bild dazu.`
2. Click `Neue Seite`. A second, empty page comes and is the one in use.
3. On page 2: click `Überschrift`, type `Seite zwei`. Click `Punkte`.
4. Click the tab `Ansicht`. Under `Format, Raster und Hilfslinien für` pick `Nur diese Seite`, then under `Format` pick `Quer`. Page 2 now lies on its side and page 1 stands upright.
5. Set the title in the window that built the sheet, before you change windows:
   - built in the MCP page: `take_snapshot`, click `Titel` by its uid, `press_key` Control+A, `type_text` `TR4 Zwei Seiten`, `press_key` Enter, then `wait_for` `Gespeichert`, click the logo, `wait_for` `Neues Blatt`. Remember that the MCP page cannot scroll back to page 1: it has no wheel and `PageUp` does nothing there.
   - built in the tool's window: `click "Titel"`, `key Control+a`, `type "TR4 Zwei Seiten"`, `key Enter`, then `where "Gespeichert"` until it prints a match.

   Then in the tool's window: `open /`, `click "TR4 Zwei Seiten"`, `where "Gespeichert"` until it prints a match, `click "Ganze Seite"`.
6. Export and compare. Here in the tool's window. Page 1 is in view: `screenshot 4-screen-1`. Read a place on the sheet off that picture and turn the wheel there until page 2 is in view, `wheel X,Y 1000` and once more if it takes that, then `screenshot 4-screen-2`. Then `pdf`. The PDF must have two pages: the first upright with `Seite eins`, the second on its side with `Seite zwei` and the points box. Then `open /`: sheet 5 starts in the MCP page.

### 5. Copy of a template, title `TR5 Kopie`

Three templates are built in for everyone: `Arbeitsblatt`, `Klassenarbeit`, `Beschriftungsblatt`. A teacher's own templates stand under `Meine Vorlagen`, and only that teacher sees them. A click on a template puts it in place of the whole sheet; `Rückgängig` brings the sheet back. That is how the app is meant to work.

1. Open `TR1 Rechnen` from `Meine Blätter`. Click the tab `Vorlagen`. Under `Meine Vorlagen` it says `Noch keine`. Type `TR Vorlage` into `Name der Vorlage` and click `Dieses Blatt als Vorlage`. `TR Vorlage` now stands under `Meine Vorlagen`.
2. Go back to `Meine Blätter`, click `Neues Blatt`, click the tab `Vorlagen`, click `TR Vorlage`. The new sheet shows the name line, the heading and the same 16 exercises with the same numbers as `TR1 Rechnen`. Set the title to `TR5 Kopie`.
3. Change the copy: click `Text` (tab `Start`), type `Nur in der Kopie`.
4. Export and compare.
5. Open `TR1 Rechnen` again: it must look as in your screenshot of sheet 1, without the new text.
6. Open `TR5 Kopie`, click the tab `Vorlagen`, click `TR Vorlage` again: the sheet shows the template as you saved it, without `Nur in der Kopie`. Click `Rückgängig` once: the text is back.
7. On `Meine Blätter` there must be five sheets, each with its title and a small picture of its first page.

