export const USAGE = {
  "from-spec":
    "node statechart.mjs from-spec SPEC.tla [--fixed FIXED.tla | --against AGREED.tla] [--label TEXT] [--map FILE] [--expect-broken RULE]... [--title TEXT] [--out DIR] [--png]",
  "from-chart":
    "node statechart.mjs from-chart CHART.mmd [--module NAME] [--expect-broken RULE]... [--title TEXT] [--out DIR] [--png]",
};
export const usage = (lines) => `Usage: ${lines.join("\n       ")}`;

export const FROM_SPEC = `from-spec SPEC.tla
  Checks each INVARIANT in SPEC.cfg in a separate TLC run. TLC stops at the first rule that a state
  breaks, and the separate runs find the rest. Each run also has the rule as a CONSTRAINT, so TLC
  stops each path at its first state that breaks the rule, and a rule that stays broken reports
  only the step that broke it. SPEC.cfg sits next to the spec and has SPECIFICATION and one
  INVARIANT line per rule. One more run dumps the state graph, and then the command draws the
  charts. TLC names each step after the innermost named action that takes it, so give each kind of
  step its own named action. The command warns when steps carry the name of the whole next-state
  action.

  --fixed FIXED.tla  The model of the open fix. It is a copy of the spec with its own file and
                     module name, such as SpecFixed.tla with MODULE SpecFixed. The command checks
                     it the same way, with FIXED.cfg, or with SPEC.cfg when there is no FIXED.cfg.
                     The charts then mark each bad state fixed or still wrong.
  --against AGREED.tla
                     The spec that SPEC.tla must follow, when SPEC.tla models the code. It needs
                     its own file and module name. The command checks it with AGREED.cfg, or with
                     SPEC.cfg when there is no AGREED.cfg. SPEC.tla may add variables, record
                     fields, and actions that AGREED.tla does not have. The comparison leaves them
                     out. Do not use it with --fixed.
  --label TEXT       The name of the --fixed or --against model in the charts and the stories.
                     Default: "the fix", or "the spec".
  --map FILE         The labels for each model state and step. Default: SPEC.map.mjs next to the
                     spec. When the file does not exist, the command writes one to fill in and
                     exits 2. Its comments say what each function gets.`;

export const FROM_CHART = `from-chart CHART.mmd
  Writes NAME.tla, NAME.cfg, and NAME.map.mjs next to the chart. When NAME.tla already exists, it
  writes none of them. Then it checks the spec as from-spec does, and compares the chart that the
  spec draws with CHART.mmd.

  --module NAME      The TLA+ module name. Default: the chart's file name in CamelCase, such as
                     NotesApp for notes-app.mmd.

  The chart is a Mermaid stateDiagram-v2. Each transition label is one action. For parallel
  regions, split one top-level composite with --, and put each part in a named composite, such as
  state Connection { ... }. Each region is one variable. A step moves every region whose current
  state has a transition with the step's label, and the other regions stay where they are. Each
  rule is one comment line:
    %% never NAME: A & B -- the rule in one sentence
  Each name after the colon is a state caption or a composite, and each comes from a different
  region. A composite stands for every state in it. The command refuses final, choice, fork, and
  history states, and regions below the top level.`;

export const COMMON = `Both commands
  --expect-broken RULE
                     A rule that is known to break. Repeat it, or list rules with commas, as in
                     A,B. The command then exits 0 when exactly these rules break, and the --fixed
                     or --against model breaks no other rule.
  --title TEXT       The chart title. Each bug chart adds ", bug N".
  --out DIR          The output folder. Default: NAME-statechart next to the input. A run writes its
                     files in a temporary folder, and then replaces the whole output folder with
                     it. When runs overlap, the output folder has the files of the run that
                     finished last. The command does not use an output folder that has files that
                     it did not write.
  --png              Also render each chart to PNG with npx @mermaid-js/mermaid-cli.
  -h, --help         Print this help, and exit 0.

Output
  The command prints whether each rule holds, the chart's counts, and one story per bug.
  from-chart also prints the comparison. The command writes these files in the output folder:
  chart.mmd          The overview.
  bug-N.mmd          Only the steps of bug N, numbered. Bugs are numbered by fewest reader steps,
                     then fewest model steps, then rule name, then cause. Bugs that only the
                     --fixed or --against model has come last.
  bug-N-developer.mmd, bug-N-layered.mmd
                     The path of bug N through the developer's states, when the mapping exports
                     detail().
  stories.md         One entry per bug: the rule, why it breaks, the shortest path in reader
                     steps, and what the --fixed or --against model does instead.
  summary.json       The counts behind the chart.
  tlc/               The config and the TLC output of each run. When the overview has regions,
                     from-spec also writes tlc/regions-all.mmd, the regions with every arrow, and
                     tlc/regions-proof.mmd, every state and step of TLC's graph in one region.
                     compare-charts.mjs tlc/regions-all.mmd tlc/regions-proof.mmd repeats the
                     proof.
  *.png              Each chart as a PNG, with --png. A run without --png deletes them.

Reading a chart
  from-spec draws the overview as two parallel regions when every state reads "context: progress":
  the contexts on one side, the progress on the other, both at the same time. It does so only when
  that has fewer states, and when the regions combine back into exactly every state and step of
  TLC's graph. Otherwise it puts the states of one context in a box named context, and prints why.
  Regions draw only the arrows of the shortest way to each state, of each bug path, and of the
  nearest step with each label. The script checks that these arrows make no step that TLC's graph
  does not have.
  An arrow from a box's border leaves from every state in the box.
  In regions, a step leaves every region that has it. "[when A]" or "[unless A]" says which states
  of the other region the step needs. A loop says the region may also stay.
  Other words in [ ] come from the mapping's guard(), and "after N s" from its timer(). TLC does
  not check them, and has no clock, so a reviewer checks them against the code.
  Gray states work. Red states break a rule. With --fixed, red states stay wrong with the fix, and
  green states are fixed by it or exist only with it. With --against, red states break a rule in
  either model, and green states exist only in the spec.
  When the mapping exports group(), the fill is the state's group, which the legend names, and the
  status is a thick red or green border on top. tlc-to-chart.mjs --help tells more.
  A state is bad when it breaks a rule, or when every path from the start to it passes a state
  that breaks one. TLC stops each path at the first state that breaks the rule, so a rule that
  stays broken colors only the states where it first breaks and the states after them that no
  path without a bug reaches.
  A thick blue border and numbered labels mark the bug. Mermaid state diagrams cannot color an
  edge.
  A label "with the fix, STEP" or "in the spec, STEP" is a step that only the other model takes. On
  a bug's path it leaves the state before the first step that the other model shows the reader
  differently, and ends where that model goes instead. "with the fix, STEP cannot happen" or "in
  the spec, STEP cannot happen" loops on the state where that model stops the step. Outside
  regions, two states have at most one arrow between them. Its lines are the numbered steps, then
  SPEC.tla's steps, then the other model's steps, with a blank line between each group.
  An edge lists every step that takes it, most common first. Words that the steps share at the
  start are written once, as in "you tap Pay or Back".

Regenerate
  With --expect-broken, one script rebuilds every chart and stops on any change:
    set -e
    node statechart.mjs from-spec Code.tla --against Agreed.tla --expect-broken NoLostUpload --png

TLC
  TLA2TOOLS is the path to tla2tools.jar, and JAVA is the java binary (default: java, Java 11 or
  later). Download tla2tools.jar from https://github.com/tlaplus/tlaplus/releases. When TLA2TOOLS
  is not set, the command says where to get TLC and exits 2.

Exit codes
  0  Every rule holds, or exactly the --expect-broken rules break. from-chart also draws CHART.mmd
     back unchanged.
  1  Another rule is broken, an expected rule holds, or the chart that the spec draws is not
     CHART.mmd. The output says which.
  2  The command cannot finish: a bad argument, a missing file, a chart or TLC output that it
     cannot read, no TLC, a helper script that cannot start, an output folder with files that the
     command did not write, an input file that changed during the run, a new mapping to fill in,
     or a chart that --png cannot render. When a chart does not render, the command keeps the
     files it wrote and exits 2, whatever the rules give. Otherwise, exit 2 does not change the
     output folder, unless the command moved it aside and cannot put it back. Then the message
     names the folder's new path. When TLC stops on an error, the message names TLC's output, in a
     temporary folder that the command keeps.`;

export const HELP = {
  "": `${usage([...Object.values(USAGE), "node statechart.mjs [from-spec|from-chart] --help"])}

Draws a Mermaid statechart of what an app's user sees, from TLC's state graph of a TLA+ spec. The
help calls that user the reader.

${FROM_SPEC}

${FROM_CHART}

${COMMON}`,
  "from-spec": `${usage([USAGE["from-spec"]])}\n\n${FROM_SPEC}\n\n${COMMON}`,
  "from-chart": `${usage([USAGE["from-chart"]])}\n\n${FROM_CHART}\n\n${COMMON}`,
};

export const more = (cmd) =>
  `Run node statechart.mjs ${cmd ? `${cmd} ` : ""}--help for the flags, the output, and the exit codes.`;
