import assert from "node:assert/strict";
import {
  spawn,
  spawnSync,
} from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { test } from "node:test";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import {
  parseMermaid,
} from "../mermaid.mjs";
import {
  checkTlcOutput,
  findTlc,
  parseDot,
  parseTraces,
  parseValue,
  ruleSentences,
  stateKey,
} from "../lib.mjs";
import {
  here,
  scripts,
  fixture,
  edges,
  node,
  done,
  evaluationError,
  door,
  flatDoor,
  lamp,
  switchLamp,
  NO_TLC,
  FROM_SPEC_USAGE,
  FROM_CHART_USAGE,
  noTlc,
  tools,
  needsTlc,
  tlc,
  syncStory,
  pay,
  payMap,
  edit,
  flatEdges,
  save,
  doorSpec,
  doorMap,
  runDoor,
  groupMap,
  order,
  chargeAgain,
  chargeOnce,
  chargeFirstOnly,
  notify,
  writeLamp,
  writeSlowPay,
  startRun,
  until,
  ownTmp,
  tlcStarted,
  staged,
  changedMidRun,
  unshare,
  hidePidNamespace,
  hidingPreload,
  failRenames,
  failingRenames,
} from "./support.mjs";


test(
  "a run whose rename fails after it moves the output folder aside puts the folder back, or says where it is",
  { skip: needsTlc.skip || (!failingRenames && "cannot compile a rename preload") },
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeLamp(dir);
    const args = ["from-spec", "Lamp.tla", "--out", "shared"];
    const shared = join(dir, "shared");
    const first = node("statechart.mjs", args, dir);
    assert.equal(first.status, 0, first.stderr);
    const chart = readFileSync(join(shared, "chart.mmd"), "utf8");
    const run = (fails) =>
      node("statechart.mjs", args, dir, { LD_PRELOAD: failingRenames, RENAME_FAILS: fails });

    const back = run("NI");
    assert.equal(back.status, 2, back.stderr);
    assert.match(
      back.stderr,
      /^cannot replace shared: EIO: .*\. The run left shared as it was\.\n$/,
    );
    assert.equal(readFileSync(join(shared, "chart.mmd"), "utf8"), chart);
    assert.deepEqual(staged(dir), []);

    const stuck = run("NII");
    assert.equal(stuck.status, 2, stuck.stderr);
    const named = stuck.stderr.match(
      /^cannot replace shared: EIO: .*\. This run moved the previous shared to (\.shared-\w+-old) and could not put it back\.\n$/,
    );
    assert.ok(named, stuck.stderr);
    const aside = named[1];
    assert.equal(existsSync(shared), false);
    assert.equal(readFileSync(join(dir, aside, "chart.mmd"), "utf8"), chart);
    assert.deepEqual(staged(dir), [aside]);
  },
);

test(
  "each TLC run writes the standard modules in its own temp folder, so overlapping runs cannot rewrite them under each other",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeSlowPay(dir, 0);
    const tmp = ownTmp(dir, "tmp");
    const log = join(dir, "java.log");
    const java = join(dir, "java");
    writeFileSync(
      java,
      `#!/bin/sh
for a; do case "$a" in -Djava.io.tmpdir=*) t="\${a#-Djava.io.tmpdir=}"; esac; done
"$REAL_JAVA" "$@" > "$LOG.$$"; s=$?
cat "$LOG.$$"
echo "$t: $(grep 'Naturals.tla' "$LOG.$$")" >> "$LOG"
rm "$LOG.$$"
exit $s
`,
      { mode: 0o755 },
    );
    const r = node("statechart.mjs", ["from-spec", "Pay.tla"], dir, {
      JAVA: java,
      TLA2TOOLS: tools.jar,
      REAL_JAVA: tools.java,
      LOG: log,
      TMPDIR: tmp,
    });
    assert.equal(r.status, 0, r.stderr);
    const runs = readFileSync(log, "utf8").trim().split("\n");
    assert.ok(runs.length > 0);
    const folders = new Set();
    for (const line of runs) {
      const [folder, parsed] = line.split(": ");
      assert.ok(folder.startsWith(join(tmp, "tlc-")), line);
      assert.equal(parsed, `Parsing file ${join(folder, "Naturals.tla")}`);
      folders.add(folder);
    }
    assert.equal(folders.size, runs.length);
  },
);

test(
  "a run that TLC stops on an error keeps TLC's output and writes no output folder",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(
      join(dir, "Pay.tla"),
      "---- MODULE Pay ----\nVARIABLE x\nASSUME FALSE\nInit == x = 0\nSpec == Init /\\ [][x' = x]_x\n====\n",
    );
    writeFileSync(join(dir, "Pay.cfg"), "SPECIFICATION Spec\n");
    writeFileSync(join(dir, "Pay.map.mjs"), 'export const state = () => "Cart";\n');
    const tmp = ownTmp(dir, "tmp");
    const r = node("statechart.mjs", ["from-spec", "Pay.tla"], dir, { TMPDIR: tmp });
    assert.equal(r.status, 2);
    const [, file] = r.stderr.match(
      /^(\S+\/tlc\/Pay\.out): TLC stopped on an error that is not a broken rule: Assumption .* is false\.\n$/,
    );
    assert.ok(file.startsWith(tmp), file);
    assert.match(readFileSync(file, "utf8"), /Assumption .* is false/);
    assert.equal(existsSync(join(dir, "Pay-statechart")), false);
  },
);

test(
  "runs of two specs that overlap on one output folder all finish, and the folder always holds one run's files",
  needsTlc,
  async () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    const out = writeSlowPay(dir, 400);
    writeLamp(dir);
    const pay = ["from-spec", "Pay.tla", "--out", "shared"];
    const lamp = ["from-spec", "Lamp.tla", "--out", "shared"];
    const alone = {};
    for (const args of [pay, lamp]) {
      const solo = join(dir, `${args[1]}-alone`);
      const r = node("statechart.mjs", [...args.slice(0, 2), "--out", solo], dir);
      assert.equal(r.status, 0, r.stderr);
      alone[args[1]] = {
        top: readdirSync(solo).sort().join(),
        tlc: readdirSync(join(solo, "tlc")).sort().join(),
        chart: readFileSync(join(solo, "chart.mmd"), "utf8"),
        summary: readFileSync(join(solo, "summary.json"), "utf8"),
      };
    }
    const shared = join(dir, "shared");
    const seen = new Set();
    let watching = true;
    const watch = (async () => {
      while (watching) {
        try {
          seen.add(readdirSync(join(shared, "tlc")).sort().join());
        } catch (e) {
          if (e.code !== "ENOENT") throw e;
        }
        await sleep(5);
      }
    })();
    const runs = [];
    for (let i = 0; i < 6; i++) {
      runs.push(startRun(dir, { args: i % 2 ? lamp : pay }).done);
      await sleep(150);
    }
    const finished = await Promise.all(runs);
    watching = false;
    await watch;
    for (const r of finished) assert.equal(r.status, 0, r.stderr);
    const runsOf = new Map(Object.entries(alone).map(([spec, a]) => [a.tlc, spec]));
    for (const listing of seen) assert.ok(runsOf.has(listing), `tlc/ had ${listing}`);
    const last = alone[runsOf.get(readdirSync(join(shared, "tlc")).sort().join())];
    assert.equal(readdirSync(shared).sort().join(), last.top);
    assert.equal(readFileSync(join(shared, "chart.mmd"), "utf8"), last.chart);
    assert.equal(readFileSync(join(shared, "summary.json"), "utf8"), last.summary);
    assert.equal(existsSync(out), false);
    assert.deepEqual(staged(dir), []);
  },
);

test(
  "the output folder model keeps every rule, and breaks one with a shared TLC folder, without each guard, or when a failed rename deletes the folder moved aside",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    const model = (ext) => readFileSync(join(scripts, "model", `OutputFolder${ext}`), "utf8");
    const r = node(
      "statechart.mjs",
      ["from-spec", join(scripts, "model", "OutputFolder.tla"), "--out", join(dir, "out")],
      dir,
    );
    assert.equal(r.status, 0, r.stdout + r.stderr);
    assert.match(r.stdout, /\nNo rule is broken\.\n/);
    for (const [i, [rule, guard, without, story]] of [
      [
        "ChartsOneSpec",
        "/\\ read' = Set(read, r, read[r] \\cup {spec})",
        "/\\ read' = [q \\in Runs |-> read[q] \\cup {spec}]",
        /You start run 2 in a second shell\..*\n.*Run 2 moves its folder into place\. Now: Two runs going: chart of both specs/,
      ],
      [
        "ChartsOneSpec",
        '/\\ pc[r] = "publish" /\\ spec = snap[r] /\\ ~out.notes',
        '/\\ pc[r] = "publish" /\\ ~out.notes',
        /You edit the spec\..*\n.*Run 1 moves its folder into place\. Now: One run going: chart of both specs/,
      ],
      [
        "KeepsYourFiles",
        '/\\ pc[r] = "aside" /\\ ~aside[r].notes\n',
        '/\\ pc[r] = "aside"\n',
        /Run 1 deletes the old folder and finishes\. Now: Done: chart of the spec\n/,
      ],
      [
        "NeverLosesChart",
        "  /\\ \\/ /\\ aside[r].exists /\\ ~out.exists\n        /\\ out' = aside[r]\n        /\\ aside' = Set(aside, r, NoFolder)\n     \\/ UNCHANGED <<out, aside>>\n",
        "  /\\ out' = out\n  /\\ aside' = Set(aside, r, IF aside[r].notes THEN aside[r] ELSE NoFolder)\n",
        /Run 2 moves the old folder aside\. Now: .*, the old chart moved aside\n.*Run 2 cannot rename a folder and stops\. Now: One run going: no folder\n/,
      ],
      [
        "NeverLosesChart",
        '/\\ pc[r] = "swap" /\\ out.exists /\\ aside[r].exists /\\ ~out.notes',
        '/\\ pc[r] = "swap" /\\ out.exists /\\ aside[r].exists',
        /You save notes in the folder\..*\n.*Run 2 finds another run's folder in place and deletes the old folder\. Now: Two runs going: your notes\n/,
      ],
    ].entries()) {
      const mutant = join(dir, `${i}-${rule}`);
      mkdirSync(mutant);
      assert.ok(model(".tla").includes(guard), guard);
      writeFileSync(join(mutant, "OutputFolder.tla"), model(".tla").replace(guard, without));
      for (const ext of [".cfg", ".map.mjs"])
        writeFileSync(join(mutant, `OutputFolder${ext}`), model(ext));
      const m = node(
        "statechart.mjs",
        ["from-spec", "OutputFolder.tla", "--expect-broken", rule],
        mutant,
      );
      assert.equal(m.status, 0, m.stdout + m.stderr);
      assert.match(m.stdout, story);
    }
  },
);
