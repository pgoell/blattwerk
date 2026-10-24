import { FULL_LABELS } from "./mermaid.mjs";

export const USAGE = "Usage: node tlc-to-chart.mjs --dot FILE --map FILE [options]";
export const HELP = `${USAGE}

Collapses a TLC state graph onto the reader's states and writes a Mermaid stateDiagram-v2.
statechart.mjs runs it once for the overview and once for each bug chart.

  --dot FILE             The state graph from TLC -dump dot,actionlabels FILE, for the current code.
                         Required.
  --map FILE             The mapping module. Required. It exports state(vars, facts), and
                         optionally detail(vars, facts), step(action, before, after),
                         guard(action, before, after), timer(action, before, after),
                         cause(vars, facts, invariant), group(vars, facts), groupColors,
                         regionNames, readerActions, and legend. guard is when the step
                         can happen, in plain words. An edge reads "step [words]" when every
                         model step behind it has words. timer is how many seconds the code waits
                         before a timer step, and the step reads "after N s, step".
                         cause is the hidden reason a bad state is bad: counterexamples with the
                         same invariant and cause are one bug. When cause returns nothing, the
                         end state stands in for it. readerActions are the actions the
                         reader takes. group is the group of a state, below. legend, such as
                         { works: "Works on main" }, gives the legend's words for the works,
                         wrong, and fixed statuses.
                         facts.enabled is the set of actions the state enables. facts.settled is
                         true when only reader actions are enabled, so nothing else happens until
                         the reader acts.
  --traces FILE          TLC output that holds counterexamples. Repeat it. TLC -continue gives one
                         per bad state. It refuses a file from a TLC run that stopped early or hit
                         an error other than a broken rule.
  --fixed-dot FILE       The state graph of the model with the open fix. Each bug's steps replay
                         on it.
  --fixed-traces FILE    TLC output for the same invariants on the fixed model. Repeat it. It marks
                         states fixed or still wrong, and adds the bugs that only the fixed model
                         has after the current model's bugs.
  --against-dot FILE     The state graph of the spec that the current code must follow.
                         Each bug's steps replay on it. Do not use it with --fixed-dot.
  --against-traces FILE  TLC output for the spec. Repeat it. Its bugs are drawn wrong, and the
                         bugs that only the spec has number after the code's bugs.
  --label TEXT           The name of the second model in the chart and the stories. Default:
                         "the fix" with --fixed-dot, "the spec" with --against-dot.
  --spec FILE            A TLA+ file whose \\* comment lines above a rule are the rule's sentence in
                         the stories. Repeat it. The first file that has a sentence wins.
  --view NAME            customer (state labels, the default), developer (detail labels), or
                         layered (detail inside state).
  --cover                Keep only the shortest path to each settled reader state, plus the
                         counterexample paths.
  --highlight N          Draw bug N as a numbered path. Default 1. 0 draws none.
  --path-only            Draw only the highlighted path.
  --full-labels          Write each label on an edge in full, joined by " or ", and mark the chart
                         "${FULL_LABELS}". Default: write the leading words that the labels
                         share once, as in "you tap Pay or Back".
  --flat                 Draw every state on its own, with no boxes.
  --regions              When every state reads "context: progress", draw two parallel regions,
                         context and progress, when they are smaller and proved. They draw the
                         steps of the shortest way to each region state, of each bug path, and
                         the nearest step with each label.
                         Otherwise draw the chart the other flags ask for, and print why.
                         Customer view, --highlight 0, no --flat or --path-only.
  --proof FILE           With --regions, write the flat chart that the proof compares with.
  --regions-all FILE     With --regions, also write the regions with every step.
  --title TEXT           The chart title.
  --out FILE             The Mermaid chart. Default: stdout.
  --story FILE           The reader stories, one per bug.
  --summary FILE         The counts for the chart and the bugs, as JSON.
  -h, --help             Print this help, and exit 0.

Each bug replays on the second model by its screens and step words, which are what the reader
sees. The replay takes the second model's steps that keep the screen and that the reader does not
take. A bug step that the reader does not see must keep the screen on the second model too, unless
the second model cannot take it. The replay stops at the first step that the second model shows
the reader differently. There the chart draws "with LABEL, STEP" (or "in LABEL, STEP" for
--against-dot) to where the second model goes, or a loop "... STEP cannot happen" when it cannot
take a step that the reader sees.

The second model may have other variables and actions than the current model. Variables and
record fields that one start state has and the other does not are left out when the two models
are compared. The second model's states take the current model's start values for the variables
it does not have, so one mapping draws both. A step of an action that the second model does not
have is skipped when it changes no shared variable, and matches any step to the same shared state
when it does.

In the customer view, states whose labels read "context: progress" with the same context sit in
one box named context, and each shows only its progress. A context with one state stays a plain
state. An arrow from a box's border stands for the same step from every state in the box: it is
drawn only when every state in the box takes that step, with the same labels, to the same state.
The layered view puts each detail state in a box named by its state label.

With --regions, each "context: progress" label is one state in the context region and one in the
progress region. A step that happens beside only some states of the other region gets a guard:
"[when A or B]" or "[unless A or B]", whichever is shorter, and a "%% when [not] ids" line under it.
The mapping's guard words, when the step has them, replace "when A or B" in the label.
The proof combines the regions with every step as compare-charts.mjs does, and needs exactly the
flat chart's states, start states, and labeled steps. Each state's color must be the worse color
of its two region states. Then the drawn arrows, combined, must make only steps of the flat chart:
a step that they make wrongly gets back every arrow that the full regions take there.
compare-charts.mjs on the --regions-all and --proof files repeats the first proof.
mapping.regionNames = [context, progress] names the two regions.

Outside regions, two states have at most one arrow. Its lines are the numbered steps, then the
current model's steps, then the second model's steps, with a blank line between each group.

Without group(), the legend shows only the statuses the chart uses. A chart with a second model
has the line "%% second model (fix|against): LABEL" right after stateDiagram-v2. Each chart
starts with front matter that keeps Mermaid from shrinking it to the page or rewrapping its labels.

Groups: group(vars, facts) returns the name of the group that a model state is in, such as
"Toast shown", or nothing. A chart state is in a group when all its model states are in it. A
region state is in a group when every state that it is part of is in it. Each group fills its
states with one color, and the legend lists only the groups that the chart draws: first the
groups in groupColors, in that order, then the others from A to Z. groupColors, such as
{ "Toast shown": "#d6eaf8" }, gives a group a light "#rgb" or "#rrggbb" color. A group with no
color, or null, takes the next free palette color: light blue, orange, purple, yellow, teal, tan,
then pink. A state in no group, or in more than one, is gray. summary.json counts the drawn
states of each group in chartGroups, and lists the chart states with more than one in mixedGroups.
TLC decides the status, and a group cannot change it. On top of the group color, a state that
breaks a rule has a thick red border, and a fixed state or a state only in the second model a
thick green border. The legend then shows that border. A thick blue border marks the bug path on
states that work. On other states of the path, the numbered arrows show it. A group cannot have
the name of a status, such as "Breaks a rule".

Writes only the files that --out, --story, and --summary name.

Exit codes
  0  It wrote the chart.
  1  It cannot use an input: a mapping without state(), TLC output that it refuses, or a
     --highlight with no such bug. The error says why.
  2  A bad argument.`;
