import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

export async function draw(spec, deps) {
  const { script, rel, published } = deps;
  const { now, other, map, work, out, title, comparing } = spec;
  const shown = published(work, out);
  const mapping = await import(pathToFileURL(path.resolve(map)).href);
  const from = ["--dot", now.dot, "--map", map, "--spec", now.spec];
  from.push(...now.traces.flatMap((t) => ["--traces", t.file]));
  if (other) {
    from.push(`--${other.role}-dot`, other.dot, "--spec", other.spec);
    from.push(...other.traces.flatMap((t) => [`--${other.role}-traces`, t.file]));
    if (other.label !== undefined) from.push("--label", other.label);
  }
  if (comparing) from.push("--full-labels", "--flat");
  else if (mapping.readerActions?.length) from.push("--cover");
  const titled = (suffix) => (title ? ["--title", `${title}${suffix}`] : []);

  const files = {
    overview: path.join(work, "chart.mmd"),
    stories: path.join(work, "stories.md"),
    summary: path.join(work, "summary.json"),
  };
  const proof = path.join(work, "tlc", "regions-proof.mmd");
  const everyArrow = path.join(work, "tlc", "regions-all.mmd");
  script(
    "tlc-to-chart.mjs",
    [
      ...from,
      ...(comparing ? [] : ["--regions", "--proof", proof, "--regions-all", everyArrow]),
      ...titled(""),
      "--highlight",
      "0",
      "--out",
      files.overview,
      "--story",
      files.stories,
      "--summary",
      files.summary,
    ],
    map,
  );
  const summary = JSON.parse(fs.readFileSync(files.summary, "utf8"));
  const charts = [files.overview];
  for (const c of summary.classes) {
    const views = typeof mapping.detail === "function" ? ["", "-developer", "-layered"] : [""];
    for (const view of views) {
      const file = path.join(work, `bug-${c.n}${view}.mmd`);
      const shape = [...(view ? ["--view", view.slice(1)] : []), "--path-only"];
      script(
        "tlc-to-chart.mjs",
        [...from, ...shape, ...titled(`, bug ${c.n}`), "--highlight", String(c.n), "--out", file],
        map,
      );
      charts.push(file);
    }
  }

  const { works, wrong, fixed: fixedCount } = summary.chartStatus;
  const L = summary.second?.label;
  console.log(
    `\nChart: ${summary.chartStates} states and ${summary.chartTransitions} transitions from ${summary.modelStates} model states.`,
  );
  const r = summary.regions;
  if (r?.drawn)
    console.log(
      `It has 2 parallel regions, of ${r.states[0]} and ${r.states[1]} states. Proof: their ${r.all} arrows together make exactly the ${r.flat.states} states and ${r.flat.transitions} labeled steps of ${shown(proof)}, and the ${r.transitions} drawn arrows make only steps among them. ${shown(everyArrow)} has all ${r.all} arrows.`,
    );
  else if (r) console.log(`It has no parallel regions, because ${r.why}.`);
  const breaks = `${wrong} ${wrong === 1 ? "breaks" : "break"} a rule`;
  console.log(
    other?.role === "fixed"
      ? `${works} work today, ${wrong} still wrong with ${L}, ${fixedCount} fixed or new with ${L}.\n`
      : other?.role === "against"
        ? `${works} work, ${breaks}, ${fixedCount} only in ${L}.\n`
        : `${works} work, ${breaks}.\n`,
  );
  if (summary.codeLike.length)
    console.log(
      `These labels or causes read like code. Write them in the reader's words in ${rel(map)}:\n${summary.codeLike.map((t) => `  ${t}`).join("\n")}\n`,
    );
  console.log(
    summary.classes.length
      ? fs.readFileSync(files.stories, "utf8").trimEnd()
      : "No rule is broken.",
  );
  return { files, charts };
}

