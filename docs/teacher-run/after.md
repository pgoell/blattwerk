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

To correct an issue you opened in this run, and no other issue:

```sh
gh issue edit <number> -R pgoell/blattwerk --title "<title>" --body "<body>" --add-label <label> --remove-label <label>
```

If you found more than 8, open the 8 worst: regressions first, then lost work and wrong print, then the rest. List the others in your report, one line each.

## Clean up

Do this always, also after a failure or a `BLOCKED`. The stage holds real teachers' files and must not stay.

1. `close_page` on your page.
2. End the tool's window, before the stage goes and also if you never started it:

   ```sh
   mise -C /home/pascal/Code/blattwerk run teacher:page -- stop
   ```

3. Stop the stage and read its output. If it reports an error, run it once more and put the output into your report:

   ```sh
   mise -C /home/pascal/Code/blattwerk run stage:down
   ```

4. Delete what is left of your exports with the verb `tidy`:

   ```sh
   mise -C /home/pascal/Code/blattwerk run teacher:page -- tidy
   ```

   Keep the folder `/tmp/teacher-run` and its pictures, because the issues name its screenshots. `tidy` deletes its PDFs.

5. Run `tidy` once more as the very last command before the `herdr` line. A PDF that came down late is deleted then, and the report names it (line 8). Then run the `herdr` line that the orchestrator's prompt gives you, and write the report.

## Report

Write, in this order:

1. The five sheets, one line each: the title, then `ok` or `faulty` with the fault in a few words.
2. The answer key of sheet 1: `ok` or `faulty`.
3. The pull requests, one line each: the number, what you tried, what you found.
4. The issues you opened, each with its label and its link.
5. The faults that did not fit into the 8, one line each.
6. The minutes you spent on the sheets, on the pull requests and in all.
7. Whether `stage:down` ended clean.
8. What the last `tidy` deleted, if anything.

End your report with a last line of its own. If you could not do the run, that line is `BLOCKED teacher-run: <reason>`. If you did it, also with faults found, that line is exactly:

DONE teacher-run
