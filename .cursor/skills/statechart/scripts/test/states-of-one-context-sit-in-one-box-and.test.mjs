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
  "states of one context sit in one box, and an arrow from the box's border stands for the same step from each",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(
      join(dir, "Window.tla"),
      `---- MODULE Window ----
VARIABLES where, reply
vars == <<where, reply>>
Init == where = "Starting" /\\ reply = "none"
Boot == where = "Starting" /\\ where' = "Chat open" /\\ UNCHANGED reply
Ask == where = "Chat open" /\\ reply = "none" /\\ reply' = "pending" /\\ UNCHANGED where
Answer == reply = "pending" /\\ reply' = "shown" /\\ UNCHANGED where
Close == where = "Chat open" /\\ where' = "Window closed" /\\ UNCHANGED reply
Open == where = "Window closed" /\\ where' = "Chat open" /\\ reply' = "none"
Next == Boot \\/ Ask \\/ Answer \\/ Close \\/ Open
Spec == Init /\\ [][Next]_vars
NoReplyWhileClosed == ~(where = "Window closed" /\\ reply = "shown")
====
`,
    );
    writeFileSync(join(dir, "Window.cfg"), "SPECIFICATION Spec\nINVARIANT NoReplyWhileClosed\n");
    writeFileSync(
      join(dir, "window.map.mjs"),
      `const R = { none: "no question", pending: "reply on its way", shown: "reply shown" };
export const state = (v) => \`\${v.where}: \${v.where === "Starting" ? "loading" : R[v.reply]}\`;
export const step = (a) => ({ Boot: "the app starts", Ask: "you ask", Answer: "the reply arrives", Close: "you close the window", Open: "you open the window" })[a];
`,
    );
    assert.match(tlc(dir, "Window").stdout, /Invariant NoReplyWhileClosed is violated/);
    const args = ["--dot", "Window.dot", "--map", "window.map.mjs", "--traces", "Window.out"];
    const draw = (extra, out) => {
      const r = node("tlc-to-chart.mjs", [...args, ...extra, "--out", out], dir);
      assert.equal(r.status, 0, r.stderr);
      return readFileSync(join(dir, out), "utf8");
    };
    const boxed = draw([], "boxed.mmd");
    const flat = draw(["--flat"], "flat.mmd");

    assert.match(
      boxed,
      /^ {2}state "Chat open" as g0 \{\n {4}state "no question" as s0\n {4}state "reply on its way" as s1\n {4}state "reply shown" as s2\n {2}\}\n {2}state "Window closed" as g1 \{\n {4}state "no question" as s3\n {4}state "reply on its way" as s4\n {4}state "reply shown" as s5\n {2}\}\n {2}state "Starting: loading" as s6\n/m,
    );
    assert.deepEqual(
      boxed.split("\n").filter((l) => /you open the window/.test(l)),
      ["  g1 --> s0 : you open the window"],
    );
    assert.equal(flat.split("\n").filter((l) => /you open the window/.test(l)).length, 3);
    assert.doesNotMatch(flat, /as g\d+ \{/);
    assert.deepEqual(flatEdges(boxed), flatEdges(flat));
    assert.match(boxed, /^ {2}class s5 wrongPath$/m);
    assert.match(boxed, /^ {2}s\d --> s5 : 4\. /m);
    assert.match(boxed, /state "Breaks a rule" as legendWrong/);
  },
);

test(
  "from-spec --against compares the code with the spec on the parts both have, and --expect-broken sets the exit code",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(join(dir, "SaveCode.tla"), save("SaveCode", true));
    writeFileSync(join(dir, "SaveAgreed.tla"), save("SaveAgreed", false));
    writeFileSync(
      join(dir, "SaveCode.cfg"),
      "SPECIFICATION Spec\nINVARIANT TypeOK\nINVARIANT NoFalseSaved\n",
    );
    writeFileSync(
      join(dir, "SaveCode.map.mjs"),
      `export const readerActions = ["Save", "Edit"];
export const state = (v) => \`\${v.screen}, \${v.note.text}\`;
export const step = (a) => ({ Save: "you press Save", Retry: "the app tries again", Confirm: "the server stores the note", TimeOut: "the save times out", Edit: "you edit the note" })[a] ?? "";
export const cause = () => "the app stops after one retry and shows Saved anyway";
`,
    );
    const run = (...extra) =>
      node(
        "statechart.mjs",
        [
          "from-spec",
          "SaveCode.tla",
          "--against",
          "SaveAgreed.tla",
          "--label",
          "the agreed chart",
          ...extra,
        ],
        dir,
      );

    const unknown = run("--expect-broken", "NoLostNote");
    assert.equal(unknown.status, 2);
    assert.equal(
      unknown.stderr,
      "--expect-broken NoLostNote: not a rule in SaveCode.cfg, whose rules are TypeOK, NoFalseSaved.\n",
    );

    const expected = run("--expect-broken", "NoFalseSaved");
    assert.equal(expected.status, 0, expected.stderr);
    assert.equal(
      expected.stdout,
      `TLC on SaveCode.tla:
  TypeOK holds.
  NoFalseSaved is broken (expected).
TLC on SaveAgreed.tla:
  TypeOK holds.
  NoFalseSaved holds.

Chart: 4 states and 4 transitions from 10 model states.
3 work, 1 breaks a rule, 0 only in the agreed chart.

## 1. Saved, draft

Rule broken: You never see "Saved" while the note is still a draft.
Why: the app stops after one retry and shows Saved anyway.
There are 2 ways to get here in the model. This is the shortest.

0. Start: Editing, draft
1. You press Save. Now: Saving, draft
2. The save times out. Now: Saved, draft

In the agreed chart, step 2 (the save times out) cannot happen, so you stay at: Saving, draft.

Broken as expected: NoFalseSaved.

Wrote chart.mmd, bug-1.mmd, stories.md, summary.json in SaveCode-statechart.
`,
    );
    const out = join(dir, "SaveCode-statechart");
    const chart = readFileSync(join(out, "chart.mmd"), "utf8");
    assert.match(chart, /^stateDiagram-v2\n {2}%% second model \(against\): the agreed chart\n/m);
    assert.deepEqual(
      [...chart.matchAll(/^ {4}state "([^"]+)" as legend\w+$/gm)].map((m) => m[1]),
      ["Works", "Breaks a rule"],
    );
    assert.match(
      chart,
      /^ {2}s3 --> s3 : in the agreed chart, the save<br\/>times out cannot happen$/m,
    );
    const bug = readFileSync(join(out, "bug-1.mmd"), "utf8");
    assert.deepEqual([...bug.matchAll(/^ {2}state "([^"]+)" as s\d+$/gm)].map((m) => m[1]).sort(), [
      "Editing, draft",
      "Saved, draft",
      "Saving, draft",
    ]);
    const summary = JSON.parse(readFileSync(join(out, "summary.json"), "utf8"));
    assert.deepEqual(summary.second.role, "against");
    assert.deepEqual(summary.second.lacks.sort(), ["note.rev", "retries"]);
    assert.equal(summary.classes[0].against, "Saving, draft");
    assert.deepEqual(summary.codeLike, []);

    const unexpected = run();
    assert.equal(unexpected.status, 1, unexpected.stderr);
    const holds = run("--expect-broken", "TypeOK");
    assert.equal(holds.status, 1, holds.stderr);
    assert.match(
      holds.stdout,
      /\nBroken but not expected: NoFalseSaved\.\n\nExpected to break but holds: TypeOK\.\n/,
    );
    const listed = run("--expect-broken", "NoFalseSaved,TypeOK");
    assert.equal(listed.status, 1, listed.stderr);
    assert.match(listed.stdout, /\nExpected to break but holds: TypeOK\.\n/);
    assert.doesNotMatch(listed.stdout, /Broken but not expected/);

    writeFileSync(
      join(dir, "code.map.mjs"),
      readFileSync(join(out, "../SaveCode.map.mjs"), "utf8").replace(
        '"the app stops after one retry and shows Saved anyway"',
        '"retryCount hit maxRetries"',
      ),
    );
    const coded = run("--map", "code.map.mjs", "--expect-broken", "NoFalseSaved");
    assert.equal(coded.status, 0, coded.stderr);
    assert.match(
      coded.stdout,
      /These labels or causes read like code\. Write them in the reader's words in code\.map\.mjs:\n {2}retryCount hit maxRetries\n/,
    );
  },
);

test(
  "from-chart checks a chart whose regions guard each other, and draws it back unchanged",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(join(dir, "lamp.mmd"), lamp);
    const r = node(
      "statechart.mjs",
      ["from-chart", "lamp.mmd", "--expect-broken", "LitWhileOff"],
      dir,
    );
    assert.equal(r.status, 0, r.stdout + r.stderr);
    assert.match(r.stdout, /\nThe spec draws lamp\.mmd back unchanged\.\n/);
  },
);

test(
  "from-spec draws parallel regions only when they combine back into TLC's graph, and boxes otherwise",
  needsTlc,
  () => {
    const run = runDoor(doorMap);
    const proved = run("NoLostReply");
    assert.match(
      proved.stdout,
      /\nChart: 6 states and 5 transitions from 8 model states\.\nIt has 2 parallel regions, of 2 and 4 states\. Proof: their 7 arrows together make exactly the 8 states and 13 labeled steps of Door-statechart\/tlc\/regions-proof\.mmd, and the 5 drawn arrows make only steps among them\. Door-statechart\/tlc\/regions-all\.mmd has all 7 arrows\.\n5 work, 1 breaks a rule\.\n/,
    );
    const lines = proved.chart.split("\n");
    assert.ok(lines.includes('    state "Where you are" as region0 {'));
    assert.ok(lines.includes("    --"));
    const guarded = lines.findIndex((l) => /: the reply arrives \[when Window open\]$/.test(l));
    assert.match(lines[guarded + 1], /^ {6}%% when r0s\d$/);
    assert.doesNotMatch(proved.chart, /^ {6}r1s\d --> r1s\d : you open the window/m);
    assert.equal(
      proved.every
        .split("\n")
        .filter((l) => /^ {6}(r1s\d) --> \1 : you open the window \[when Window closed\]$/.test(l))
        .length,
      1,
    );
    const again = node(
      "compare-charts.mjs",
      ["tlc/regions-all.mmd", "tlc/regions-proof.mmd"],
      proved.out,
    );
    assert.equal(again.stdout, "same\n", again.stderr);

    const boxed = run("NoShownWhileClosed");
    assert.equal(boxed.every, null);
    assert.match(
      boxed.stdout,
      /\nIt has no parallel regions, because "Window closed: reply shown" is "Breaks a rule", and its two region states would show "Works"\.\n/,
    );
    assert.doesNotMatch(boxed.chart, /^ +--$/m);
    assert.match(boxed.chart, /^ {2}state "Window closed" as g\d \{$/m);
  },
);

test(
  "the mapping's guard words show on an arrow only when every model step behind it has them",
  needsTlc,
  () => {
    const run = runDoor(
      `${doorMap}export const guard = (a, before) =>
  ({ Answer: "window open", Drop: "window closed", Ask: before.where === "Open" ? "window open" : "" })[a] ?? "";
`,
    );
    const proved = run("NoLostReply");
    const lines = proved.chart.split("\n");
    for (const words of [
      /: the reply arrives \[window open\]$/,
      /: the app drops the reply \[window closed\]$/,
    ])
      assert.match(lines[lines.findIndex((l) => words.test(l)) + 1], /^ {6}%% when r0s\d$/);
    assert.ok(lines.some((l) => /^ {6}r1s\d --> r1s\d : you ask$/.test(l)));
    const again = node(
      "compare-charts.mjs",
      ["tlc/regions-all.mmd", "tlc/regions-proof.mmd"],
      proved.out,
    );
    assert.equal(again.stdout, "same\n", again.stderr);
    assert.match(proved.bug, / : \d\. the app drops the reply \[window closed\]$/m);

    const boxed = run("NoShownWhileClosed");
    assert.match(boxed.chart, / : you ask \[window open\]$/m);
    assert.match(boxed.chart, / : you ask$/m);
  },
);

test(
  "the mapping's timer() writes after N s on timer steps, and refuses a value that is not seconds",
  needsTlc,
  () => {
    const timed = runDoor(
      `${doorMap}export const timer = (a) => (a === "Drop" ? 30 : undefined);\n`,
    )("NoLostReply");
    assert.match(timed.chart, / : after 30 s, the app drops the reply \[when Window closed\]$/m);
    assert.match(timed.bug, / : \d\. after 30 s, the app drops the reply$/m);
    const again = node(
      "compare-charts.mjs",
      ["tlc/regions-all.mmd", "tlc/regions-proof.mmd"],
      timed.out,
    );
    assert.equal(again.stdout, "same\n", again.stderr);

    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(join(dir, "Door.tla"), doorSpec);
    writeFileSync(join(dir, "Door.cfg"), "SPECIFICATION Spec\nINVARIANT NoLostReply\n");
    writeFileSync(join(dir, "Door.map.mjs"), `${doorMap}export const timer = () => "soon";\n`);
    const r = node("statechart.mjs", ["from-spec", "Door.tla"], dir);
    assert.notEqual(r.status, 0);
    assert.match(
      r.stderr,
      /timer\(\) must return a number of seconds above 0, or nothing; got "soon" for \w+/,
    );
  },
);

test(
  "group() fills each state with its group's color, and the legend lists only the groups the chart draws",
  needsTlc,
  () => {
    const run = runDoor(groupMap)("NoLostReply");
    const lines = run.chart.split("\n");
    assert.deepEqual(lines.slice(0, lines.indexOf('  state "At the same time" as regions {')), [
      "---",
      "config:",
      "  markdownAutoWrap: false",
      "  state:",
      "    useMaxWidth: false",
      "---",
      "stateDiagram-v2",
      "  classDef plain fill:#f4f6f7,stroke:#566573,color:#1b2631",
      "  classDef plainWrong fill:#f4f6f7,stroke:#c0392b,stroke-width:4px,color:#7b241c",
      "  classDef group0 fill:#d1f2eb,stroke:#697976,color:#1b2631",
      "  classDef group0Wrong fill:#d1f2eb,stroke:#c0392b,stroke-width:4px,color:#7b241c",
      "  classDef group1 fill:#d6eaf8,stroke:#6b757c,color:#1b2631",
      "  classDef group2 fill:#fdebd0,stroke:#7f7668,color:#1b2631",
      '  state "Legend" as legend {',
      '    state "Reply shown" as legendGroup0',
      '    state "Waiting" as legendGroup1',
      '    state "Nothing to show" as legendGroup2',
      '    state "Breaks a rule" as legendWrong',
      "  }",
      "  class legendGroup0 group0",
      "  class legendGroup1 group1",
      "  class legendGroup2 group2",
      "  class legendWrong plainWrong",
    ]);
    assert.ok(lines.includes('      state "reply lost" as r1s1'));
    assert.deepEqual(
      lines.filter((l) => l.startsWith("  class r")),
      [
        "  class r0s0 plain",
        "  class r0s1 plain",
        "  class r1s0 group2",
        "  class r1s1 group0Wrong",
        "  class r1s2 group1",
        "  class r1s3 group0",
      ],
    );
    assert.match(run.stdout, /\n5 work, 1 breaks a rule\.\n/);
    const again = node(
      "compare-charts.mjs",
      ["tlc/regions-all.mmd", "tlc/regions-proof.mmd"],
      run.out,
    );
    assert.equal(again.stdout, "same\n", again.stderr);

    const bug = run.bug.split("\n");
    assert.ok(
      bug.includes(
        "  classDef group1Path fill:#d6eaf8,stroke:#1f3a93,stroke-width:4px,color:#1b2631",
      ),
    );
    assert.deepEqual(
      bug.filter((l) => /^ {2}class s\d/.test(l)),
      [
        "  class s0 group0Wrong",
        "  class s1 group1Path",
        "  class s2 group2Path",
        "  class s3 group1Path",
      ],
    );

    const summary = JSON.parse(readFileSync(join(run.out, "summary.json"), "utf8"));
    assert.deepEqual(summary.chartGroups, [
      { name: "Reply shown", color: "#d1f2eb", states: 2 },
      { name: "Waiting", color: "#d6eaf8", states: 1 },
      { name: "Nothing to show", color: "#fdebd0", states: 1 },
    ]);
    assert.deepEqual(summary.mixedGroups, []);
  },
);
