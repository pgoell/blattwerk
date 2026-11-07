# Review guide

The CI reviewer reads this file, `.claude/CLAUDE.md` and the pull request
before it reads the diff. Keep it short: every line costs a review.

## What counts as a failure here

- A saved sheet, template or share no longer opens, or opens changed.
- Print, PDF or Lösungen differ from what the editor shows.
- A block loses a block action: copy, paste, undo, redo, group, move to
  another page.
- A task block prints a wrong task or a false key for some panel setting or
  typed number.
- A block prop or MCP tool without its TSDoc description, a stale
  `src/blattwerk/sheet.schema.json`, or a new kind of task with no recipe in
  `docs/okf/recipes/`.
- A teacher reaches another teacher's sheets, uploads or tokens.
- Dev or a test touches the live data under `~/.local/share/blattwerk/`.
- A doc in `docs/` says something the code no longer does.

## Design

Look at how the change is built as well as whether it works. The lints see one
function or one file; they miss these, which `docs/review-an-area.md` explains.
Each point must name what would show it, so the author can check it:

- A shallow module: a new file, function or component whose body only passes
  calls on. Name the caller it should fold into.
- One task spread thin: name the files this one change touched that always
  change together, and the one they should become.
- A list written out twice: name every copy of the list (kinds of block,
  props, panel settings) that must now be kept the same by hand.
- Code in the wrong home: name the module the feature lives in and why the
  code belongs there.
- A file cut at a line count to fit the size limit: name the commit that cut it.
- A rule of `.claude/CLAUDE.md` broken. Quote the rule.
- Comment bloat on the diff's lines, docstrings and TSDoc included: history
  told in prose, the code restated, a doc or another comment repeated, a long
  comment where one line would do. Name the lines and give the shorter text.
  In the summary, never a thread.

Taste with no rule behind it is not a finding.

## What not to flag

- Formatting and the rules ruff, ty and tsc already enforce.
- A schema or block page out of date: `mise run lint` checks the drift.
- A missing test where the PR body names the test that covers the line.
- A design point about code the diff does not touch; the area review takes those.

## How to report

Only an Important finding becomes a thread on its line, and every thread must be
answered before the merge. Everything else goes in the summary, where the
author reads it and nothing waits on it: an agent fixes whatever it is told, so a
blocking design point costs a commit and a CI run whether it mattered or not.

- **Important**: a bug this diff brings in, or a gap against the linked issue.
  A thread on the file and line, naming the class of bug so the author fixes
  every place it occurs. Important findings come first: never leave one out to
  make room for anything else.
- **Design**: a point from the list above, with the change you would make. At
  most 3, in the summary.
- **Pre-existing**: a bug the base branch already has. In the summary, as a
  line the author can turn into an issue.
- **Nit**: worth a look, safe to ignore. In the summary.

At most 10 findings in all. Every finding names a file and a line in the diff;
do not guess a file name. Never report again a finding an earlier round raised.
The summary gives the count per tag, or says "No issues found."
