#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { checkTlcOutput, findTlc, parseDot } from "./lib.mjs";
import { draw } from "./statechart-draw.mjs";
import { HELP, USAGE, more, usage } from "./statechart-help.mjs";
import { SCAFFOLD } from "./statechart-scaffold.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));


class CannotFinish extends Error {}
class TlcStopped extends CannotFinish {}

const COMMANDS = {
  "from-spec": {
    flags: ["--map", "--fixed", "--against", "--label", "--expect-broken", "--title", "--out"],
    run: fromSpec,
  },
  "from-chart": { flags: ["--module", "--expect-broken", "--title", "--out"], run: fromChart },
};

function parseArgs([command, ...rest]) {
  if (command === "-h" || command === "--help") return { help: HELP[""] };
  if (!Object.hasOwn(COMMANDS, command))
    throw new CannotFinish(`${usage(Object.values(USAGE))}\n${more()}`);
  const flags = { "expect-broken": new Set() };
  let input;
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a === "-h" || a === "--help") return { help: HELP[command] };
    if (a === "--png") flags.png = true;
    else if (COMMANDS[command].flags.includes(a)) {
      if (i + 1 === rest.length) throw new CannotFinish(`${a} needs a value. ${more(command)}`);
      const name = a.slice(2);
      if (flags[name] instanceof Set) for (const v of rest[++i].split(",")) flags[name].add(v);
      else flags[name] = rest[++i];
    } else if (!a.startsWith("-") && input === undefined) input = a;
    else throw new CannotFinish(`unknown argument ${a}. ${more(command)}`);
  }
  if (input === undefined) throw new CannotFinish(`${usage([USAGE[command]])}\n${more(command)}`);
  return { command, input, flags };
}

const rel = (file) => path.relative(process.cwd(), file) || ".";
const cfgOf = (spec) => spec.replace(/\.tla$/, ".cfg");

function findTools() {
  try {
    return findTlc();
  } catch (e) {
    throw new CannotFinish(e.message);
  }
}

function script(name, scriptArgs, about, { okExits = [0] } = {}) {
  const r = spawnSync(process.execPath, [path.join(here, name), ...scriptArgs], {
    encoding: "utf8",
  });
  if (r.error) throw new CannotFinish(`cannot run ${name}: ${r.error.message}`);
  if (okExits.includes(r.status)) return r;
  const thrown = r.stderr.match(/^Error: (.*)$/m)?.[1];
  throw new CannotFinish(thrown ? `${rel(about)}: ${thrown}` : r.stderr.trim());
}

const KEYWORD =
  /^(SPECIFICATION|INIT|NEXT|CONSTANTS?|INVARIANTS?|PROPERTY|PROPERTIES|SYMMETRY|VIEW|CONSTRAINTS?|ACTION_CONSTRAINTS?|CHECK_DEADLOCK|POSTCONDITION|ALIAS)$/;

function splitRules(cfg) {
  const words = cfg
    .replace(/\(\*[^]*?\*\)/g, " ")
    .replace(/\\\*.*/g, " ")
    .split(/\s+/)
    .filter(Boolean);
  const kept = [];
  const rules = [];
  let section = "";
  for (const w of words) {
    if (KEYWORD.test(w)) section = w;
    if (!/^INVARIANTS?$/.test(section)) kept.push(KEYWORD.test(w) && kept.length ? `\n${w}` : w);
    else if (w !== section && !rules.includes(w)) rules.push(w);
  }
  return { cfgWithoutRules: `${kept.join(" ")}\n`, rules };
}

function tlc(tools, spec, cfg, base, dump) {
  fs.writeFileSync(`${base}.cfg`, cfg);
  const metadir = fs.mkdtempSync(path.join(os.tmpdir(), "tlc-"));
  // TLC writes the standard modules, such as Naturals.tla, to java.io.tmpdir under fixed names,
  // so runs that share that folder can read a module while another run rewrites it.
  const javaTmp = path.join(metadir, "tmp");
  fs.mkdirSync(javaTmp);
  // -deadlock: a UI at rest has nothing left to do, which TLC would report as a deadlock.
  const r = spawnSync(
    tools.java,
    [
      `-Djava.io.tmpdir=${javaTmp}`,
      "-cp",
      tools.jar,
      "tlc2.TLC",
      "-metadir",
      metadir,
      "-deadlock",
      "-continue",
      ...(dump ? ["-dump", "dot,actionlabels", path.resolve(dump)] : []),
      "-config",
      path.resolve(`${base}.cfg`),
      path.basename(spec),
    ],
    { cwd: path.dirname(path.resolve(spec)), encoding: "utf8", maxBuffer: 1 << 30 },
  );
  fs.rmSync(metadir, { recursive: true, force: true });
  if (r.error) throw new CannotFinish(`cannot run TLC: ${r.error.message}`);
  fs.writeFileSync(`${base}.out`, r.stdout);
  try {
    checkTlcOutput(r.stdout, `${base}.out`);
  } catch (e) {
    throw new TlcStopped(e.message);
  }
  return r.stdout;
}

function warnUnnamedSteps(spec, cfg, dot) {
  const text = fs
    .readFileSync(spec, "utf8")
    .replace(/\(\*[^]*?\*\)/g, " ")
    .replace(/\\\*.*/g, " ");
  const specName = /^SPECIFICATION\s+(\w+)/m.exec(cfg)?.[1];
  const specBody = specName && new RegExp(`^${specName}\\s*==(.*(\\n[ \\t]+.*)*)`, "m").exec(text);
  const next =
    /^NEXT\s+(\w+)/m.exec(cfg)?.[1] ?? /\[\]\s*\[\s*(\w+)\s*\]_/.exec(specBody?.[1] ?? text)?.[1];
  const graph = parseDot(fs.readFileSync(dot, "utf8"));
  const unnamed = [...graph.edges, ...graph.loops].filter((e) => e.action === next).length;
  if (unnamed > 0)
    console.error(
      `${rel(spec)}: ${unnamed} ${unnamed === 1 ? "step has" : "steps have"} the name ${next}, the whole next-state action, because TLC names a step after the innermost named action that takes it. If the reader must tell these steps apart, give each part of ${next} its own name, as in Pay == ... and ${next} == Pay \\/ Charge.`,
    );
}

function readModel(spec, cfgFile) {
  if (!fs.existsSync(spec)) throw new CannotFinish(`${rel(spec)} does not exist`);
  if (!fs.existsSync(cfgFile))
    throw new CannotFinish(
      `${rel(cfgFile)} does not exist. It needs SPECIFICATION and one INVARIANT line per rule.`,
    );
  return { spec, cfgFile, ...splitRules(fs.readFileSync(cfgFile, "utf8")) };
}

function readInput(spec, expected) {
  const model = readModel(spec, cfgOf(spec));
  const unknown = [...expected].filter((r) => !model.rules.includes(r));
  if (unknown.length)
    throw new CannotFinish(
      `--expect-broken ${unknown.join(", ")}: not a rule in ${rel(model.cfgFile)}, whose rules are ${model.rules.join(", ") || "none"}.`,
    );
  return model;
}

function check(tools, { spec, cfgFile, cfgWithoutRules, rules }, work, expected) {
  const name = path.basename(spec, ".tla");
  const tlcDir = path.join(work, "tlc");
  const dot = path.join(tlcDir, `${name}.dot`);
  tlc(tools, spec, cfgWithoutRules, path.join(tlcDir, name), dot);
  warnUnnamedSteps(spec, cfgWithoutRules, dot);
  console.log(`TLC on ${path.basename(spec)}:`);
  if (rules.length === 0)
    console.log(`  ${path.basename(cfgFile)} has no INVARIANT, so no rule is checked.`);
  // With -continue TLC reports every bad state. The CONSTRAINT stops each path at its first bad
  // state, so a rule that stays broken reports only the step that broke it, not every later state.
  const traces = rules.map((rule) => {
    const file = path.join(tlcDir, `${name}-${rule}`);
    const cfg = `${cfgWithoutRules}INVARIANT ${rule}\nCONSTRAINT ${rule}\n`;
    const broken = /^Error: Invariant /m.test(tlc(tools, spec, cfg, file));
    console.log(
      `  ${rule} ${broken ? (expected.has(rule) ? "is broken (expected)" : "is broken") : "holds"}.`,
    );
    return { file: `${file}.out`, rule, broken };
  });
  return { spec, dot, traces, broken: traces.some((t) => t.broken) };
}

function rulesAsExpected(now, other, expected) {
  const brokenIn = (m) => (m?.traces ?? []).filter((t) => t.broken).map((t) => t.rule);
  if (expected.size === 0) return !now.broken && !other?.broken;
  const unexpected = [...new Set([...brokenIn(now), ...brokenIn(other)])].filter(
    (r) => !expected.has(r),
  );
  const holds = [...expected].filter((r) => !brokenIn(now).includes(r));
  if (unexpected.length) console.log(`\nBroken but not expected: ${unexpected.join(", ")}.`);
  if (holds.length) console.log(`\nExpected to break but holds: ${holds.join(", ")}.`);
  if (!unexpected.length && !holds.length)
    console.log(`\nBroken as expected: ${[...expected].join(", ")}.`);
  return !unexpected.length && !holds.length;
}

function render(charts, shown) {
  const pngs = [];
  for (const chart of charts) {
    const png = chart.replace(/\.mmd$/, ".png");
    const r = spawnSync(
      "npx",
      ["-y", "@mermaid-js/mermaid-cli", "-i", chart, "-o", png, "-s", "2"],
      {
        encoding: "utf8",
      },
    );
    if (r.status === 0) pngs.push(png);
    else
      console.error(
        `could not render ${shown(chart)}: ${(r.stderr || r.error?.message || "").trim()}`,
      );
  }
  return pngs;
}

function finish({ work, out, inputs }, { files, charts }, ok, png) {
  const pngs = png ? render(charts, published(work, out)) : [];
  publish(work, out, inputs);
  const written = [...charts, ...pngs, files.stories, files.summary]
    .map((f) => path.basename(f))
    .join(", ");
  console.log(`\nWrote ${written} in ${rel(out)}.`);
  if (png && pngs.length < charts.length) return 2;
  return ok ? 0 : 1;
}

const published = (work, out) => (file) => rel(path.join(out, path.relative(work, file)));

const OWN =
  /^((chart|bug-\d+(-developer|-layered)?)\.(mmd|png)|stories\.md|summary\.json|tlc|\.DS_Store)$/;

function foreign(dir) {
  try {
    return fs
      .readdirSync(dir)
      .filter((f) => !OWN.test(f))
      .sort();
  } catch (e) {
    if (e.code === "ENOENT") return [];
    throw new CannotFinish(`cannot use ${rel(dir)} as the output folder: ${e.message}`);
  }
}

function refuseForeign(out, files = foreign(out)) {
  const [first, ...others] = files;
  if (first)
    throw new CannotFinish(
      `${rel(out)} has ${others.length ? `${others.length + 1} files that this command did not write, such as ${first}` : `a file that this command did not write: ${first}`}. A run puts its files in place of the whole output folder, so pass --out with a new folder.`,
    );
}

function outDir(flagged, input, name) {
  const out = flagged ?? path.join(path.dirname(input), `${name}-statechart`);
  refuseForeign(out);
  return out;
}

const fingerprint = (file) => {
  try {
    const { ino, ctimeNs } = fs.statSync(file, { bigint: true });
    return `${ino} ${ctimeNs} ${fs.readFileSync(file, "base64")}`;
  } catch {
    return null;
  }
};

function snapshot(files, inputs = new Map()) {
  for (const f of files) if (f && !inputs.has(f)) inputs.set(f, fingerprint(f));
  return inputs;
}

async function inWorkFolder(body) {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "statechart-"));
  fs.mkdirSync(path.join(work, "tlc"));
  let keep = false;
  try {
    return await body(work);
  } catch (e) {
    keep = e instanceof TlcStopped;
    throw e;
  } finally {
    if (!keep) fs.rmSync(work, { recursive: true, force: true });
  }
}

const moved = (from, to, ...missed) => {
  try {
    fs.renameSync(from, to);
    return true;
  } catch (e) {
    if (missed.includes(e.code)) return false;
    throw e;
  }
};

function publish(work, out, inputs) {
  const parent = path.dirname(path.resolve(out));
  fs.mkdirSync(parent, { recursive: true });
  const next = fs.mkdtempSync(path.join(parent, `.${path.basename(out)}-`));
  const old = `${next}-old`;
  let aside = false;
  try {
    fs.cpSync(work, next, { recursive: true });
    const changed = [...inputs].find(([f, was]) => fingerprint(f) !== was)?.[0];
    if (changed)
      throw new CannotFinish(
        `${rel(changed)} changed while this run read it, so the run left ${rel(out)} as it was. Run the command again.`,
      );
    refuseForeign(out);
    while (!moved(next, out, "ENOTEMPTY", "EEXIST")) {
      if (aside) {
        refuseForeign(out);
        fs.rmSync(old, { recursive: true, force: true });
        aside = false;
      }
      aside = moved(out, old, "ENOENT");
      if (aside) refuseForeign(out, foreign(old));
    }
  } catch (e) {
    const back = !aside || putBack(old, out);
    fs.rmSync(next, { recursive: true, force: true });
    const why = e instanceof CannotFinish ? e.message : `cannot replace ${rel(out)}: ${e.message}.`;
    if (!back)
      throw new CannotFinish(
        `${why} This run moved the previous ${rel(out)} to ${rel(old)} and could not put it back.`,
      );
    throw e instanceof CannotFinish
      ? e
      : new CannotFinish(`${why} The run left ${rel(out)} as it was.`);
  }
  if (aside) fs.rmSync(old, { recursive: true, force: true });
}

function putBack(old, out) {
  try {
    return moved(old, out, "ENOTEMPTY", "EEXIST");
  } catch {
    return false;
  }
}

function secondModel(input, { fixed, against, label }) {
  if (fixed && against)
    throw new CannotFinish(`use --fixed or --against, not both. ${more("from-spec")}`);
  if (!fixed && !against) {
    if (label === undefined) return null;
    throw new CannotFinish(
      `--label names the --fixed or --against model; it needs one of them. ${more("from-spec")}`,
    );
  }
  const [role, spec] = fixed ? ["fixed", fixed] : ["against", against];
  const name = path.basename(input, ".tla");
  // TLC's output files are named after the spec, so a second model with the same name overwrites them.
  if (path.basename(spec, ".tla") === name)
    throw new CannotFinish(
      `${rel(spec)} needs its own file and module name, such as ${name}${fixed ? "Fixed" : "Agreed"}.tla.`,
    );
  const cfg = fs.existsSync(cfgOf(spec)) ? cfgOf(spec) : cfgOf(input);
  return { role, label, model: readModel(spec, cfg) };
}

async function fromSpec(input, { "expect-broken": expected, ...flags }) {
  const name = path.basename(input, ".tla");
  const map = flags.map ?? path.join(path.dirname(input), `${name}.map.mjs`);
  const secondSpec = flags.fixed ?? flags.against;
  const inputs = snapshot([input, cfgOf(input), map, secondSpec, secondSpec && cfgOf(secondSpec)]);
  const second = secondModel(input, flags);
  const tools = findTools();
  const model = readInput(input, expected);
  const out = outDir(flags.out, input, name);
  return inWorkFolder(async (work) => {
    const now = check(tools, model, work, expected);
    if (!fs.existsSync(map)) {
      fs.writeFileSync(map, SCAFFOLD(name, parseDot(fs.readFileSync(now.dot, "utf8"))));
      throw new CannotFinish(
        `\nWrote ${rel(map)}. Fill in its labels, then run this command again.`,
      );
    }
    const other = second && {
      role: second.role,
      label: second.label,
      ...check(tools, second.model, work, expected),
    };
    const drawn = await draw({ now, other, map, work, out, title: flags.title }, { script, rel, published });
    return finish({ work, out, inputs }, drawn, rulesAsExpected(now, other, expected), flags.png);
  });
}

async function fromChart(input, { "expect-broken": expected, ...flags }) {
  const name =
    flags.module ??
    path
      .basename(input, path.extname(input))
      .replace(/(^|[^A-Za-z0-9]+)([A-Za-z0-9])/g, (_, __, c) => c.toUpperCase());
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(name))
    throw new CannotFinish(`cannot make a TLA+ module name from ${input}; add --module NAME`);
  const spec = path.join(path.dirname(input), `${name}.tla`);
  const map = spec.replace(/\.tla$/, ".map.mjs");
  const inputs = snapshot([input]);
  if (fs.existsSync(spec)) {
    console.log(`Kept ${rel(spec)}. Delete it to write the spec again from ${rel(input)}.`);
  } else {
    script("chart-to-tla.mjs", [input, "--module", name], input);
    console.log(`Wrote ${name}.tla, ${name}.cfg, and ${name}.map.mjs from ${rel(input)}.`);
  }
  snapshot([spec, cfgOf(spec), map], inputs);
  const tools = findTools();
  const model = readInput(spec, expected);
  const out = outDir(flags.out, input, name);
  return inWorkFolder(async (work) => {
    const now = check(tools, model, work, expected);
    const drawn = await draw({ now, map, work, out, title: flags.title, comparing: true }, { script, rel, published });
    const compared = script("compare-charts.mjs", [input, drawn.files.overview], input, {
      okExits: [0, 1],
    });
    if (compared.status === 0) console.log(`\nThe spec draws ${rel(input)} back unchanged.`);
    else
      console.log(
        `\nThe spec does not draw ${rel(input)}:\n${compared.stdout.trimEnd().replace(/^/gm, "  ")}`,
      );
    return finish(
      { work, out, inputs },
      drawn,
      rulesAsExpected(now, null, expected) && compared.status === 0,
      flags.png,
    );
  });
}

try {
  const { help, command, input, flags } = parseArgs(process.argv.slice(2));
  if (help) {
    console.log(help);
    process.exit(0);
  }
  process.exit(await COMMANDS[command].run(input, flags));
} catch (e) {
  if (!(e instanceof CannotFinish)) throw e;
  console.error(e.message);
  process.exit(2);
}
