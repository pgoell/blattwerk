## Start the stage

1. End a window that an earlier run left (the folder holds its address, so this comes first), make your folder and clear old exports. Run each line as a command of its own.

   ```sh
   mise -C /home/pascal/Code/blattwerk run teacher:page -- stop
   ```

   ```sh
   rm -rf /tmp/teacher-run
   ```

   ```sh
   mkdir /tmp/teacher-run
   ```

   ```sh
   mise -C /home/pascal/Code/blattwerk run teacher:page -- tidy
   ```

2. Start a fresh stage, also if one seems to run already:

   ```sh
   mise -C /home/pascal/Code/blattwerk run stage:up
   ```

   It starts a copy of the live app on a copy of the live data. Its last five lines are:

   ```
   URL: http://127.0.0.1:8220
   E-Mail: teacher-run@stage.invalid
   Passwort: <a fresh password each time>
   E-Mail: teacher-run-2@stage.invalid
   Passwort: <another fresh password>
   ```

   Only this machine reaches the stage. The two test teachers are new accounts with no sheets and no templates of their own, and neither is an admin. You work as the first. The second is there to check that what one account copied never reaches the next: see "Two teachers".

## Sign in

1. Run `date +%s` and take its number as N. That number only names the context. The run's minutes come from `The clock is N`, not from this `date`: the shell's `date` can run slow against the work. `new_page` with `http://127.0.0.1:8220` and `isolatedContext` `teacher-run-N`, then `resize_page` to 1280 by 1024. Signed out, every path shows the form `Anmelden`. The context is new and empty for each run: each stage copies the same live data, so its first upload gets the same address as the first upload of the stage before, and a browser that kept the old picture would show it in place of the new one. The tool's window needs nothing of the kind: each `start` gives it an empty browser.
2. Fill `E-Mail` and `Passwort` with the two values the stage printed and click `Anmelden`.
3. You land on `Meine Blätter` with the line "Noch kein Blatt. Leg dein erstes an."
4. Sign in to the tool's window now, so it is ready when a step needs it:

   ```sh
   mise -C /home/pascal/Code/blattwerk run teacher:page -- start
   ```

   Then, each after the same `teacher:page --`: `click "E-Mail"`, `type "teacher-run@stage.invalid"`, `click "Passwort"`, `type "<the password>"`, `key Enter`. Read `last.png`: it shows `Meine Blätter`.

