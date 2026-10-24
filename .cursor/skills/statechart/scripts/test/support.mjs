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

export const here = dirname(fileURLToPath(import.meta.url));

export const scripts = dirname(here);

export const fixture = (name) => readFileSync(join(here, name), "utf8");

export const edges = (r) => r.transitions.map((t) => `${t.from} -> ${t.to} : ${t.label}`).sort();

export const node = (script, args, cwd, env = {}) =>
  spawnSync(process.execPath, [join(scripts, script), ...args], {
    cwd,
    encoding: "utf8",
    env: { ...process.env, ...env },
    timeout: 120_000,
  });

export const done = "Model checking completed. No error has been found.\n";

export const evaluationError = `Error: Invariant NoLost is violated.
Error: The behavior up to this point is:
State 1: <Initial predicate>
s = "Idle"

State 2: <Lose line 4, col 9 to line 4, col 33 of module F>
s = "Lost"

Error: TLC threw an unexpected exception.
This was probably caused by an error in the spec or model.

Error: The behavior up to this point is:
State 1: <Initial predicate>
s = "Idle"

State 2: <Save line 5, col 9 to line 5, col 35 of module F>
s = "Saving"

3 states generated, 3 distinct states found, 0 states left on queue.
`;

export const door = `stateDiagram-v2
  state Door {
    [*] --> Locked
    Locked --> Unlocked : tap unlock
    Unlocked --> Locked : tap lock
    --
    [*] --> Closed
    Closed --> Open : open the door
    Open --> Closed : close the door
  }
  [*] --> Door`;

export const flatDoor = (extra = []) =>
  [
    "stateDiagram-v2",
    '  state "Locked | Closed" as L_C',
    '  state "Locked | Open" as L_O',
    '  state "Unlocked | Closed" as U_C',
    '  state "Unlocked | Open" as U_O',
    "  [*] --> L_C",
    "  L_C --> U_C : tap unlock",
    "  U_C --> L_C : tap lock",
    "  L_O --> U_O : tap unlock",
    "  L_C --> L_O : open the door",
    "  L_O --> L_C : close the door",
    "  U_C --> U_O : open the door",
    "  U_O --> U_C : close the door",
    ...extra,
  ].join("\n");

export const lamp = `stateDiagram-v2
  state "Lamp" as lamp {
    state "Power" as power {
      [*] --> Off
      Off --> On : flip the switch
      On --> Off : flip the switch
    }
    --
    state "Bulb" as bulb {
      [*] --> Dark
      Dark --> Lit : warm up [when the<br/>power is on]
      %% when On
      Lit --> Dark : cool down [when the power is off]
      %% when not On
    }
  }
  %% never LitWhileOff: Off & Lit -- The bulb is never lit while the power is off.
`;

export const switchLamp = `stateDiagram-v2
  state "Lamp" as lamp {
    state "Power" as power {
      [*] --> Off
      Off --> On : flip the switch
      On --> Off : flip the switch
    }
    --
    state "Bulb" as bulb {
      [*] --> Dark
      Dark --> Lit : flip the switch [when the power is off]
      %% when Off
      Lit --> Dark : flip the switch
    }
  }
`;

export const NO_TLC = `Cannot find TLC. Download tla2tools.jar from a TLA+ release:
  https://github.com/tlaplus/tlaplus/releases
Then set TLA2TOOLS to the path of tla2tools.jar, and JAVA to a java binary (Java 11 or later).
`;

export const FROM_SPEC_USAGE =
  "node statechart.mjs from-spec SPEC.tla [--fixed FIXED.tla | --against AGREED.tla] [--label TEXT] [--map FILE] [--expect-broken RULE]... [--title TEXT] [--out DIR] [--png]";

export const FROM_CHART_USAGE =
  "node statechart.mjs from-chart CHART.mmd [--module NAME] [--expect-broken RULE]... [--title TEXT] [--out DIR] [--png]";

export const noTlc = { TLA2TOOLS: "", JAVA: "" };

export const tools = (() => {
  try {
    return findTlc();
  } catch {
    return null;
  }
})();

export const needsTlc = { skip: tools ? false : "cannot find TLC" };

export function tlc(dir, name) {
  const r = spawnSync(
    tools.java,
    [
      "-cp",
      tools.jar,
      "tlc2.TLC",
      "-metadir",
      mkdtempSync(join(tmpdir(), "tlc-")),
      "-deadlock",
      "-continue",
      "-dump",
      "dot,actionlabels",
      `${name}.dot`,
      "-config",
      `${name}.cfg`,
      `${name}.tla`,
    ],
    { cwd: dir, encoding: "utf8" },
  );
  writeFileSync(join(dir, `${name}.out`), r.stdout);
  return r;
}

export const syncStory = `## 1. Offline | Synced

Rule broken: You never see "Synced" while you are offline.
This is the only way to get here in the model.

0. Start: Online | Synced
1. The network drops. Now: Offline | Waiting to sync
2. The server confirms. Now: Offline | Synced
`;

export const pay = (name, charge) => `---- MODULE ${name} ----
EXTENDS Naturals
VARIABLES screen, charges
vars == <<screen, charges>>
Init == screen = "Cart" /\\ charges = 0
Pay == screen = "Cart" /\\ screen' = "Paying" /\\ UNCHANGED charges
Charge == ${charge}
Refund == charges = 2 /\\ charges' = 1 /\\ screen' = "Refunded"
Next == Pay \\/ Charge \\/ Refund
Spec == Init /\\ [][Next]_vars
NoDoubleCharge == charges <= 1
====
`;

export const payMap = `export const readerActions = ["Pay"];
export const state = (v) => v.screen + ["", ", charged", ", charged twice"][v.charges];
export const step = (action) => ({ Pay: "you pay", Charge: "the bank charges you", Refund: "the bank refunds you" })[action] ?? "";
export const cause = () => "each charge request charges again";
`;

export const edit = (name, fixed) => `---- MODULE ${name} ----
VARIABLES s, flashed
vars == <<s, flashed>>
Init == s = "Idle" /\\ flashed = FALSE
Tap == s = "Idle" /\\ s' = "Saving" /\\ UNCHANGED flashed
Lose == s = "Saving" /\\ s' = "Lost edit" /\\ UNCHANGED flashed
Flash == s = "Saving" /\\ s' = "Flash" /\\ flashed' = ${fixed ? "TRUE" : "FALSE"}
Back == s \\in {"Lost edit", "Flash"} /\\ s' = "Idle" /\\ flashed' = FALSE
Next == Tap \\/ Flash \\/ Back${fixed ? "" : " \\/ Lose"}
Spec == Init /\\ [][Next]_vars
NoLostEdit == s # "Lost edit" /\\ ~(s = "Flash" /\\ flashed)
====
`;

export function flatEdges(mmd) {
  const names = new Map();
  const members = new Map();
  let box = null;
  for (const line of mmd.split("\n")) {
    const opens = /^ {2}state "([^"]+)" as (g\d+) \{$/.exec(line);
    const state = /^ +state "([^"]+)" as (s\d+)$/.exec(line);
    const said = (s) => s.replaceAll("<br/>", " ");
    if (opens) {
      box = { id: opens[2], name: said(opens[1]) };
      members.set(box.id, []);
    } else if (line === "  }") box = null;
    else if (state) {
      names.set(state[2], box ? `${box.name}: ${said(state[1])}` : said(state[1]));
      if (box) members.get(box.id).push(state[2]);
    }
  }
  return [...mmd.matchAll(/^ {2}([gs]\d+) --> (s\d+) : (.*)$/gm)]
    .flatMap(([, from, to, label]) =>
      (members.get(from) ?? [from]).map((f) => `${names.get(f)} --> ${names.get(to)} : ${label}`),
    )
    .sort();
}

export const save = (name, code) => `---- MODULE ${name} ----
VARIABLES screen, note${code ? ", retries" : ""}
vars == <<screen, note${code ? ", retries" : ""}>>
Init == screen = "Editing" /\\ note = [text |-> "draft"${code ? `, rev |-> 0] /\\ retries = 0` : "]"}
Save == screen = "Editing" /\\ screen' = "Saving" /\\ UNCHANGED <<note${code ? ", retries" : ""}>>
Confirm == screen = "Saving" /\\ screen' = "Saved" /\\ note' = [text |-> "stored"${code ? `, rev |-> 1] /\\ UNCHANGED retries` : "]"}
Edit == screen = "Saved" /\\ screen' = "Editing" /\\ note' = [note EXCEPT !.text = "draft"]${code ? " /\\ retries' = 0" : ""}
${
  code
    ? `Retry == screen = "Saving" /\\ retries = 0 /\\ retries' = 1 /\\ UNCHANGED <<screen, note>>
TimeOut == screen = "Saving" /\\ retries = 1 /\\ screen' = "Saved" /\\ UNCHANGED <<note, retries>>
Next == Save \\/ Retry \\/ Confirm \\/ TimeOut \\/ Edit`
    : "Next == Save \\/ Confirm \\/ Edit"
}
Spec == Init /\\ [][Next]_vars
TypeOK == screen \\in {"Editing", "Saving", "Saved"}
\\* You never see "Saved" while the note is still a draft.
NoFalseSaved == ~(screen = "Saved" /\\ note.text = "draft")
====
`;

export const doorSpec = `---- MODULE Door ----
VARIABLES where, reply
vars == <<where, reply>>
Init == where = "Open" /\\ reply = "none"
Ask == reply = "none" /\\ reply' = "pending" /\\ UNCHANGED where
Answer == where = "Open" /\\ reply = "pending" /\\ reply' = "shown" /\\ UNCHANGED where
Drop == where = "Closed" /\\ reply = "pending" /\\ reply' = "lost" /\\ UNCHANGED where
Close == where = "Open" /\\ where' = "Closed" /\\ UNCHANGED reply
Reopen == where = "Closed" /\\ where' = "Open" /\\ (reply' = reply \\/ (reply = "pending" /\\ reply' = "shown"))
Next == Ask \\/ Answer \\/ Drop \\/ Close \\/ Reopen
Spec == Init /\\ [][Next]_vars
NoLostReply == reply # "lost"
NoShownWhileClosed == ~(where = "Closed" /\\ reply = "shown")
====
`;

export const doorMap = `const W = { Open: "Window open", Closed: "Window closed" };
const R = { none: "no question", pending: "reply on its way", shown: "reply shown", lost: "reply lost" };
export const regionNames = ["Where you are", "Your reply"];
export const state = (v) => \`\${W[v.where]}: \${R[v.reply]}\`;
export const step = (a) => ({ Ask: "you ask", Answer: "the reply arrives", Drop: "the app drops the reply", Close: "you close the window", Reopen: "you open the window" })[a];
`;

export function runDoor(map) {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  writeFileSync(join(dir, "Door.tla"), doorSpec);
  writeFileSync(join(dir, "Door.map.mjs"), map);
  const out = join(dir, "Door-statechart");
  const read = (f) => readFileSync(join(out, f), "utf8").replaceAll("<br/>", " ");
  return (rule) => {
    writeFileSync(join(dir, "Door.cfg"), `SPECIFICATION Spec\nINVARIANT ${rule}\n`);
    const r = node("statechart.mjs", ["from-spec", "Door.tla", "--expect-broken", rule], dir);
    assert.equal(r.status, 0, r.stdout + r.stderr);
    const every = join(out, "tlc", "regions-all.mmd");
    return {
      stdout: r.stdout,
      chart: read("chart.mmd"),
      every: existsSync(every) ? read("tlc/regions-all.mmd") : null,
      bug: read("bug-1.mmd"),
      out,
    };
  };
}

export const groupMap = `${doorMap}export const group = (v) =>
  ({ none: "Nothing to show", pending: "Waiting", shown: "Reply shown", lost: "Reply shown" })[v.reply];
export const groupColors = { "Reply shown": "#d1f2eb", Waiting: null, "Never drawn": "#ffffff" };
`;

export const order = (name, note, charge) => `---- MODULE ${name} ----
EXTENDS Naturals
VARIABLES screen, charges, note
vars == <<screen, charges, note>>
Init == screen = "Cart" /\\ charges = 0 /\\ note = 0
Pay == screen = "Cart" /\\ screen' = "Paying" /\\ note' = ${note} /\\ UNCHANGED charges
Charge == screen = "Paying" /\\ charges < 2 /\\ ${charge}
Next == Pay \\/ Charge
Spec == Init /\\ [][Next]_vars
NoDoubleCharge == charges <= 1
====
`;

export const chargeAgain = "charges' = charges + 1 /\\ UNCHANGED <<screen, note>>";

export const chargeOnce = `IF charges = 0 THEN charges' = 1 /\\ UNCHANGED <<screen, note>> ELSE screen' = "Paid" /\\ UNCHANGED <<charges, note>>`;

export const chargeFirstOnly = "charges = 0 /\\ charges' = 1 /\\ UNCHANGED <<screen, note>>";

export const notify = (name, mutedArrive) => `---- MODULE ${name} ----
EXTENDS Naturals
VARIABLES screen, muted, banner, badge, missed, msgs, syncs
vars == <<screen, muted, banner, badge, missed, msgs, syncs>>
Init == screen = "Inbox" /\\ muted = FALSE /\\ banner = FALSE /\\ badge = FALSE
        /\\ missed = FALSE /\\ msgs = 0 /\\ syncs = 0
OpenThread == screen = "Inbox" /\\ screen' = "Thread" /\\ UNCHANGED <<muted, banner, badge, missed, msgs, syncs>>
OpenSettings == screen \\in {"Inbox", "Thread"} /\\ screen' = "Settings" /\\ UNCHANGED <<muted, banner, badge, missed, msgs, syncs>>
TapBack == screen \\in {"Thread", "Settings"} /\\ screen' = "Inbox" /\\ UNCHANGED <<muted, banner, badge, missed, msgs, syncs>>
Mute == screen = "Settings" /\\ ~muted /\\ muted' = TRUE /\\ UNCHANGED <<screen, banner, badge, missed, msgs, syncs>>
Refresh == syncs < 2 /\\ syncs' = syncs + 1 /\\ UNCHANGED <<screen, muted, banner, badge, missed, msgs>>
Arrive == msgs < syncs /\\ msgs' = msgs + 1
          /\\ (IF muted THEN ${mutedArrive} ELSE banner' = TRUE /\\ UNCHANGED <<badge, missed>>)
          /\\ UNCHANGED <<screen, muted, syncs>>
Next == OpenThread \\/ OpenSettings \\/ TapBack \\/ Mute \\/ Refresh \\/ Arrive
Spec == Init /\\ [][Next]_vars
NeverMissed == ~missed
NoBannerOnThread == ~(banner /\\ screen = "Thread")
====
`;

export const writeLamp = (dir) => {
  writeFileSync(
    join(dir, "Lamp.tla"),
    "---- MODULE Lamp ----\nVARIABLE on\nInit == on = FALSE\nOn == on' = TRUE\nOff == on' = FALSE\nSpec == Init /\\ [][On \\/ Off]_on\n====\n",
  );
  writeFileSync(join(dir, "Lamp.cfg"), "SPECIFICATION Spec\n");
  writeFileSync(
    join(dir, "Lamp.map.mjs"),
    'export const state = (v) => (v.on ? "On" : "Off");\nexport const step = () => "you flip the switch";\n',
  );
  return join(dir, "Lamp-statechart");
};

export const writeSlowPay = (dir, ticks, paid = "Paid") => {
  writeFileSync(
    join(dir, "Pay.tla"),
    `---- MODULE Pay ----
EXTENDS Naturals
VARIABLES screen, charges, ticks
vars == <<screen, charges, ticks>>
Init == screen = "Cart" /\\ charges = 0 /\\ ticks = 0
TapPay == screen = "Cart" /\\ screen' = "Paying" /\\ UNCHANGED <<charges, ticks>>
Charge == screen = "Paying" /\\ charges < 2 /\\ charges' = charges + 1 /\\ UNCHANGED <<screen, ticks>>
Done == screen = "Paying" /\\ charges > 0 /\\ screen' = "${paid}" /\\ UNCHANGED <<charges, ticks>>
Tick == ticks < ${ticks} /\\ ticks' = ticks + 1 /\\ UNCHANGED <<screen, charges>>
Spec == Init /\\ [][TapPay \\/ Charge \\/ Done \\/ Tick]_vars
ChargedAtMostTwice == charges <= 2
====
`,
  );
  writeFileSync(join(dir, "Pay.cfg"), "SPECIFICATION Spec\nINVARIANT ChargedAtMostTwice\n");
  writeFileSync(
    join(dir, "Pay.map.mjs"),
    'export const state = (v) => v.screen;\nexport const step = (a) => ({ TapPay: "you tap Pay", Charge: "the charge goes through", Done: "the receipt shows" })[a] ?? "";\n',
  );
  return join(dir, "Pay-statechart");
};

export const startRun = (dir, { wrap = [], env = {}, args = ["from-spec", "Pay.tla"] } = {}) => {
  const [command, ...rest] = [...wrap, process.execPath, join(scripts, "statechart.mjs"), ...args];
  const child = spawn(command, rest, {
    cwd: dir,
    env: { ...process.env, ...env },
    stdio: ["ignore", "ignore", "pipe"],
    detached: true,
  });
  let stderr = "";
  child.stderr.on("data", (d) => {
    stderr += d;
  });
  return {
    child,
    done: new Promise((done) => child.on("close", (status) => done({ status, stderr }))),
  };
};

export const until = async (ready) => {
  while (!ready()) await sleep(20);
};

export const ownTmp = (dir, name) => {
  const tmp = join(dir, name);
  mkdirSync(tmp);
  return tmp;
};

export const tlcStarted = (tmp) => readdirSync(tmp).some((f) => f.startsWith("tlc-"));

export const staged = (dir) => readdirSync(dir).filter((f) => f.startsWith("."));

export const changedMidRun = async ({ wrap = [], env = {} }) => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-"));
  const out = writeSlowPay(dir, 20000);
  const tmp = ownTmp(dir, "tmp-a");
  const first = startRun(dir, { wrap, env: { ...env, TMPDIR: tmp } });
  await until(() => tlcStarted(tmp));
  await sleep(500);
  writeSlowPay(dir, 20000, "Receipt");
  const second = startRun(dir, { wrap, env: { ...env, TMPDIR: ownTmp(dir, "tmp-b") } });
  const [paid, receipt] = await Promise.all([first.done, second.done]);
  assert.equal(receipt.status, 0, receipt.stderr);
  assert.equal(paid.status, 2, paid.stderr);
  assert.equal(
    paid.stderr,
    "Pay.tla changed while this run read it, so the run left Pay-statechart as it was. Run the command again.\n",
  );
  const chart = readFileSync(join(out, "chart.mmd"), "utf8");
  assert.match(chart, /Receipt/);
  assert.doesNotMatch(chart, /Paid/);
  assert.deepEqual(staged(dir), []);
};

export const unshare = ["unshare", "--user", "--map-root-user", "--pid", "--fork", "--mount-proc"];

export const hidePidNamespace = `#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
ssize_t readlink(const char *path, char *buf, size_t size) {
  static ssize_t (*real)(const char *, char *, size_t);
  if (!real) real = dlsym(RTLD_NEXT, "readlink");
  if (path && strcmp(path, "/proc/self/ns/pid") == 0) { errno = EIO; return -1; }
  return real(path, buf, size);
}
`;

export const hidingPreload = (() => {
  if (spawnSync(unshare[0], [...unshare.slice(1), "true"]).status !== 0) return null;
  const dir = mkdtempSync(join(tmpdir(), "statechart-preload-"));
  writeFileSync(join(dir, "hide.c"), hidePidNamespace);
  const so = join(dir, "hide.so");
  const cc = spawnSync("cc", ["-shared", "-fPIC", "-o", so, join(dir, "hide.c"), "-ldl"]);
  return cc.status === 0 ? so : null;
})();

export const failRenames = `#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
static size_t hits;
int rename(const char *from, const char *to) {
  static int (*real)(const char *, const char *);
  if (!real) real = dlsym(RTLD_NEXT, "rename");
  const char *base = strrchr(to, '/'), *fails = getenv("RENAME_FAILS");
  base = base ? base + 1 : to;
  if (fails && strcmp(base, "shared") == 0 && hits < strlen(fails)) {
    errno = fails[hits++] == 'N' ? ENOTEMPTY : EIO;
    return -1;
  }
  return real(from, to);
}
`;

export const failingRenames = (() => {
  const dir = mkdtempSync(join(tmpdir(), "statechart-preload-"));
  writeFileSync(join(dir, "rename.c"), failRenames);
  const so = join(dir, "rename.so");
  const cc = spawnSync("cc", ["-shared", "-fPIC", "-o", so, join(dir, "rename.c"), "-ldl"]);
  return cc.status === 0 ? so : null;
})();
