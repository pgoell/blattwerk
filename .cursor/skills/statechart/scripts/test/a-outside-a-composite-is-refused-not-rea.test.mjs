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


test("a -- outside a composite is refused, not read as one region", () => {
  const split =
    "stateDiagram-v2\n  [*] --> Online\n  Online --> Offline : the network drops\n  --\n  [*] --> Synced\n  Synced --> Pending : you edit a note\n";
  assert.throws(() => parseMermaid(split), /-- outside a composite/);
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "split.mmd"), split);
  writeFileSync(join(dir, "door.mmd"), door);
  const tla = node("chart-to-tla.mjs", ["split.mmd", "--module", "Split"], dir);
  assert.notEqual(tla.status, 0);
  assert.match(tla.stderr, /-- outside a composite/);
  for (const pair of [
    ["split.mmd", "split.mmd"],
    ["door.mmd", "split.mmd"],
    ["split.mmd", "door.mmd"],
  ]) {
    const r = node("compare-charts.mjs", pair, dir);
    assert.equal(r.status, 2, pair.join(" "));
    assert.match(r.stderr, /^split\.mmd: the chart has -- outside a composite/);
  }
});

test("compare refuses a chart it cannot read, or an ACTUAL chart that is not drawn for comparison", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "agreed.mmd"), door);
  for (const pair of [
    ["agreed.mmd", "missing.mmd"],
    ["missing.mmd", "agreed.mmd"],
  ]) {
    const r = node("compare-charts.mjs", pair, dir);
    assert.equal(r.status, 2, pair.join(" "));
    assert.match(r.stderr, /^missing\.mmd: ENOENT/);
  }
  for (const [extra, why] of [
    ["  U_O --> L_O : 1. tap lock", /--highlight 0/],
    [
      "  %% second model (against): the spec",
      "actual.mmd: it has a second model; draw ACTUAL without --fixed-dot or --against-dot\n",
    ],
    [
      '  state "Locked" as g1 {\n    state "Closed" as L_C2\n  }',
      "actual.mmd: it has boxes; draw ACTUAL with --flat\n",
    ],
  ]) {
    writeFileSync(join(dir, "actual.mmd"), flatDoor([extra]));
    const r = node("compare-charts.mjs", ["agreed.mmd", "actual.mmd"], dir);
    assert.equal(r.status, 2, extra);
    if (typeof why === "string") assert.equal(r.stderr, why);
    else assert.match(r.stderr, why);
  }
});

test("an edge lists every step, writes shared leading words once, and the chart renders at its natural width", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  const nodes = [
    ["Home", 1],
    ["Home", 2],
    ["Home", 3],
    ["Away", 1],
    ["Away", 2],
    ["Done", 1],
  ].map(
    ([s, n], i) =>
      `${i + 1} [label="/\\\\ s = \\"${s}\\"\\n/\\\\ n = ${n}"${i ? "" : ",style = filled"}]`,
  );
  const steps = [
    "1 -> 4 TapPay",
    "2 -> 5 TapBack",
    "3 -> 4 TapHome",
    "4 -> 1 OpenThread",
    "5 -> 2 OpenApp",
    "4 -> 6 Finish",
  ];
  writeFileSync(
    join(dir, "nav.dot"),
    `strict digraph DiskGraph {\n${nodes.join("\n")}\n${steps.map((e) => e.replace(/ (\w+)$/, ' [label="$1"];')).join("\n")}\n}\n`,
  );
  writeFileSync(
    join(dir, "nav.map.mjs"),
    `export const state = (v) => v.s;
export const step = (a) => ({ TapPay: "you tap Pay", TapBack: "you tap Back", TapHome: "you tap Home", OpenThread: "you open the thread", OpenApp: "you open the phone app", Finish: "" })[a];
`,
  );
  writeFileSync(
    join(dir, "agreed.mmd"),
    `stateDiagram-v2
  [*] --> Home
  Home --> Away : you tap Pay
  Home --> Away : you tap Back
  Home --> Away : you tap Home
  Away --> Home : you open the thread
  Away --> Home : you open the phone app
  Away --> Done
`,
  );
  const draw = (...extra) => {
    const r = node(
      "tlc-to-chart.mjs",
      [
        "--dot",
        "nav.dot",
        "--map",
        "nav.map.mjs",
        "--highlight",
        "0",
        "--out",
        "chart.mmd",
        ...extra,
      ],
      dir,
    );
    assert.equal(r.status, 0, r.stderr);
    return readFileSync(join(dir, "chart.mmd"), "utf8");
  };
  const chart = draw();
  assert.ok(
    chart.startsWith(
      "---\nconfig:\n  markdownAutoWrap: false\n  state:\n    useMaxWidth: false\n---\nstateDiagram-v2\n",
    ),
    chart,
  );
  const shortened = [
    "Away -> Done : ",
    "Away -> Home : you open the thread or the phone app",
    "Home -> Away : you tap Pay, Back, or Home",
  ];
  assert.deepEqual(edges(parseMermaid(chart).regions.Main), shortened);
  const crlf = chart.replace("---\n", "---  \n").replaceAll("\n", "\r\n");
  assert.deepEqual(edges(parseMermaid(crlf).regions.Main), shortened);
  const refused = node("compare-charts.mjs", ["agreed.mmd", "chart.mmd"], dir);
  assert.equal(refused.status, 2);
  assert.match(refused.stderr, /draw ACTUAL with --full-labels/);
  const full = draw("--full-labels");
  assert.match(full, /^stateDiagram-v2\n {2}%% labels in full\n/m);
  assert.deepEqual(edges(parseMermaid(full).regions.Main), [
    "Away -> Done : ",
    "Away -> Home : you open the thread or you open the phone app",
    "Home -> Away : you tap Pay or you tap Back or you tap Home",
  ]);
  assert.equal(node("compare-charts.mjs", ["agreed.mmd", "chart.mmd"], dir).stdout, "same\n");
});

test("statechart.mjs writes the spec next to the chart, keeps it on the next run, and stops without TLC", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "notes-app.mmd"), fixture("sync.mmd"));
  const first = node("statechart.mjs", ["from-chart", "notes-app.mmd"], dir, noTlc);
  assert.equal(first.status, 2);
  assert.equal(
    first.stdout,
    "Wrote NotesApp.tla, NotesApp.cfg, and NotesApp.map.mjs from notes-app.mmd.\n",
  );
  assert.equal(first.stderr, NO_TLC);
  assert.equal(
    readFileSync(join(dir, "NotesApp.cfg"), "utf8"),
    "SPECIFICATION Spec\nINVARIANT TypeOK\nINVARIANT NeverSyncedWhileOffline\n",
  );
  const again = node("statechart.mjs", ["from-chart", "notes-app.mmd"], dir, noTlc);
  assert.equal(
    again.stdout,
    "Kept NotesApp.tla. Delete it to write the spec again from notes-app.mmd.\n",
  );
  const spec = node("statechart.mjs", ["from-spec", "NotesApp.tla"], dir, noTlc);
  assert.equal(spec.status, 2);
  assert.equal(spec.stderr, NO_TLC);
  const missingJar = node("statechart.mjs", ["from-spec", "NotesApp.tla"], dir, {
    TLA2TOOLS: "/nonexistent/tla2tools.jar",
  });
  assert.equal(missingJar.status, 2);
  assert.equal(
    missingJar.stderr,
    "TLA2TOOLS is /nonexistent/tla2tools.jar, which does not exist.\n",
  );
});

test("statechart.mjs writes no output folder when it refuses the input", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "tla2tools.jar"), "");
  writeFileSync(join(dir, "Pay.tla"), "---- MODULE Pay ----\n====\n");
  writeFileSync(join(dir, "Pay.cfg"), "SPECIFICATION Spec\nINVARIANT Paid\n");
  writeFileSync(join(dir, "cart.mmd"), "stateDiagram-v2\n  [*] --> Cart\n  Cart --> Paid : pay\n");
  for (const args of [
    ["from-spec", "Pya.tla"],
    ["from-spec", "Pay.tla", "--expect-broken", "Unpaid"],
    ["from-spec", "Pay.tla", "--fixed", "PayFixd.tla"],
    ["from-chart", "cart.mmd", "--expect-broken", "Unpaid"],
  ]) {
    const r = node("statechart.mjs", args, dir, { TLA2TOOLS: join(dir, "tla2tools.jar") });
    assert.equal(r.status, 2, r.stderr);
  }
  assert.deepEqual(
    readdirSync(dir).filter((f) => f.endsWith("-statechart")),
    [],
  );
});

test("statechart.mjs does not use an output folder that has files that it did not write", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "tla2tools.jar"), "");
  writeFileSync(join(dir, "Pay.tla"), "---- MODULE Pay ----\n====\n");
  writeFileSync(join(dir, "Pay.cfg"), "SPECIFICATION Spec\n");
  const env = { TLA2TOOLS: join(dir, "tla2tools.jar") };
  const cwd = node("statechart.mjs", ["from-spec", "Pay.tla", "--out", "."], dir, env);
  assert.equal(cwd.status, 2);
  assert.equal(
    cwd.stderr,
    ". has 3 files that this command did not write, such as Pay.cfg. A run puts its files in place of the whole output folder, so pass --out with a new folder.\n",
  );
  const out = join(dir, "Pay-statechart");
  mkdirSync(join(out, "tlc"), { recursive: true });
  writeFileSync(join(out, "chart.mmd"), "kept\n");
  writeFileSync(join(out, ".DS_Store"), "");
  writeFileSync(join(out, "notes.md"), "mine\n");
  const notes = node("statechart.mjs", ["from-spec", "Pay.tla"], dir, env);
  assert.equal(notes.status, 2);
  assert.equal(
    notes.stderr,
    "Pay-statechart has a file that this command did not write: notes.md. A run puts its files in place of the whole output folder, so pass --out with a new folder.\n",
  );
  assert.deepEqual(readdirSync(dir).sort(), [
    "Pay-statechart",
    "Pay.cfg",
    "Pay.tla",
    "tla2tools.jar",
  ]);
  assert.deepEqual(readdirSync(out).sort(), [".DS_Store", "chart.mmd", "notes.md", "tlc"]);
  assert.equal(readFileSync(join(out, "chart.mmd"), "utf8"), "kept\n");
});

test("statechart.mjs exits 2 and names a helper script that cannot start", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "notes-app.mmd"), fixture("sync.mmd"));
  writeFileSync(join(dir, "no-node.cjs"), 'process.execPath = "/nonexistent/node";\n');
  const r = node("statechart.mjs", ["from-chart", "notes-app.mmd"], dir, {
    NODE_OPTIONS: `--require ${join(dir, "no-node.cjs")}`,
  });
  assert.equal(r.status, 2, r.stderr);
  assert.match(r.stderr, /chart-to-tla\.mjs/);
});

test("statechart.mjs names the chart it refuses and the argument it does not know", () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(
    join(dir, "c.mmd"),
    "stateDiagram-v2\n  [*] --> A\n  A --> B : go\n  %% never Bad: C -- never C\n",
  );
  const refused = node("statechart.mjs", ["from-chart", "c.mmd"], dir);
  assert.equal(refused.status, 2);
  assert.equal(refused.stdout, "");
  assert.equal(refused.stderr, 'c.mmd: never line names "C", which is not a state in the chart\n');
  const unknown = node("statechart.mjs", ["from-chart", "c.mmd", "--fixed", "CFixed.tla"], dir);
  assert.equal(unknown.status, 2);
  assert.equal(
    unknown.stderr,
    "unknown argument --fixed. Run node statechart.mjs from-chart --help for the flags, the output, and the exit codes.\n",
  );
  const sameName = node("statechart.mjs", ["from-spec", "C.tla", "--fixed", "fix/C.tla"], dir);
  assert.equal(sameName.status, 2);
  assert.equal(
    sameName.stderr,
    "fix/C.tla needs its own file and module name, such as CFixed.tla.\n",
  );
  const sameAgreed = node("statechart.mjs", ["from-spec", "C.tla", "--against", "a/C.tla"], dir);
  assert.equal(
    sameAgreed.stderr,
    "a/C.tla needs its own file and module name, such as CAgreed.tla.\n",
  );
  for (const [extra, stderr] of [
    [
      ["--fixed", "F.tla", "--against", "A.tla"],
      "use --fixed or --against, not both. Run node statechart.mjs from-spec --help for the flags, the output, and the exit codes.\n",
    ],
    [
      ["--label", "the new build"],
      "--label names the --fixed or --against model; it needs one of them. Run node statechart.mjs from-spec --help for the flags, the output, and the exit codes.\n",
    ],
  ]) {
    const r = node("statechart.mjs", ["from-spec", "C.tla", ...extra], dir);
    assert.equal(r.status, 2, extra.join(" "));
    assert.equal(r.stderr, stderr);
  }
  const valueless = node("statechart.mjs", ["from-chart", "c.mmd", "--out"], dir);
  assert.equal(valueless.status, 2);
  assert.equal(
    valueless.stderr,
    "--out needs a value. Run node statechart.mjs from-chart --help for the flags, the output, and the exit codes.\n",
  );
  const bare = node("statechart.mjs", [], dir);
  assert.equal(bare.status, 2);
  assert.equal(
    bare.stderr,
    `Usage: ${FROM_SPEC_USAGE}
       ${FROM_CHART_USAGE}
Run node statechart.mjs --help for the flags, the output, and the exit codes.
`,
  );
});

test("every script prints its help with -h or --help, and points at it for an argument it does not know", () => {
  const help = {
    "statechart.mjs": [[], `Usage: ${FROM_SPEC_USAGE}`],
    "statechart.mjs from-spec": [["from-spec"], `Usage: ${FROM_SPEC_USAGE}`],
    "statechart.mjs from-chart": [["from-chart", "notes-app.mmd"], `Usage: ${FROM_CHART_USAGE}`],
    "chart-to-tla.mjs": [[], "Usage: node chart-to-tla.mjs CHART.mmd --module NAME [--dir OUT]"],
    "tlc-to-chart.mjs": [[], "Usage: node tlc-to-chart.mjs --dot FILE --map FILE [options]"],
    "compare-charts.mjs": [[], "Usage: node compare-charts.mjs EXPECTED.mmd ACTUAL.mmd"],
  };
  for (const [name, [before, usage]] of Object.entries(help)) {
    const script = name.split(" ")[0];
    for (const flag of ["-h", "--help"]) {
      const r = node(script, [...before, flag], here);
      assert.equal(r.status, 0, `${name} ${flag}`);
      assert.equal(r.stderr, "");
      assert.equal(r.stdout.split("\n")[0], usage);
      assert.match(r.stdout, /\nExit codes\n {2}0 .*\n(.*\n)* {2}1 .*\n(.*\n)* {2}2 /);
    }
  }
  const top = node("statechart.mjs", ["--help"], here).stdout.split("\n");
  assert.equal(top[1], `       ${FROM_CHART_USAGE}`);
  assert.equal(top[2], "       node statechart.mjs [from-spec|from-chart] --help");
  for (const flag of [
    "--fixed FIXED.tla",
    "--label TEXT",
    "--map FILE",
    "--module NAME",
    "--title TEXT",
    "--out DIR",
    "--png",
    "-h, --help",
  ])
    assert.ok(
      top.some((l) => l.startsWith(`  ${flag}  `)),
      flag,
    );
  for (const [script, args, stderr] of [
    [
      "statechart.mjs",
      ["from-spec", "--nope"],
      "unknown argument --nope. Run node statechart.mjs from-spec --help for the flags, the output, and the exit codes.\n",
    ],
    [
      "chart-to-tla.mjs",
      ["--nope"],
      "unknown argument --nope. Run node chart-to-tla.mjs --help for the flags.\n",
    ],
    [
      "tlc-to-chart.mjs",
      ["--nope"],
      "unknown argument --nope. Run node tlc-to-chart.mjs --help for the flags.\n",
    ],
    [
      "tlc-to-chart.mjs",
      ["--dot", "a.dot", "--map", "a.map.mjs", "--regions"],
      "--regions draws the whole customer chart: use --highlight 0, without --flat or --path-only. Run node tlc-to-chart.mjs --help for the flags.\n",
    ],
    [
      "tlc-to-chart.mjs",
      ["--dot", "a.dot", "--map", "a.map.mjs", "--proof", "p.mmd"],
      "--proof writes the regions proof; it needs --regions. Run node tlc-to-chart.mjs --help for the flags.\n",
    ],
    [
      "compare-charts.mjs",
      ["--nope"],
      "unknown argument --nope. Run node compare-charts.mjs --help for the flags.\n",
    ],
  ]) {
    const r = node(script, args, here);
    assert.equal(r.status, 2, script);
    assert.equal(r.stdout, "");
    assert.equal(r.stderr, stderr);
  }
});

test("from-chart checks the agreed chart and draws it back unchanged", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "upload.mmd"), fixture("upload.mmd"));
  const r = node("statechart.mjs", ["from-chart", "upload.mmd"], dir);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(
    r.stdout,
    `Wrote Upload.tla, Upload.cfg, and Upload.map.mjs from upload.mmd.
TLC on Upload.tla:
  TypeOK holds.

Chart: 5 states and 8 transitions from 5 model states.
5 work, 0 break a rule.

No rule is broken.

The spec draws upload.mmd back unchanged.

Wrote chart.mmd, stories.md, summary.json in Upload-statechart.
`,
  );
  assert.equal(r.stderr, "");
});

test("TLC reads a label with a guarded and an unguarded move in one region", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "switch.mmd"), switchLamp);
  const r = node("statechart.mjs", ["from-chart", "switch.mmd"], dir);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(r.stdout, /\nThe spec draws switch\.mmd back unchanged\.\n/);
});
