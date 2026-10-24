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
  "the mapping cannot hide a broken rule, and refuses a status name, a dark or bad color, or a group that is not a name",
  needsTlc,
  () => {
    const run = runDoor(groupMap)("NoLostReply");
    const tlcDir = join(run.out, "tlc");
    const chart = (map, ...extra) => {
      writeFileSync(join(tlcDir, "probe.map.mjs"), map);
      return node(
        "tlc-to-chart.mjs",
        [
          "--dot",
          "Door.dot",
          "--map",
          "probe.map.mjs",
          "--traces",
          "Door-NoLostReply.out",
          "--highlight",
          "0",
          ...extra,
        ],
        tlcDir,
      );
    };

    const hidden = chart(
      `${doorMap}export const group = () => "All good";\nexport const groupColors = { "All good": "#e9f7ef" };\n`,
      "--regions",
    );
    assert.equal(hidden.status, 0, hidden.stderr);
    const lines = hidden.stdout.split("\n");
    assert.ok(
      lines.includes(
        "  classDef group0Wrong fill:#e9f7ef,stroke:#c0392b,stroke-width:4px,color:#7b241c",
      ),
    );
    const legend = lines.indexOf('  state "Legend" as legend {');
    assert.deepEqual(lines.slice(legend, legend + 6), [
      '  state "Legend" as legend {',
      '    state "All good" as legendGroup0',
      '    state "Breaks a rule" as legendWrong',
      "  }",
      "  class legendGroup0 group0",
      "  class legendWrong plainWrong",
    ]);
    assert.ok(lines.includes("  class r1s1 group0Wrong"));
    assert.equal(lines.filter((l) => / group0Wrong$/.test(l)).length, 1);

    const coarse = chart(
      `const W = { Open: "Window open", Closed: "Window closed" };
export const state = (v) => W[v.where];
export const group = (v) => (v.reply === "shown" ? "Reply shown" : "Waiting");
`,
      "--summary",
      "coarse.json",
    );
    assert.equal(coarse.status, 0, coarse.stderr);
    assert.deepEqual(
      coarse.stdout.split("\n").filter((l) => /^ {2}(class|classDef) /.test(l)),
      [
        "  classDef plain fill:#f4f6f7,stroke:#566573,color:#1b2631",
        "  classDef plainWrong fill:#f4f6f7,stroke:#c0392b,stroke-width:4px,color:#7b241c",
        "  class legendWrong plainWrong",
        "  class s0 plainWrong",
        "  class s1 plain",
      ],
    );
    const summary = JSON.parse(readFileSync(join(tlcDir, "coarse.json"), "utf8"));
    assert.deepEqual(summary.chartGroups, []);
    assert.deepEqual(summary.mixedGroups, ["Window closed", "Window open"]);

    for (const [map, error] of [
      [
        `export const group = (v) => (v.reply === "lost" ? "Breaks a rule" : "Fine");`,
        /group "Breaks a rule" has the name of a status; TLC decides the status, so name the group for what the reader sees/,
      ],
      [`export const group = () => "fixed";`, /group "fixed" has the name of a status/],
      [
        `export const group = () => "All good";\nexport const groupColors = { "All good": "#123" };`,
        /groupColors\["All good"\] "#123" is too dark for the status borders to show on it/,
      ],
      [
        `export const group = () => "All good";\nexport const groupColors = { "All good": "red" };`,
        /groupColors\["All good"\] "red" is not "#rgb" or "#rrggbb"/,
      ],
      [
        `export const group = () => "All good";\nexport const groupColors = ["#ffffff"];`,
        /groupColors must be an object from a group name to a color such as #d6eaf8/,
      ],
      [`export const group = () => 1;`, /group\(\) must return a group name or nothing; got 1/],
    ]) {
      const r = chart(`${doorMap}${map}\n`, "--regions");
      assert.equal(r.status, 1, map);
      assert.equal(r.stdout, "", map);
      assert.match(r.stderr, error);
    }
  },
);

test(
  "the fix changes a bug only at the first step that the reader sees differently",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(join(dir, "Order.tla"), order("Order", 0, chargeAgain));
    writeFileSync(join(dir, "Order.cfg"), "SPECIFICATION Spec\nINVARIANT NoDoubleCharge\n");
    const withFix = (charge, map = payMap) => {
      writeFileSync(join(dir, "Order.map.mjs"), map);
      writeFileSync(join(dir, "OrderFixed.tla"), order("OrderFixed", 1, charge));
      const r = node(
        "statechart.mjs",
        ["from-spec", "Order.tla", "--fixed", "OrderFixed.tla"],
        dir,
      );
      assert.equal(r.status, 1, r.stderr);
      const chart = readFileSync(join(dir, "Order-statechart", "chart.mmd"), "utf8");
      return {
        story: readFileSync(join(dir, "Order-statechart", "stories.md"), "utf8"),
        fixEdges: parseMermaid(chart)
          .regions.Main.transitions.filter((t) => t.label.includes("with the fix"))
          .map((t) => `${t.from} --> ${t.to} : ${t.label}`),
      };
    };
    const hidden = withFix(chargeAgain);
    assert.deepEqual(hidden.fixEdges, []);
    assert.match(
      hidden.story,
      /^With the fix you see the same screens and steps, so the fix does not change this path\.$/m,
    );
    const once = withFix(chargeOnce);
    assert.deepEqual(once.fixEdges, [
      "Paying, charged --> Paid, charged : with the fix, the bank charges you",
    ]);
    assert.match(
      once.story,
      /^With the fix, step 3 \(the bank charges you\) takes you to: Paid, charged\.$/m,
    );
    const unlabeledMap = payMap.replace(
      /^export const state = .*$/m,
      "export const state = (v) => v.screen;",
    );
    const unseen = withFix(chargeOnce, unlabeledMap);
    assert.deepEqual(unseen.fixEdges, ["Paying --> Paid : with the fix, the bank charges you"]);
    assert.match(
      unseen.story,
      /^With the fix, after step 1, "the bank charges you" happens and takes you to: Paid\.$/m,
    );
    const blocked = withFix(chargeFirstOnly, unlabeledMap);
    assert.deepEqual(blocked.fixEdges, []);
    assert.match(
      blocked.story,
      /yet the rule holds, so the state labels do not show what the fix changes/,
    );
  },
);

test(
  "a step the reader does not see breaks the rule, and the fix shows it on another screen",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(
      join(dir, "Notify.tla"),
      notify("Notify", "missed' = TRUE /\\ UNCHANGED <<banner, badge>>"),
    );
    writeFileSync(
      join(dir, "NotifyBadge.tla"),
      notify("NotifyBadge", "badge' = TRUE /\\ UNCHANGED <<banner, missed>>"),
    );
    writeFileSync(
      join(dir, "Notify.cfg"),
      "SPECIFICATION Spec\nINVARIANT NeverMissed\nINVARIANT NoBannerOnThread\n",
    );
    writeFileSync(
      join(dir, "Notify.map.mjs"),
      `export const readerActions = ["OpenThread", "OpenSettings", "TapBack", "Mute", "Refresh"];
export const state = (v) => [v.screen, v.muted && "muted", v.banner && "banner", v.badge && "badge"].filter(Boolean).join(", ");
export const step = (a) => ({ OpenThread: "you open the thread", OpenSettings: "you open settings", TapBack: "you tap Back", Mute: "you mute alerts", Refresh: "you pull to refresh", Arrive: "a message arrives" })[a];
export const cause = () => null;
`,
    );
    const r = node(
      "statechart.mjs",
      ["from-spec", "Notify.tla", "--fixed", "NotifyBadge.tla", "--label", "the badge fix"],
      dir,
    );
    assert.equal(r.status, 1, r.stderr);
    const out = (f) => readFileSync(join(dir, "Notify-statechart", f), "utf8");
    const fixEdges = (f) =>
      parseMermaid(out(f))
        .regions.Main.transitions.filter((t) => t.label.includes("with the badge fix"))
        .map((t) => `${t.from} --> ${t.to} : ${t.label}`);
    const { classes } = JSON.parse(out("summary.json"));
    assert.deepEqual(
      classes.map((c) => [c.invariant, c.end, c.fix]),
      [
        ["NoBannerOnThread", "Thread, banner", "unchanged"],
        ["NeverMissed", "Settings, muted", "Settings, muted, badge"],
        ["NeverMissed", "Inbox, muted", "Inbox, muted, badge"],
        ["NeverMissed", "Settings, muted, banner", "Settings, muted, banner, badge"],
        ["NeverMissed", "Thread, muted", "Thread, muted, badge"],
        ["NoBannerOnThread", "Thread, muted, banner", "unchanged"],
        ["NeverMissed", "Inbox, muted, banner", "Inbox, muted, banner, badge"],
        ["NeverMissed", "Thread, muted, banner", "Thread, muted, banner, badge"],
        ["NoBannerOnThread", "Thread, muted, banner, badge", "new with the badge fix"],
      ],
    );
    const missed = classes.filter((c) => c.invariant === "NeverMissed");

    const story = out("stories.md");
    assert.doesNotMatch(story, /do not show what/);
    assert.match(
      story,
      /^With the badge fix, after step 3, "a message arrives" happens and takes you to: Settings, muted, badge\.$/m,
    );
    const settings = classes.find((c) => c.end === "Settings, muted");
    assert.deepEqual(fixEdges(`bug-${settings.n}.mmd`), [
      "Settings, muted --> Settings, muted, badge : with the badge fix, a message arrives",
    ]);
    const drawn = fixEdges("chart.mmd");
    assert.equal(new Set(drawn).size, drawn.length);
    for (const c of missed)
      assert.ok(
        drawn.includes(`${c.end} --> ${c.end}, badge : with the badge fix, a message arrives`),
        `bug ${c.n}`,
      );
  },
);

test(
  "each looping step on a bug path keeps its own label, a null cause groups bugs by end state, and the mapping names the key's colors",
  needsTlc,
  () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    writeFileSync(
      join(dir, "Browse.tla"),
      `---- MODULE Browse ----
EXTENDS Naturals
VARIABLES screen, looks, scrolled
vars == <<screen, looks, scrolled>>
Init == screen = "Cart" /\\ looks = 0 /\\ scrolled = FALSE
Look == screen = "Cart" /\\ looks < 3 /\\ looks' = looks + 1 /\\ UNCHANGED <<screen, scrolled>>
Scroll == screen = "Cart" /\\ looks = 1 /\\ ~scrolled /\\ scrolled' = TRUE /\\ UNCHANGED <<screen, looks>>
Pay == screen = "Cart" /\\ looks = 3 /\\ scrolled /\\ screen' = "Paying" /\\ UNCHANGED <<looks, scrolled>>
Fail == screen = "Paying" /\\ screen' = "Failed" /\\ UNCHANGED <<looks, scrolled>>
Hang == screen = "Paying" /\\ screen' = "Stuck" /\\ UNCHANGED <<looks, scrolled>>
Next == Look \\/ Scroll \\/ Pay \\/ Fail \\/ Hang
Spec == Init /\\ [][Next]_vars
NeverLost == screen \\notin {"Failed", "Stuck"}
====
`,
    );
    writeFileSync(join(dir, "Browse.cfg"), "SPECIFICATION Spec\nINVARIANT NeverLost\n");
    writeFileSync(
      join(dir, "Browse.map.mjs"),
      `export const readerActions = ["Look", "Scroll", "Pay"];
export const state = (v) => v.screen;
export const step = (a) => ({ Look: "you look", Scroll: "you scroll", Pay: "you pay", Fail: "the payment fails", Hang: "the payment hangs" })[a];
export const cause = () => null;
export const legend = { works: "Works on main", wrong: "Wrong on main" };
`,
    );
    const r = node("statechart.mjs", ["from-spec", "Browse.tla"], dir);
    assert.equal(r.status, 1, r.stderr);
    const out = (f) => readFileSync(join(dir, "Browse-statechart", f), "utf8");
    assert.deepEqual(
      JSON.parse(out("summary.json")).classes.map((c) => [c.end, c.cause]),
      [
        ["Failed", null],
        ["Stuck", null],
      ],
    );
    assert.doesNotMatch(out("stories.md"), /^Why:|null/m);
    const loops = (chart) => [...chart.matchAll(/^ {2}(s\d+) --> \1 : (.*)$/gm)].map((m) => m[2]);
    assert.deepEqual(loops(out("bug-1.mmd")), ["1. you look<br/>2. you scroll<br/>3, 4. you look"]);
    assert.deepEqual(loops(out("chart.mmd")), ["you look or you scroll"]);
    const chart = out("chart.mmd");
    assert.ok(chart.includes('state "Works on main" as legendWorks'));
    assert.ok(chart.includes('state "Wrong on main" as legendWrong'));
    assert.doesNotMatch(chart, /legendFixed/);
  },
);

test("a rule that stays broken reports only the step that broke it", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(
    join(dir, "Buzz.tla"),
    `---- MODULE Buzz ----
EXTENDS Naturals
VARIABLES x, y, buzzed
vars == <<x, y, buzzed>>
Init == x = 0 /\\ y = 0 /\\ buzzed = FALSE
IncX == x < 6 /\\ x' = x + 1 /\\ UNCHANGED <<y, buzzed>>
IncY == y < 6 /\\ y' = y + 1 /\\ UNCHANGED <<x, buzzed>>
Ring == x = 2 /\\ ~buzzed /\\ buzzed' = TRUE /\\ UNCHANGED <<x, y>>
Next == IncX \\/ IncY \\/ Ring
Spec == Init /\\ [][Next]_vars
NeverBuzzed == ~buzzed
====
`,
  );
  writeFileSync(join(dir, "Buzz.cfg"), "SPECIFICATION Spec\nINVARIANT NeverBuzzed\n");
  writeFileSync(
    join(dir, "Buzz.map.mjs"),
    'export const state = (v) => (v.buzzed ? "Buzzed" : "Quiet");\nexport const step = () => "time passes";\n',
  );
  const r = node("statechart.mjs", ["from-spec", "Buzz.tla"], dir);
  assert.equal(r.status, 1, r.stderr);
  const traces = parseTraces(
    readFileSync(join(dir, "Buzz-statechart", "tlc", "Buzz-NeverBuzzed.out"), "utf8"),
  );
  assert.equal(traces.length, 7);
  for (const t of traces)
    assert.equal(
      t.steps.findIndex((s) => s.vars.buzzed),
      t.steps.length - 1,
    );
});

test("from-spec warns when steps carry the name of the whole next-state action", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  const count = (next) => `---- MODULE Count ----
EXTENDS Naturals
VARIABLES x
Init == x = 0
Inc == x < 3 /\\ x' = x + 1
${next}
Spec == \\* not [][Inc]_x
        Init /\\ [][Next]_x
====
`;
  writeFileSync(join(dir, "Count.cfg"), "SPECIFICATION Spec\n");
  writeFileSync(join(dir, "Count.map.mjs"), "export const state = (v) => String(v.x);\n");
  writeFileSync(join(dir, "Count.tla"), count("Next == Inc \\/ (x = 3 /\\ x' = 0)"));
  const unnamed = node("statechart.mjs", ["from-spec", "Count.tla"], dir);
  assert.equal(unnamed.status, 0, unnamed.stderr);
  assert.match(
    unnamed.stderr,
    /^Count\.tla: 1 step has the name Next, the whole next-state action/,
  );
  writeFileSync(join(dir, "Count.tla"), count("Next == Inc"));
  const named = node("statechart.mjs", ["from-spec", "Count.tla"], dir);
  assert.equal(named.status, 0, named.stderr);
  assert.equal(named.stderr, "");
});

test("a rerun without --png removes the chart.png of an earlier run", needsTlc, () => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  const out = writeLamp(dir);
  mkdirSync(out);
  writeFileSync(join(out, "chart.png"), "");
  const r = node("statechart.mjs", ["from-spec", "Lamp.tla"], dir);
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(
    readdirSync(out).filter((f) => f.endsWith(".png")),
    [],
  );
});

test(
  "a run whose Node is killed mid-TLC leaves the output folder as it was, and a rerun charts its own spec",
  needsTlc,
  async () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    const out = writeSlowPay(dir, 60000);
    const tmp = ownTmp(dir, "tmp");
    const first = startRun(dir, { env: { TMPDIR: tmp } });
    await until(() => tlcStarted(tmp));
    await sleep(300);
    first.child.kill("SIGTERM");
    await first.done;
    assert.doesNotThrow(() => process.kill(-first.child.pid, 0), "TLC outlives its Node");
    assert.equal(existsSync(out), false);

    writeSlowPay(dir, 200, "Receipt");
    const second = node("statechart.mjs", ["from-spec", "Pay.tla"], dir);
    process.kill(-first.child.pid, "SIGKILL");
    assert.equal(second.status, 0, second.stderr);
    for (const file of ["chart.mmd", join("tlc", "Pay.dot")]) {
      const text = readFileSync(join(out, file), "utf8");
      assert.match(text, /Receipt/);
      assert.doesNotMatch(text, /Paid/);
    }
    assert.deepEqual(staged(dir), []);
  },
);

test(
  "a run whose spec changes while it reads it leaves the output folder, and the run that read the new spec charts it",
  needsTlc,
  () => changedMidRun({}),
);

test(
  "runs in PID namespaces that hide which namespace they are in chart only their own spec",
  {
    skip:
      needsTlc.skip ||
      (!hidingPreload && "cannot make a PID namespace, or cannot compile a readlink preload"),
  },
  () => changedMidRun({ wrap: unshare, env: { LD_PRELOAD: hidingPreload } }),
);

test(
  "a file that is put in the output folder during a run stays, and the run exits 2",
  needsTlc,
  async () => {
    const dir = mkdtempSync(join(tmpdir(), "statechart-"));
    const out = writeSlowPay(dir, 20000);
    const tmp = ownTmp(dir, "tmp");
    const run = startRun(dir, { env: { TMPDIR: tmp } });
    await until(() => tlcStarted(tmp));
    mkdirSync(out);
    writeFileSync(join(out, "notes.md"), "mine\n");
    const r = await run.done;
    assert.equal(r.status, 2);
    assert.equal(
      r.stderr,
      "Pay-statechart has a file that this command did not write: notes.md. A run puts its files in place of the whole output folder, so pass --out with a new folder.\n",
    );
    assert.deepEqual(readdirSync(out), ["notes.md"]);
    assert.deepEqual(staged(dir), []);
  },
);
