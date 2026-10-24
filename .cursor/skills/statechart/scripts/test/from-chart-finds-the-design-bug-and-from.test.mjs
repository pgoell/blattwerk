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


test("from-chart finds the design bug, and from-spec with the fix marks it fixed", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "sync.mmd"), fixture("sync.mmd"));
  const today = node("statechart.mjs", ["from-chart", "sync.mmd"], dir);
  assert.equal(today.status, 1, today.stderr);
  assert.equal(
    today.stdout,
    `Wrote Sync.tla, Sync.cfg, and Sync.map.mjs from sync.mmd.
TLC on Sync.tla:
  TypeOK holds.
  NeverSyncedWhileOffline is broken.

Chart: 4 states and 8 transitions from 4 model states.
3 work, 1 breaks a rule.

${syncStory}
The spec draws sync.mmd back unchanged.

Wrote chart.mmd, bug-1.mmd, stories.md, summary.json in Sync-statechart.
`,
  );
  assert.match(
    readFileSync(join(dir, "Sync-statechart", "bug-1.mmd"), "utf8"),
    /: 2\. the server confirms\n/,
  );

  const spec = readFileSync(join(dir, "Sync.tla"), "utf8");
  const guarded = spec
    .replace("TheServerConfirms ==\n", 'TheServerConfirms ==\n    /\\ connection = "Online"\n')
    .replace("MODULE Sync", "MODULE SyncFixed");
  assert.notEqual(guarded, spec);
  writeFileSync(join(dir, "SyncFixed.tla"), guarded);
  const fixed = node("statechart.mjs", ["from-spec", "Sync.tla", "--fixed", "SyncFixed.tla"], dir);
  assert.equal(fixed.status, 1, fixed.stderr);
  assert.equal(
    fixed.stdout,
    `TLC on Sync.tla:
  TypeOK holds.
  NeverSyncedWhileOffline is broken.
TLC on SyncFixed.tla:
  TypeOK holds.
  NeverSyncedWhileOffline holds.

Chart: 4 states and 9 transitions from 4 model states.
3 work today, 0 still wrong with the fix, 1 fixed or new with the fix.

${syncStory}
With the fix, step 2 (the server confirms) cannot happen, so you stay at: Offline | Waiting to sync.

Wrote chart.mmd, bug-1.mmd, stories.md, summary.json in Sync-statechart.
`,
  );
  const summary = JSON.parse(readFileSync(join(dir, "Sync-statechart", "summary.json"), "utf8"));
  assert.deepEqual(summary.chartStatus, { works: 3, wrong: 0, fixed: 1 });
  assert.equal(summary.classes[0].fix, "Offline | Waiting to sync");

  const map = readFileSync(join(dir, "Sync.map.mjs"), "utf8");
  writeFileSync(join(dir, "Sync.map.mjs"), `${map}export const group = () => "Your notes";\n`);
  const grouped = node(
    "statechart.mjs",
    ["from-spec", "Sync.tla", "--fixed", "SyncFixed.tla"],
    dir,
  );
  assert.equal(grouped.status, 1, grouped.stderr);
  const lines = readFileSync(join(dir, "Sync-statechart", "chart.mmd"), "utf8").split("\n");
  assert.deepEqual(
    lines.filter((l) => /^ {2}(classDef|class) |legend/.test(l)),
    [
      "  classDef plainFixed fill:#f4f6f7,stroke:#1e8449,stroke-width:4px,color:#145a32",
      "  classDef group0 fill:#d6eaf8,stroke:#6b757c,color:#1b2631",
      "  classDef group0Fixed fill:#d6eaf8,stroke:#1e8449,stroke-width:4px,color:#145a32",
      '  state "Legend" as legend {',
      '    state "Your notes" as legendGroup0',
      '    state "Fixed or new with the fix" as legendFixed',
      "  class legendGroup0 group0",
      "  class legendFixed plainFixed",
      "  class s0 group0Fixed",
      "  class s1 group0",
      "  class s2 group0",
      "  class s3 group0",
    ],
  );
  writeFileSync(join(dir, "Sync.map.mjs"), map);

  writeFileSync(join(dir, "Sync.tla"), guarded.replace("MODULE SyncFixed", "MODULE Sync"));
  const coded = node("statechart.mjs", ["from-chart", "sync.mmd"], dir);
  assert.equal(coded.status, 1, coded.stderr);
  assert.equal(
    coded.stdout,
    `Kept Sync.tla. Delete it to write the spec again from sync.mmd.
TLC on Sync.tla:
  TypeOK holds.
  NeverSyncedWhileOffline holds.

Chart: 3 states and 5 transitions from 3 model states.
3 work, 0 break a rule.

No rule is broken.

The spec does not draw sync.mmd:
  states only in EXPECTED (no path from the start reaches them in the spec, or the spec renamed them):
    Offline | Synced
  transitions only in EXPECTED (a guard in the spec blocks them, or the spec renamed the step):
    Offline | Synced --> Offline | Waiting to sync : the network drops
    Offline | Synced --> Offline | Waiting to sync : you edit a note
    Offline | Synced --> Online | Synced : the network returns
    Offline | Waiting to sync --> Offline | Synced : the server confirms
  5 difference(s)

Wrote chart.mmd, stories.md, summary.json in Sync-statechart.
`,
  );
  assert.deepEqual(readdirSync(join(dir, "Sync-statechart")).sort(), [
    "chart.mmd",
    "stories.md",
    "summary.json",
    "tlc",
  ]);
});

test(
  "--png exits 2 unless every chart renders, even with --expect-broken, and keeps the files it wrote",
  needsTlc,
  () => {
    const args = ["from-chart", "sync.mmd", "--expect-broken", "NeverSyncedWhileOffline", "--png"];
    const bin = mkdtempSync(join(tmpdir(), "fake-npx-"));
    const launch = "Error: Failed to launch the browser process!";
    writeFileSync(
      join(bin, "npx"),
      `#!/bin/sh
while [ $# -gt 0 ]; do
  case "$1" in -i) chart=$2 ; -o) png=$2 ; esac
  shift
done
for c in $UNRENDERED; do
  case "$chart" in */$c.mmd) echo "${launch}" >&2; exit 1 ; esac
done
echo png > "$png"
`,
      { mode: 0o755 },
    );
    for (const [unrendered, status, written] of [
      ["chart bug-1", 2, ["chart.mmd", "bug-1.mmd"]],
      ["bug-1", 2, ["chart.mmd", "bug-1.mmd", "chart.png"]],
      ["", 0, ["chart.mmd", "bug-1.mmd", "chart.png", "bug-1.png"]],
    ]) {
      const dir = mkdtempSync(join(tmpdir(), "statechart-"));
      writeFileSync(join(dir, "sync.mmd"), fixture("sync.mmd"));
      const r = node("statechart.mjs", args, dir, {
        PATH: `${bin}${delimiter}${process.env.PATH}`,
        UNRENDERED: unrendered,
      });
      assert.equal(r.status, status, `${unrendered}: ${r.stdout}${r.stderr}`);
      assert.equal(
        r.stderr,
        unrendered
          .split(" ")
          .filter(Boolean)
          .map((c) => `could not render Sync-statechart/${c}.mmd: ${launch}\n`)
          .join(""),
      );
      assert.match(r.stdout, /\nBroken as expected: NeverSyncedWhileOffline\.\n/);
      assert.equal(
        r.stdout.split("\n").at(-2),
        `Wrote ${[...written, "stories.md", "summary.json"].join(", ")} in Sync-statechart.`,
      );
      assert.deepEqual(
        readdirSync(join(dir, "Sync-statechart")).sort(),
        [...written, "stories.md", "summary.json", "tlc"].sort(),
      );
    }
  },
);

test(
  "a state reached only after a bug takes the bug's color, and the fix edge leaves the state before the changed step",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    const cfg = "SPECIFICATION Spec\nINVARIANT NoDoubleCharge\n";
    writeFileSync(
      join(dir, "Pay.tla"),
      pay(
        "Pay",
        `screen = "Paying" /\\ charges < 2 /\\ charges' = charges + 1 /\\ UNCHANGED screen`,
      ),
    );
    writeFileSync(
      join(dir, "PayFixed.tla"),
      pay(
        "PayFixed",
        `screen = "Paying" /\\ charges < 2 /\\ IF charges = 0 THEN charges' = 1 /\\ UNCHANGED screen ELSE screen' = "Paid" /\\ UNCHANGED charges`,
      ),
    );
    writeFileSync(join(dir, "Pay.cfg"), cfg);
    writeFileSync(join(dir, "PayFixed.cfg"), cfg);
    writeFileSync(join(dir, "pay.map.mjs"), payMap);
    assert.match(tlc(dir, "Pay").stdout, /Invariant NoDoubleCharge is violated/);
    assert.doesNotMatch(tlc(dir, "PayFixed").stdout, /is violated/);

    const statusOf = (chart) => {
      const names = new Map(
        [...chart.matchAll(/^ {2}state "([^"]+)" as (s\d+)$/gm)].map((m) => [
          m[2],
          m[1].replace(/<br\/>/g, " "),
        ]),
      );
      return Object.fromEntries(
        [...chart.matchAll(/^ {2}class (s\d+) (\w+)$/gm)].map((m) => [names.get(m[1]), m[2]]),
      );
    };
    const args = [
      "--dot",
      "Pay.dot",
      "--map",
      "pay.map.mjs",
      "--traces",
      "Pay.out",
      "--highlight",
      "0",
      "--out",
      "chart.mmd",
    ];
    assert.equal(node("tlc-to-chart.mjs", args, dir).status, 0);
    assert.deepEqual(statusOf(readFileSync(join(dir, "chart.mmd"), "utf8")), {
      Cart: "works",
      Paying: "works",
      "Paying, charged": "works",
      "Paying, charged twice": "wrong",
      "Refunded, charged": "wrong",
    });

    const withFix = [...args, "--fixed-dot", "PayFixed.dot", "--fixed-traces", "PayFixed.out"];
    assert.equal(node("tlc-to-chart.mjs", withFix, dir).status, 0);
    const chart = readFileSync(join(dir, "chart.mmd"), "utf8");
    assert.deepEqual(statusOf(chart), {
      Cart: "works",
      "Paid, charged": "fixed",
      Paying: "works",
      "Paying, charged": "works",
      "Paying, charged twice": "fixed",
      "Refunded, charged": "fixed",
    });
    assert.deepEqual(
      [...chart.matchAll(/^ {4}state "([^"]+)" as legend\w+$/gm)].map((m) => m[1]),
      ["Works today", "Fixed or new with the fix"],
    );
    assert.match(chart, /^stateDiagram-v2\n {2}%% second model \(fix\): the fix\n/m);
    const fixEdges = parseMermaid(chart).regions.Main.transitions.filter((t) =>
      t.label.startsWith("with the fix, "),
    );
    assert.deepEqual(
      fixEdges.map((t) => `${t.from} --> ${t.to} : ${t.label}`),
      ["Paying, charged --> Paid, charged : with the fix, the bank charges you"],
    );
  },
);

test(
  "from-spec writes a mapping to fill in, then draws each bug in every view the mapping has",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(
      join(dir, "Pay.tla"),
      pay(
        "Pay",
        `screen = "Paying" /\\ charges < 2 /\\ charges' = charges + 1 /\\ UNCHANGED screen`,
      ),
    );
    writeFileSync(
      join(dir, "Pay.cfg"),
      "SPECIFICATION Spec\n\\* The reader's rule.\nINVARIANTS\n  NoDoubleCharge\n",
    );
    const first = node("statechart.mjs", ["from-spec", "Pay.tla"], dir);
    assert.equal(first.status, 2);
    assert.equal(first.stdout, "TLC on Pay.tla:\n  NoDoubleCharge is broken.\n");
    assert.equal(
      first.stderr,
      "\nWrote Pay.map.mjs. Fill in its labels, then run this command again.\n",
    );
    const scaffold = readFileSync(join(dir, "Pay.map.mjs"), "utf8");
    assert.match(scaffold, /^\/\/ Variables: screen, charges\.$/m);
    assert.match(
      scaffold,
      /^const STEPS = \{\n\tCharge: "Charge",\n\tPay: "Pay",\n\tRefund: "Refund",\n\};$/m,
    );
    assert.equal(existsSync(join(dir, "Pay-statechart")), false);

    writeFileSync(
      join(dir, "Pay.map.mjs"),
      `${payMap}export const detail = (v) => \`charges = \${v.charges}\`;\n`,
    );
    const r = node("statechart.mjs", ["from-spec", "Pay.tla"], dir);
    assert.equal(r.status, 1, r.stderr);
    assert.equal(
      r.stdout,
      `TLC on Pay.tla:
  NoDoubleCharge is broken.

Chart: 5 states and 4 transitions from 5 model states.
3 work, 2 break a rule.

## 1. Paying, charged twice

Rule broken: \`NoDoubleCharge\`
Why: each charge request charges again.
This is the only way to get here in the model.

0. Start: Cart
1. You pay. Now: Paying
2. The bank charges you. Now: Paying, charged
3. The bank charges you. Now: Paying, charged twice

Wrote chart.mmd, bug-1.mmd, bug-1-developer.mmd, bug-1-layered.mmd, stories.md, summary.json in Pay-statechart.
`,
    );
    assert.match(
      readFileSync(join(dir, "Pay-statechart", "bug-1-layered.mmd"), "utf8"),
      /state "Paying, charged twice" as g\d \{\n {4}state "charges = 2" as s\d\n/,
    );
    assert.deepEqual(readdirSync(join(dir, "Pay-statechart")).sort(), [
      "bug-1-developer.mmd",
      "bug-1-layered.mmd",
      "bug-1.mmd",
      "chart.mmd",
      "stories.md",
      "summary.json",
      "tlc",
    ]);
    assert.equal(
      readFileSync(join(dir, "Pay-statechart", "tlc", "Pay.cfg"), "utf8"),
      "SPECIFICATION Spec\n",
    );
    assert.equal(
      readFileSync(join(dir, "Pay-statechart", "tlc", "Pay-NoDoubleCharge.cfg"), "utf8"),
      "SPECIFICATION Spec\nINVARIANT NoDoubleCharge\nCONSTRAINT NoDoubleCharge\n",
    );
  },
);

test("a rule broken by a start state marks that state wrong", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(
    join(dir, "Start.tla"),
    `---- MODULE Start ----
VARIABLES conn, badge
vars == <<conn, badge>>
Init == conn \\in {"Online", "Offline"} /\\ badge = "Synced"
Drop == conn = "Online" /\\ conn' = "Offline" /\\ badge' = "Waiting"
Next == Drop
Spec == Init /\\ [][Next]_vars
NeverSyncedWhileOffline == ~(conn = "Offline" /\\ badge = "Synced")
====
`,
  );
  writeFileSync(join(dir, "Start.cfg"), "SPECIFICATION Spec\nINVARIANT NeverSyncedWhileOffline\n");
  writeFileSync(
    join(dir, "start.map.mjs"),
    'export const state = (v) => `${v.conn} | ${v.badge}`;\nexport const step = () => "the network drops";\n',
  );
  assert.match(tlc(dir, "Start").stdout, /is violated by the initial state/);
  const args = [
    "--dot",
    "Start.dot",
    "--map",
    "start.map.mjs",
    "--traces",
    "Start.out",
    "--summary",
    "summary.json",
    "--out",
    "chart.mmd",
  ];
  const r = node("tlc-to-chart.mjs", args, dir);
  assert.equal(r.status, 0, r.stderr);
  const summary = JSON.parse(readFileSync(join(dir, "summary.json"), "utf8"));
  assert.deepEqual(
    summary.classes.map((c) => [c.end, c.readerSteps]),
    [["Offline | Synced", 0]],
  );
  assert.deepEqual(summary.chartStatus, { works: 2, wrong: 1, fixed: 0 });
});

test(
  "a bug that only the fixed model has is numbered after the current bugs and drawn wrong",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    const cfg = "SPECIFICATION Spec\nINVARIANT NoLostEdit\n";
    for (const [name, fixed] of [
      ["Edit", false],
      ["EditFixed", true],
    ]) {
      writeFileSync(join(dir, `${name}.tla`), edit(name, fixed));
      writeFileSync(join(dir, `${name}.cfg`), cfg);
      assert.match(tlc(dir, name).stdout, /Invariant NoLostEdit is violated/);
    }
    writeFileSync(
      join(dir, "edit.map.mjs"),
      'export const readerActions = ["Tap"];\nexport const state = (v) => v.s;\nexport const step = (a) => ({ Tap: "you tap Save", Lose: "the save fails", Flash: "the screen flashes", Back: "you go back" })[a] ?? "";\n',
    );
    const args = [
      "--dot",
      "Edit.dot",
      "--map",
      "edit.map.mjs",
      "--traces",
      "Edit.out",
      "--fixed-dot",
      "EditFixed.dot",
      "--fixed-traces",
      "EditFixed.out",
    ];
    const r = node(
      "tlc-to-chart.mjs",
      [
        ...args,
        "--cover",
        "--highlight",
        "0",
        "--story",
        "story.md",
        "--summary",
        "summary.json",
        "--out",
        "chart.mmd",
      ],
      dir,
    );
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stderr, /1 bug\(s\), 1 new with the fix/);
    const summary = JSON.parse(readFileSync(join(dir, "summary.json"), "utf8"));
    assert.deepEqual(
      summary.classes.map((c) => [c.n, c.end, c.fix]),
      [
        [1, "Lost edit", "Saving"],
        [2, "Flash", "new with the fix"],
      ],
    );
    assert.deepEqual(summary.chartStatus, { works: 2, wrong: 1, fixed: 1 });
    assert.match(readFileSync(join(dir, "story.md"), "utf8"), /^## 2\. New with the fix: Flash$/m);
    const two = node(
      "tlc-to-chart.mjs",
      [...args, "--highlight", "2", "--path-only", "--out", "bug2.mmd"],
      dir,
    );
    assert.equal(two.status, 0, two.stderr);
    assert.match(readFileSync(join(dir, "bug2.mmd"), "utf8"), /: 2\. the screen flashes\n/);
  },
);
