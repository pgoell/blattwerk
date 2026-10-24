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


test("a transition on a composite leaves from every state inside it", () => {
  const { regions } = parseMermaid(fixture("upload.mmd"));
  const main = regions.Main;
  assert.deepEqual([...main.states].sort(), [
    "Nothing chosen",
    "Upload failed",
    "Uploaded",
    "Uploading.Checking the file",
    "Uploading.Sending the file",
  ]);
  assert.deepEqual([...main.initial], ["Nothing chosen"]);
  assert.deepEqual(edges(main), [
    "Nothing chosen -> Uploading.Sending the file : you choose a file",
    "Upload failed -> Uploading.Sending the file : you retry",
    "Uploading.Checking the file -> Nothing chosen : you cancel",
    "Uploading.Checking the file -> Upload failed : the network drops",
    "Uploading.Checking the file -> Uploaded : the check passes",
    "Uploading.Sending the file -> Nothing chosen : you cancel",
    "Uploading.Sending the file -> Upload failed : the network drops",
    "Uploading.Sending the file -> Uploading.Checking the file : the last byte arrives",
  ]);
});

test("the deepest source wins when a composite and a state inside it share a label", () => {
  const { regions } = parseMermaid(`stateDiagram-v2
  state Form {
    [*] --> Typing
    Typing --> Confirm : you press Escape
    state Confirm
  }
  [*] --> Form
  Form --> Closed : you press Escape
  Confirm --> Closed : you press Escape`);
  assert.deepEqual(edges(regions.Main), [
    "Form.Confirm -> Closed : you press Escape",
    "Form.Typing -> Form.Confirm : you press Escape",
  ]);
});

test("a top-level composite split by -- makes one region per part", () => {
  const { regions, nevers } = parseMermaid(fixture("sync.mmd"));
  assert.deepEqual(Object.keys(regions), ["Connection", "Sync badge"]);
  assert.deepEqual(edges(regions["Sync badge"]), [
    "Synced -> Waiting to sync : the network drops",
    "Synced -> Waiting to sync : you edit a note",
    "Waiting to sync -> Synced : the server confirms",
  ]);
  assert.deepEqual(nevers, [
    {
      name: "NeverSyncedWhileOffline",
      states: ["Offline", "Synced"],
      sentence: 'You never see "Synced" while you are offline.',
    },
  ]);
});

test("a rule's sentence is the comment lines right above it, and a state key ignores field order", () => {
  const sentences = ruleSentences(`---- MODULE M ----
\\* Not about a rule.

\\* You never see "Saved"
\\* while the note is a draft.
NoFalseSaved == TRUE
Bare == TRUE
====`);
  assert.deepEqual(
    [...sentences],
    [["NoFalseSaved", 'You never see "Saved" while the note is a draft.']],
  );
  assert.equal(stateKey({ b: 1, a: { d: 2, c: [3] } }), stateKey({ a: { c: [3], d: 2 }, b: 1 }));
});

test("the legend is not part of the machine", () => {
  const { regions } = parseMermaid(`stateDiagram-v2
  state "Legend" as legend {
    state "Works today" as legendWorks
  }
  [*] --> A
  A --> B : go`);
  assert.deepEqual([...regions.Main.states].sort(), ["A", "B"]);
});

test("the parser refuses charts it cannot read", () => {
  assert.throws(() => parseMermaid("stateDiagram-v2\n  state A {\n  [*] --> B"), /unclosed/);
  assert.throws(() => parseMermaid("stateDiagram-v2\n  A ==> B"), /cannot read chart line/);
  assert.throws(
    () => parseMermaid("stateDiagram-v2\n  state A {\n    B --> C : go\n  }\n  [*] --> A"),
    /no \[\*\] --> start/,
  );
  assert.throws(
    () =>
      parseMermaid(
        "stateDiagram-v2\n  state A {\n    state B {\n      [*] --> C\n      --\n      [*] --> D\n    }\n    [*] --> B\n  }\n  [*] --> A",
      ),
    /below the top level/,
  );
  assert.throws(
    () => parseMermaid("stateDiagram-v2\n  [*] --> A\n  A --> [*] : you close the app"),
    /final state/,
  );
  assert.throws(
    () =>
      parseMermaid(
        'stateDiagram-v2\n  state "Something went wrong" as UploadError\n  state "Something went wrong" as SyncError\n  [*] --> UploadError\n  UploadError --> SyncError : go',
      ),
    /two states have the caption "Something went wrong"/,
  );
});

test("the parser reads class shorthand, repeated descriptions, and states first named inside a composite", () => {
  const { regions } = parseMermaid(`stateDiagram-v2
  classDef wrong fill:#fdd
  N : Nothing chosen
  N : press Upload to start
  [*] --> N
  N:::wrong --> Done : you finish
  Done --> Moving:::wrong
  state A {
    [*] --> X
    X --> Y : go
  }
  Moving --> A : start
  Y --> Z : next
  A --> N : cancel`);
  assert.deepEqual([...regions.Main.states].sort(), [
    "A.X",
    "A.Y",
    "Done",
    "Moving",
    "Nothing chosen",
    "Z",
  ]);
  assert.deepEqual(edges(regions.Main), [
    "A.X -> A.Y : go",
    "A.X -> Nothing chosen : cancel",
    "A.Y -> Nothing chosen : cancel",
    "A.Y -> Z : next",
    "Done -> Moving : ",
    "Moving -> A.X : start",
    "Nothing chosen -> Done : you finish",
  ]);
});

test("TLC values, states, graphs, and traces parse", () => {
  assert.deepEqual(parseValue('[a |-> <<1, "x">>, b |-> {TRUE}]'), { a: [1, "x"], b: [true] });
  assert.deepEqual(parseValue('("p" :> 1 @@ "q" :> 2)'), { p: 1, q: 2 });
  const graph = parseDot(`strict digraph DiskGraph {
1 [label="/\\\\ x = 0",style = filled]
2 [label="/\\\\ x = 1"]
1 -> 2 [label="Inc",color="black",fontcolor="black"];
1 -> 2 [label="Inc",color="black",fontcolor="black"];
2 -> 2 [label="Stay"];
}`);
  assert.equal(graph.nodes.get("1").init, true);
  assert.deepEqual(graph.nodes.get("2").vars, { x: 1 });
  assert.deepEqual(graph.edges, [{ from: "1", to: "2", action: "Inc" }]);
  assert.deepEqual(graph.loops, [{ from: "2", to: "2", action: "Stay" }]);
  assert.throws(
    () =>
      parseDot(
        'strict digraph DiskGraph {\n1 [label="/\\\\ x = 0",style = filled]\n2 [label="/\\\\ x = 1"]\n1 -> 2;\n}',
      ),
    /no action names/,
  );
  const [trace] = parseTraces(`Error: Invariant Small is violated.
Error: The behavior up to this point is:
State 1: <Initial predicate>
x = 0

State 2: <Inc line 9, col 8 to line 9, col 20 of module M>
x = 1
`);
  assert.equal(trace.invariant, "Small");
  assert.deepEqual(trace.steps, [
    { action: null, vars: { x: 0 } },
    { action: "Inc", vars: { x: 1 } },
  ]);
});

test("a rule broken by a start state is a counterexample of one state", () => {
  const text = `Error: Invariant NeverSyncedWhileOffline is violated by the initial state:
/\\ badge = "Synced"
/\\ conn = "Offline"

${done}`;
  assert.doesNotThrow(() => checkTlcOutput(text, "tlc.out"));
  assert.deepEqual(parseTraces(text), [
    {
      invariant: "NeverSyncedWhileOffline",
      steps: [{ action: null, vars: { badge: "Synced", conn: "Offline" } }],
    },
  ]);
});

test("TLC output from a run that failed or stopped early is refused", () => {
  assert.doesNotThrow(() =>
    checkTlcOutput(
      `Error: Invariant Small is violated.\nError: The behavior up to this point is:\nState 1: <Initial predicate>\nx = 0\n\n${done}`,
      "ok.out",
    ),
  );
  assert.throws(
    () =>
      checkTlcOutput(
        "Error: The invariant Nope specified in the configuration file\nis not defined in the specification.\n",
        "cfg.out",
      ),
    /cfg\.out: TLC stopped on an error that is not a broken rule/,
  );
  assert.throws(
    () => checkTlcOutput("Error: Parsing or semantic analysis failed.\n", "parse.out"),
    /not a broken rule/,
  );
  assert.throws(
    () => checkTlcOutput(evaluationError, "eval.out"),
    /TLC threw an unexpected exception/,
  );
  assert.throws(
    () =>
      checkTlcOutput(
        "Error: Invariant Small is violated.\nError: The behavior up to this point is:\nState 1: <Initial predicate>\nx = 0\n",
        "stopped.out",
      ),
    /did not finish/,
  );
  assert.deepEqual(
    parseTraces(evaluationError).map((t) => t.invariant),
    ["NoLost", null],
  );
});

test("a step that changes nothing keeps a state unsettled, and a quote in a reader label survives the chart", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(
    join(dir, "save.dot"),
    `strict digraph DiskGraph {
1 [label="/\\\\ s = \\"Idle\\"",style = filled]
2 [label="/\\\\ s = \\"Saving\\""]
1 -> 2 [label="Tap"];
2 -> 2 [label="Retry"];
}`,
  );
  writeFileSync(
    join(dir, "save.map.mjs"),
    `export const readerActions = ["Tap"];
export const state = (v, facts) => (v.s === "Idle" ? 'Badge says "Synced"' : facts.settled ? "Saved" : "Saving");
export const step = (action) => ({ Tap: "you tap Save" })[action] ?? "";
`,
  );
  const r = node(
    "tlc-to-chart.mjs",
    ["--dot", "save.dot", "--map", "save.map.mjs", "--highlight", "0", "--out", "chart.mmd"],
    dir,
  );
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(edges(parseMermaid(readFileSync(join(dir, "chart.mmd"), "utf8")).regions.Main), [
    'Badge says "Synced" -> Saving : you tap Save',
  ]);
});

test("chart-to-tla writes one action per label and one invariant per never line", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "sync.mmd"), fixture("sync.mmd"));
  const r = node("chart-to-tla.mjs", ["sync.mmd", "--module", "Sync"], dir);
  assert.equal(r.status, 0, r.stderr);
  const spec = readFileSync(join(dir, "Sync.tla"), "utf8");
  assert.match(spec, /^VARIABLES connection, syncBadge$/m);
  assert.match(
    spec,
    /^TheNetworkDrops ==\n {4}\/\\ \(connection \\in \{"Online"\} \\\/ syncBadge \\in \{"Synced"\}\)$/m,
  );
  assert.match(
    spec,
    /^NeverSyncedWhileOffline == ~\(connection = "Offline" \/\\ syncBadge = "Synced"\)$/m,
  );
  assert.equal(
    readFileSync(join(dir, "Sync.cfg"), "utf8"),
    "SPECIFICATION Spec\nINVARIANT TypeOK\nINVARIANT NeverSyncedWhileOffline\n",
  );
  assert.match(r.stderr, /rules TypeOK NeverSyncedWhileOffline/);
});

test("chart-to-tla refuses a never line that names no state", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(
    join(dir, "c.mmd"),
    "stateDiagram-v2\n  [*] --> A\n  A --> B : go\n  %% never Bad: C -- never C\n",
  );
  const r = node("chart-to-tla.mjs", ["c.mmd", "--module", "C"], dir);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /names "C", which is not a state/);
});

test("a never line names a state exactly, or every state inside a composite", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(
    join(dir, "c.mmd"),
    `stateDiagram-v2
  state "Saving" as S
  state "Saving..." as S2
  state Busy {
    [*] --> Checking
    Checking --> Sending : the check passes
  }
  [*] --> S
  S --> S2 : you wait
  S2 --> Busy : you send
  Busy --> S : you cancel
  %% never NoSaving: Saving -- You never see Saving.
  %% never NoBusy: Busy -- You are never busy.
`,
  );
  const r = node("chart-to-tla.mjs", ["c.mmd", "--module", "C"], dir);
  assert.equal(r.status, 0, r.stderr);
  const spec = readFileSync(join(dir, "C.tla"), "utf8");
  assert.match(spec, /^NoSaving == ~\(main = "Saving"\)$/m);
  assert.match(spec, /^NoBusy == ~\(main \\in \{"Busy\.Checking", "Busy\.Sending"\}\)$/m);
  assert.match(
    readFileSync(join(dir, "C.map.mjs"), "utf8"),
    /^export const readerActions = \[\];$/m,
  );
});

test("compare reads parallel regions as one machine, so a guard across regions shows", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "agreed.mmd"), door);
  writeFileSync(join(dir, "guarded.mmd"), flatDoor());
  writeFileSync(join(dir, "free.mmd"), flatDoor(["  U_O --> L_O : tap lock"]));
  const differ = node("compare-charts.mjs", ["agreed.mmd", "guarded.mmd"], dir);
  assert.equal(differ.status, 1);
  assert.match(
    differ.stdout,
    /transitions only in EXPECTED[^\n]*:\n {2}Unlocked \| Open --> Locked \| Open : tap lock\n1 difference\(s\)/,
  );
  const same = node("compare-charts.mjs", ["agreed.mmd", "free.mmd"], dir);
  assert.equal(same.stdout.trim(), "same", same.stdout);
});

test("a %% when line guards a step on the other region's states, and [words] are only its text", () => {
  const { regions } = parseMermaid(lamp);
  assert.deepEqual(regions.Bulb.transitions, [
    { from: "Dark", to: "Lit", label: "warm up", guard: { not: false, states: { Power: ["On"] } } },
    {
      from: "Lit",
      to: "Dark",
      label: "cool down",
      guard: { not: true, states: { Power: ["On"] } },
    },
  ]);
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "lamp.mmd"), lamp);
  writeFileSync(
    join(dir, "flat.mmd"),
    [
      "stateDiagram-v2",
      "  [*] --> OD",
      '  state "Off | Dark" as OD',
      '  state "On | Dark" as ND',
      '  state "On | Lit" as NL',
      '  state "Off | Lit" as OL',
      "  OD --> ND : flip the switch",
      "  ND --> OD : flip the switch",
      "  ND --> NL : warm up",
      "  NL --> OL : flip the switch",
      "  OL --> NL : flip the switch",
      "  OL --> OD : cool down",
    ].join("\n"),
  );
  const same = node("compare-charts.mjs", ["lamp.mmd", "flat.mmd"], dir);
  assert.equal(same.stdout, "same\n", same.stderr);
  const tla = node("chart-to-tla.mjs", ["lamp.mmd", "--module", "Lamp"], dir);
  assert.equal(tla.status, 0, tla.stderr);
  const spec = readFileSync(join(dir, "Lamp.tla"), "utf8");
  assert.match(spec, /\(bulb = "Dark" \/\\ power = "On" \/\\ bulb' = "Lit"\)/);
  assert.match(spec, /\(bulb = "Lit" \/\\ ~\(power = "On"\) \/\\ bulb' = "Dark"\)/);

  for (const [from, to, why] of [
    [
      "      %% when On\n",
      "      state Glow\n      %% when On\n",
      /must come right after a transition/,
    ],
    [
      "warm up [when the<br/>power is on]",
      "warm up",
      /must end its label with the guard's words in \[ \]/,
    ],
    ["      %% when On\n", "      %% when Nope\n", /names Nope, which is not a state id/],
    ["      %% when On\n", "      %% when Lit\n", /names Lit, which is in the step's own region/],
  ])
    assert.throws(() => parseMermaid(lamp.replace(from, to)), why);
  assert.throws(
    () =>
      parseMermaid(
        "stateDiagram-v2\n  [*] --> A\n  A --> B : go [when C]\n  %% when C\n  B --> C : on\n",
      ),
    /the chart has none/,
  );
  assert.deepEqual(
    edges(parseMermaid("stateDiagram-v2\n  [*] --> A\n  A --> B : go [user away]\n").regions.Main),
    ["A -> B : go"],
  );
});

test("a label with a guarded and an unguarded move in one region writes both moves", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "switch.mmd"), switchLamp);
  const r = node("chart-to-tla.mjs", ["switch.mmd", "--module", "Switch"], dir);
  assert.equal(r.status, 0, r.stderr);
  const spec = readFileSync(join(dir, "Switch.tla"), "utf8");
  assert.equal(
    spec.slice(spec.indexOf("\\* flip the switch"), spec.indexOf("\nNext ==")),
    `\\* flip the switch
FlipTheSwitch ==
    /\\ (power \\in {"Off", "On"} \\/ (bulb = "Dark" /\\ power = "Off") \\/ (bulb = "Lit"))
    /\\ \\/ (power = "Off" /\\ power' = "On")
       \\/ (power = "On" /\\ power' = "Off")
       \\/ (power \\notin {"Off", "On"} /\\ UNCHANGED power)
    /\\ \\/ (bulb = "Dark" /\\ power = "Off" /\\ bulb' = "Lit")
       \\/ (bulb = "Lit" /\\ bulb' = "Dark")
       \\/ (~((bulb = "Dark" /\\ power = "Off") \\/ (bulb = "Lit")) /\\ UNCHANGED bulb)
`,
  );
});

test("compare reads a one-region chart as the machine its steps reach, without steps that change nothing", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  const drawn =
    "stateDiagram-v2\n  [*] --> Idle\n  Idle --> Busy : start\n  Busy --> Idle : finish\n";
  writeFileSync(join(dir, "drawn.mmd"), drawn);
  writeFileSync(join(dir, "loop.mmd"), `${drawn}  Idle --> Idle : refresh\n`);
  writeFileSync(join(dir, "orphan.mmd"), `${drawn}  Lost --> Idle : come back\n`);
  const same = node("compare-charts.mjs", ["loop.mmd", "drawn.mmd"], dir);
  assert.equal(same.status, 0);
  assert.equal(same.stdout, "same\n");
  const orphan = node("compare-charts.mjs", ["orphan.mmd", "drawn.mmd"], dir);
  assert.equal(orphan.status, 1);
  assert.equal(
    orphan.stdout,
    "states the agreed chart's own steps never reach:\n  Lost\n1 difference(s)\n",
  );
});
