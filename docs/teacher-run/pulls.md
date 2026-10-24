## 25 minutes on the last five pull requests

1. Note the time with `date`. Stop after 25 minutes, wherever you are, and not before. With an "above all", stop after 30 minutes instead, and do not stop at 25.
2. Read the titles and bodies. The lists leave out the titles that start with `ci`, `chore`, `docs`, `test`, `build` or `refactor` before they take five. A title that starts with `ci`, `chore`, `docs`, `build` or `refactor` is one a teacher does not see. A title that starts with `test` can still change the app, as #480 did:

   ```sh
   gh pr list -R pgoell/blattwerk --state merged -L 20 --json number,title,body,url,mergedAt --jq 'sort_by(.mergedAt) | reverse | map(select(.title | test("^(ci|chore|docs|test|build|refactor)[(:!]") | not)) | .[0:5][] | "#\(.number) \(.title)\n\(.url)\n\(.body[0:2500])\n"'
   ```

3. For each pull request, say in one line what a teacher can now do or no longer suffers. Skip one that changes nothing a teacher can see (tests, deploy, docs), and give its minutes to the others.
4. Go deep. Each sentence of a body that says what a teacher now sees or can do is a claim, and each claim gets a try of its own: a pull request with five claims gets five tries, not one. Try each on one of your five sheets or on a new one:
   - as the body describes it, in the tool's window where the claim is about a mouse, a hover, a drag or a key;
   - in a narrow window and in a wide one: `resize 820 1180` and `resize 1280 1024`, or `resize_page` in the MCP page. The editor picks its layout when it opens, so open the sheet again after each resize;
   - followed by `Rückgängig` and `Wiederholen`, and by `key Control+z`;
   - with the PDF beside the screen, where the claim is about print.
   - a claim you cannot try with clicks and keys is not a fault of the app. A block type the app does not offer is one: say so in the report and go on.
5. Then try to break it:
   - the steps in an odd order;
   - with the session run out: `expire`, then go on working; the MCP page stays signed in.
   - where a pull request is about what an account copies or sees: across the two teachers, as "Two teachers" says;
   - `Rückgängig` and `Wiederholen` after each step, and several times in a row;
   - with several blocks picked (the button `Mehrere`, or `click` and `shift-click`);
   - while a text, a cell or a menu is open;
   - at once after a reload of the page. `key F5` does not reload the tool's window: there a reload is `open /blatt/N`, with the sheet's number, which a line of each verb's output gives (`The page is /blatt/N`), or `open /` and a click on the sheet's title;
   - if the pull request names the iPad: `resize 1180 820` too, or `emulate` an iPad in the MCP page.
6. After each try, check that the sheet still shows what it should. At the end set the window back to 1280 by 1024. A block that lies on another shows nothing about ink, line spacing or a font: move them apart on the screen and in the PDF before you judge.
7. If time is left after all five, do not stop early: go on to the five pull requests before them.

   ```sh
   gh pr list -R pgoell/blattwerk --state merged -L 20 --json number,title,body,url,mergedAt --jq 'sort_by(.mergedAt) | reverse | map(select(.title | test("^(ci|chore|docs|test|build|refactor)[(:!]") | not)) | .[5:10][] | "#\(.number) \(.title)\n\(.url)\n\(.body[0:2500])\n"'
   ```

8. Those lists leave out a title that starts with `test`, and one of those can still change the app. Read each of them in the same 20, the whole body, with `gh pr view N -R pgoell/blattwerk --json title,body`. Try a claim a teacher can see, and skip one that changes nothing a teacher sees.

   ```sh
   gh pr list -R pgoell/blattwerk --state merged -L 20 --json number,title,body,url,mergedAt --jq 'sort_by(.mergedAt) | reverse | map(select(.title | test("^test[(:!]"))) | .[] | "#\(.number) \(.title)\n\(.url)\n"'
   ```

