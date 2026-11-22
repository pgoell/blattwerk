# Review an area for deep modules

The lints look at one function or one file at a time. They do not see a task
spread over six shallow files, or a file that only hands calls on. This review
reads one area whole and files what should merge or move.

Run one when an area keeps producing bugs, or a file in it reaches 4,500
tokens (the limit is 5,000, `scripts/check-file-size`). A weekly job also runs
one on its own; see [The weekly design review](#the-weekly-design-review).

Every command below runs from the repository root.

## 1. Pick the area and list its files

An area is the code one feature lives in: the sheet's blocks, the editor's
panel, one task block such as `frontend/src/zahlzerlegung/`. Start from the
files whose names say so, then add the files they import from the same feature
and the ones that import them.

```sh
git ls-files frontend/src | grep -E 'zahlzerlegung'
```

Write the list down: it heads the findings.

## 2. Measure each file

For each file, its size in tokens, how many files import it, how many imports
it has, and how often it changed and broke:

```sh
for f in frontend/src/zahlzerlegung/zahlzerlegung.ts frontend/src/sheet/blocks/zahlzerlegung.tsx; do
  stem=$(basename "${f%.*}")
  echo "$f tokens=$(( $(wc -c < "$f") / 4 ))" \
    "imported-by=$(git grep -lE "from \"[./]*.*/$stem\"" -- frontend/src | wc -l)" \
    "imports=$(grep -c '^import' "$f")" \
    "commits=$(git log --oneline --since=3.months -- "$f" | wc -l)" \
    "fixes=$(git log --format=%s --since=3.months -- "$f" | grep -c '^fix')"
done
```

A file near 5,000 tokens with many fixes is where to read first. A file with
many imports and one importer is a place calls pass through.

## 3. Read each file and ask three questions

Read every file on the list in full. For each one, answer:

1. **Does a small interface hide real work, or does the file only pass calls
   on?** Count its exports and what each does. A function whose body is one
   call to another function with a fixed argument hides nothing. A component
   that takes twenty props and hands them to its children hides nothing either.
2. **How many files does one task touch?** Pick a change someone made or will
   make, such as adding a new block type, and find every file it touches. The
   commit that last did it shows this: `git show --stat <hash>`. When one
   question ("which blocks are there") is answered by a list written out in
   several files, `git grep` one item of the list and count the places. Check
   that every copy holds the same items; a copy that lacks one is a bug.
3. **What should merge or move?** Two files that always change together should
   be one. Code in a file because that file already had the arguments it needed,
   and not because it belongs to the feature, should move. A file cut in two to
   fit the size limit, at a line count rather than along a module, shows in its
   first commit: `git log --follow --format='%h %s' -- <file> | tail -1`.

## 4. Write the findings

Keep three to five, worst first. Each finding names the files and lines it is
about; what one task costs today, in files touched; the change, what merges or
moves and the interface that is left; and what the change costs, with an answer
to any reason the code's own comments give for its shape now.

Drop a finding that only renames or reorders. A finding has to make some task
touch fewer files or read less code.

## 5. File them

File each finding as its own issue labelled `refactor` and `later`, until
pgoell has picked which to build. File each bug found on the way as its own
issue labelled `bug`.

## The weekly design review

Every Monday at 03:15 Berlin time the `Design review` workflow
(`.github/workflows/design-review.yml`) runs steps 2 to 4 with an agent, on the
area busiest in the last 7 days. It never writes code.

The area is a source folder under `src/blattwerk` or `frontend/src`; a folder
of more than 20 files splits by the first word of each file name, as
`frontend/src/pages/editor:palette`. Tests belong to no area. The score is the
area's commits plus its `bug` and `regression` issues, both over 7 days; an
issue counts for the areas whose files it names. Files over 4,500 tokens break
a tie. Commits of a pull request that names a finding's issue do not count, nor
does an area reviewed in the last 4 weeks unless 3 or more bugs named it since.
To see what the next run would pick, with no token:

```sh
python3 .github/review/design.py pick
```

The agent reads the code with read tools and git only, and reads every
`review:*` issue, open and closed, so it does not suggest a finding again. A
workflow step files what it wrote as one issue labelled `refactor`, `later` and
`review:design`: at most 5 findings as a checklist. A week with no area or no
finding files nothing and says so in the job summary.

To act on the issue, tick the findings worth building and file each ticked one
as its own `refactor` issue, without `later`, with `From #<review issue>` in its
body; that line is how the next run knows which commits to leave out. Then
close the review issue. A finding left unticked on a closed issue counts as
rejected, and the job does not file it again.

## The pull request review

Every pull request from a branch of this repo gets two reviews in CI, the
`Review` and `Security` checks (`.github/workflows/ci.yml`, prompts in
`.github/review/`). Both run after Lint, Test and Commits pass, and skip a draft,
a fork and Dependabot. `REVIEW.md` says what counts as a finding. An Important
finding is a thread on its line; branch protection waits until every thread is
resolved. A pull request on a path in `.github/CODEOWNERS` also waits for
pgoell's approving review. How the findings were answered lately:

```sh
python3 .github/review/outcomes.py [days] [sample size]
```
