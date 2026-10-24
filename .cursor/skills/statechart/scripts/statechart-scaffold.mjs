export const SCAFFOLD = (name, graph) => {
  const vars = Object.keys([...graph.nodes.values()][0]?.vars ?? {});
  const actions = [...new Set([...graph.edges, ...graph.loops].map((e) => e.action))].sort();
  return `// Chart labels for ${name}, for statechart.mjs. Write labels in plain words, not variable or action names.
// v, before, and after map each variable to its value. Strings, numbers, and booleans keep their kind.
// Sequences, tuples, and sets become arrays, indexed from 0. Records and functions become objects.
// Variables: ${vars.join(", ")}.

// The actions the reader takes. facts.settled is true when only these are enabled, and the overview
// keeps the shortest path to each settled state, plus every bug path.
export const readerActions = [];

// The label for one model state. facts.enabled is the set of actions the state enables,
// including steps that change no variable. Write it as "context: progress", such as
// "Offline: upload queued": the chart puts the states of one context in one box.
// Do not claim a result that a pending step can still change, such as "upload failed" while a
// retry is still queued.
export function state(v, facts) {
	return JSON.stringify(v);
}

// The names of the two parallel regions, when the overview draws them: contexts, then progress.
// export const regionNames = ["Network", "What happened to the file"];

// The group of one model state, in words the reader sees, such as "Upload done". The chart fills
// the states of one group with one color, and the legend names the groups. TLC still decides
// which states break a rule, and draws them with a thick red border on top of the group color.
// groupColors gives a group a light color. Groups without one take a palette color.
// export function group(v, facts) {}
// export const groupColors = { "Upload done": "#d1f2eb" };

// The label for one step. A step that leaves the reader in the same state is not drawn,
// unless the reader takes it on a bug path. "" draws no label, and a numbered bug step shows the action.
const STEPS = {
${actions.map((a) => `\t${a}: ${JSON.stringify(a)},`).join("\n")}
};
export function step(action, before, after) {
	return STEPS[action] ?? action;
}

// When the step can happen, in plain words, such as "offline or disk full". The chart shows
// "step [words]". "" adds nothing.
// export function guard(action, before, after) {}

// For a timer step, how many seconds the code waits, from the constant in the code. The chart
// shows "after N s, step". Return nothing for other steps.
// export function timer(action, before, after) {}

// Why a bad state is bad, in words a product manager reads, such as "the laptop went offline, and
// the app drops an upload it cannot send". No variable, function, or event names.
// Counterexamples that break one rule with one cause are one bug, so two bugs that end on the
// same screen stay apart only if their causes differ. Return null to group by the end state.
// export function cause(v, facts, invariant) {}

// The developer's words for one model state. With it, each bug is also drawn through these states.
// export function detail(v, facts) {}

// The legend's words for each status, in place of the defaults. Group entries keep their names.
// export const legend = { works: "Works on main", wrong: "Wrong on main", fixed: "Fixed in the open PR" };
`;
};

