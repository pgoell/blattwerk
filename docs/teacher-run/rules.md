## Rules

Allowed:

- The `chrome-devtools` tools `new_page`, `list_pages`, `navigate_page`, `click`, `fill`, `type_text`, `press_key`, `hover`, `drag`, `upload_file`, `handle_dialog`, `take_snapshot`, `take_screenshot`, `wait_for`, `resize_page`, `emulate`, `close_page`. Real clicks and keys only. This brief calls that page the MCP page.
- The tool `mise -C /home/pascal/Code/blattwerk run teacher:page -- <verb>`: a Chromium window of your own with a real mouse and real keys, 1280 by 1024, held between calls. Where this brief writes only a verb, such as `hover "PDF"`, it goes after the `--`. The tool's verbs as written here, and no other:
  - `start`: opens the window on the stage's start page, signed out. A second `start` replaces the first.
  - `stop`: ends it.
  - `open PATH`: a path on the stage, such as `/` or `/blatt/12`.
  - `click TARGET`
  - `double-click TARGET`
  - `shift-click TARGET`
  - `hover TARGET`
  - `drag FROM TO`
  - `key-drag KEY FROM TO`: holds `KEY` down, as `key` spells it, drags from `FROM` to `TO` and lets the key go. `key-drag Space X,Y X2,Y2` pans the desk: the hand a teacher gets by holding Space. `key Space` leaves the desk where it is.
  - `middle-drag FROM TO`: the same with the middle button held. On the desk it moves the view, as a teacher pans with the wheel's button.
  - `swipe FROM TO`: a finger put down at `FROM`, moved to `TO` and lifted, as on an iPad. The drawers open by a swipe from a window's edge only in the upright window: `resize 820 1180` first, then `swipe 817,600 660,600` opens the right one.
  - `wheel TARGET DY`: turns the wheel by `DY` pixels; a negative number is up.
  - `key KEYS [N]`: a key as Playwright spells it (`Escape`, `ArrowRight`, `Control+z`, `Delete`), `N` times. `+` is the German plus key, the one that types + with no Shift. `key "Control++"` zooms in, and so do `key "Control+NumpadAdd"` and `key "Control+Equal"`. A letter outside that list, such as `Ä`, is a keydown too: `key "Ä"` types it.
  - `type TEXT`: into whatever has the focus. A letter such as `Ü`, `ä`, `ö` or `ß` is a keydown, so a picked block opens on it and the letter is kept. `type "Übung"` on a picked text ends in `Übung`.
  - `where NAME`: prints each visible match with its `x,y` and changes nothing. A whole name or text goes first. Where none is called so, it prints each name or text that holds `NAME`, with capitals as written: `where "28"` prints `28 + 5 = at x,y`, and `where "%"` prints the zoom's number, such as `88 % at x,y`. A name with a slash, as `where "/ 7"`, works. A list is found by its label only, never by its options: `where "123"` finds no digit list. `where` changes nothing and still says `(outside the window)` for a match that lies outside the window: `where "Füllung und Rand"` may say so when the right panel is turned away. At 820 wide and at 1000 by 800 the zoom's number folds into `Mehr`, so `where "%"` finds nothing and says it may lie under `Mehr`: `click "Mehr"`, `click "Zoom"`, then `value "Zoom in Prozent"` reads the number.
  - `value NAME`: prints what the field of that name holds and changes nothing: a colour as `#rrggbb`, a slider's number. A heading that introduces a row of buttons, such as `Übertrag`, prints the button that is on: `Übertrag is Mit`.
  - `resize W H`
  - `screenshot [NAME]`: writes `/tmp/teacher-run/<NAME>.png`, the window and no more. NAME takes letters, digits, `_`, commas and `-` only: no spaces and no dots.
  - `pdf [TARGET]`: clicks the bar's `PDF` (`pdf Lösungen` for the answer key), saves the file into `/tmp/teacher-run/` under its own name and prints the path. The focus stays where it was: a slider you clicked before still takes the next key. While the bar "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert" waits for a choice, the PDF waits too, and `pdf` says so at once: then `pdf "Andere Version laden"` or `pdf "Mit dieser überschreiben"` makes the choice and saves the file that comes after it. With the dialog `Varianten drucken` open, `pdf` and `pdf Lösungen` take that dialog's button, not the bar's of the same name. `click "PDF"` and `click "Lösungen"` do the same, in the bar and in that dialog: the file is saved into the run folder and is not left in Downloads.
  - `drop FILE TARGET`: drops the file `/tmp/teacher-run/FILE` at the target, as a teacher drags a file from the desktop onto the sheet. Only a file in `/tmp/teacher-run` drops.
  - `upload FILE TARGET`: clicks the target, such as `"Bild"`, and picks `/tmp/teacher-run/FILE` in the file box it opens: a real upload, as the MCP page's `upload_file` does it.
  - `paste-elsewhere`: stands for another app, such as Word or a mail: pastes with Control+V into a field of its own and prints what that field took, words or a picture or nothing. The app's page and its focus stay as they were.
  - `ctrl-click TARGET`: holds Ctrl and clicks. On a page thumbnail it adds that page to the choice, or drops it. The thumbnail's words are the page's own too, so `click "Seite 3"` finds nothing once the page has text: `where "Seite 3"` prints the place, and `ctrl-click X,Y` uses it. `shift-click` still picks the range from the page in use.
  - `finger TARGET`: a finger put down at TARGET, held still for half a second, and lifted. On a block, a thumbnail or the empty page the menu opens when it lifts. A finger that moves is `swipe`, and that opens no menu.
  - `paste-word TEXT`: pastes TEXT as Word would, onto the sheet, or into a text that is open. `*fett*` is bold and `_schief_` is italic. A line that starts with `- ` is a bullet and one that starts with `1. ` is numbered. Write `\n` for a new line: `paste-word "Ein *fett* Wort\n- eins"`. A colour, a font, a size or a picture is not in these words.
  - `drop-web FILE TARGET`: drops FILE from the run folder as a picture dragged off a web page, where the browser hands the picture over. It lands at TARGET. `drop-web URL TARGET` with an address such as `https://example.org/katze.png` is a picture the page does not fetch: it says to copy it or save the file, and fetches nothing.
  - `mic`: gives the window a microphone. It has no real one, and the MCP page has none: record here. `click "Feedback"`, then `click "● Aufnahme starten"`. Shut the form while it records, with `key Escape`, `click "Schließen"` or `click "Abschicken"`. The clip stays, and the next time the form opens it says the recording was still running.
  - `expire`: ends the window's sign-in, as if the session had run out; the page stays as it is.
  - `box yes VERB [ARGS]` or `box no VERB [ARGS]`: runs that verb and answers the box it meets. A verb without `box` answers no. A box comes with a delete (its button's name ends in `löschen`) and when `open` would leave unsaved work; the output names its words.
  - `tidy`: deletes each `TR*.pdf` and `blattomat*.mcpb` in the downloads folder and each PDF in `/tmp/teacher-run`, and names each one it deleted. It needs no window.

  `TARGET`, `FROM` and `TO` are either `X,Y` in window pixels, the same pixels as the tool's screenshot, or a visible name in quotes: a control's whole name or a whole text on the screen. No match is an error. In a narrow window the bar folds some buttons away, at 820 wide the zoom's `Ganze Seite`: the error then says the name may lie under `Mehr`, so `click "Mehr"` and look again. So are several: the tool then lists each with its `x,y`, and you use the pixels. If one of the matches is the only control of that name (a button, a field, a list or a tab), the tool takes that control: `click "Zahlenraum"` takes the list, not the heading above it. The same where that control lies outside the window and a heading shares the name: `click "Aufgabenfamilien"` turns the panel to the list. With a text picked, `click "Text"` takes the left panel's button, not the right panel's heading, which is also called `Text`. If a named control lies outside the window and is the only one of that name, the tool turns the page or the panel to it by itself, clicks, and its output ends with `(turned the page to it)`. If the tool turns the page to a place you did not mean, as to a heading on page 2, press Escape to unpick the block and try again. A click on a greyed control prints `clicked at X,Y, on a greyed control: nothing happens`, also after the tool turned the panel to one that lay outside the window. Every verb's output ends with a line `The page is /blatt/12`: the sheet's number for `open /blatt/N`. The line before it is `The clock is N`, the seconds since `start`. The shell's `date` can run slow against the work, so the minutes come from this clock and not from `date`. A block on the sheet has no name: read its place off the screenshot. Every verb that acts also saves `/tmp/teacher-run/last.png` and prints its path. `click "Klassenarbeit"` takes the template's button, not the same word drawn in a little page: that word is also on `Klassenarbeit Deckblatt`, so `where` prints several, and when the button lies outside the window the click turns the left panel to it. With the zoom's list open, `click "Ganze Seite"` takes the list's item; `where` still prints the bar's button as well. One call acts and shows: look with your Read tool.

  One verb per shell call, then read what it printed. Never chain two verbs with `&&` or `;`, and never run a verb in a loop: the next step depends on what the last one did. A link that opens a new tab (as on `Konto`) does not take the window away: the tool shuts the new tab and says so.
- The shell commands this brief spells out, `date`, and `ls`, `rm`, `pdftoppm` and `pdffonts` on your own files in `/tmp/teacher-run` and on the `TR*.pdf` files in `~/Downloads`. `pdftoppm` takes `-r` from 60 to 110 (60 for the layout, up to 110 to read small digits), and `-f` and `-l` for one page, as `-f 2 -l 2`. `pdffonts` names the fonts of a PDF.
- `grep` in the shell, on a snapshot file in `/tmp/teacher-run` and on nothing else. There is no Grep tool. `wait_for` answers with the whole page in the chat: do not search that answer. To find a control's name, `take_snapshot` with its `filePath` `/tmp/teacher-run/<name>.txt` writes the snapshot to that file, and `grep` searches the file.
- `gh pr list`, `gh issue list`, `gh issue create` and `gh issue edit` as written below, and `gh label list -R pgoell/blattwerk` to know the labels. Of a pull request you read the title and the body only. `gh pr list` cuts each body at 2500 letters: read a longer one whole with `gh pr view N -R pgoell/blattwerk --json title,body`.

Forbidden:

- `evaluate_script` and any other script in the page.
- `curl` or any other direct call to `/api`.
- Any docker command.
- The page `/admin`.
- Anything under `~/.local/share`.
- Reading any file under `/home/pascal/Code/blattwerk`: source, tests, other docs.
- `gh pr diff` and `gh pr view --json files`.
- The live site `blattwerk.pgoell.com`.
- A script of your own that wraps the tool, and `sleep`. `where` waits up to 3 seconds for a match by itself, so run it again with no pause between the calls.

The tool is no way around this list: `open` takes paths of the stage only, and every ban holds in both windows.

Which window for what. The MCP page: `take_snapshot`, `wait_for`, `fill`, `upload_file`, plain clicks and reading. The tool's window: all that a mouse or a held key does (hover, drag, key-drag, Shift and click, double click, sliders, colours, lists, the wheel), and the whole hunt on the pull requests if you like. What the MCP page cannot do is there too: `ctrl-click`, `finger`, `paste-word`, `drop-web` and `mic`. The bar's `Einfügen` works in the tool's window too. Both are signed in as the same teacher. A delete in the MCP page (a button whose name ends in `löschen`) opens a browser box that asks to confirm: answer it with `handle_dialog`. If `take_screenshot` of the MCP page hangs, as it does when the page lies behind another tab, use `take_snapshot`.

A sheet is open in one of the two windows at a time. Before you change windows, wait for `Gespeichert`, go back to `Meine Blätter` in the one, then open the sheet in the other. Two windows on one sheet each hold a copy of their own: the later save meets the banner "Dieses Blatt wurde auf einem anderen Gerät geändert", and one copy's work is lost.

The MCP browser is shared with other sessions. Open your own page with `new_page` and act on that page only. Never select, navigate or close a page you did not open. If a call says "Could not connect to Chrome" or "browser is already running", do not kill or restart Chrome: stop the stage (see "Clean up") and end your report with the line `BLOCKED teacher-run: <reason>`. Do the same if the stage does not start or the sign-in fails twice.

