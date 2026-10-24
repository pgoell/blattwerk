import type * as T from "./types.ts";
import { nonEmpty } from "./types.ts";
import {
  readSnapshot,
  classifyPr,
  selectTierMajorStackDecision,
  verdictFactory,
  blockerVerdict,
  RunDependencies,
  deadlinePassed,
  pollUntilTerminal,
  StepResult,
} from "./policy.ts";
export async function runSimple(args: {
  readonly dependencies: RunDependencies;
  readonly contexts: T.NonEmpty<T.PrContext>;
  readonly mode: T.WatchMode;
  readonly statusOnly: boolean;
  readonly options: T.PollingOptions;
}): Promise<T.TerminalVerdict> {
  const stamp = verdictFactory(args.dependencies.clock, args.mode);
  const step = async (): Promise<StepResult<T.TerminalVerdict>> => {
    const rows: T.PrSnapshot[] = [];
    for (const context of args.contexts)
      rows.push(
        await readSnapshot({
          reader: args.dependencies.reader,
          context,
          pendingHistory: "include",
          allowDraft: args.options.allowDraft,
        })
      );
    const complete = nonEmpty(rows);
    if (complete === null) throw new Error("watch context cannot be empty");
    if (args.statusOnly)
      return {
        kind: "terminal",
        verdict: stamp({
          kind: "STATUS",
          terminal: true,
          exitCode: 0,
          reason: "status-only",
          rows: complete,
        }),
      };
    if (args.mode === "queued-stack")
      throw new Error("queued-stack requires status-only in the simple runner");
    if (args.mode === "stack")
      args.dependencies.emit(
        stamp(
          { kind: "STATUS", terminal: false, reason: "poll", rows: complete },
          args.mode
        )
      );
    const decision =
      args.mode === "single"
        ? classifyPr(complete[0], args.options.allowDraft)
        : selectTierMajorStackDecision(complete, args.options.allowDraft);
    if (decision.kind === "blocker")
      return {
        kind: "terminal",
        verdict: blockerVerdict(stamp, decision.blocker),
      };
    if (decision.kind === "ready" || decision.kind === "merged")
      return {
        kind: "terminal",
        verdict: stamp(
          {
            kind: "READY",
            terminal: true,
            exitCode: 0,
            scope: { kind: "single", pr: decision.pr },
          },
          args.mode
        ),
      };
    if (decision.kind === "clear")
      return {
        kind: "terminal",
        verdict: stamp(
          {
            kind: "READY",
            terminal: true,
            exitCode: 0,
            scope: { kind: "stack", prs: decision.prs },
          },
          args.mode
        ),
      };
    args.dependencies.emit(
      stamp({
        kind: "WAITING",
        terminal: false,
        frontier: decision.frontier,
        reason: { kind: "pending-checks", pending: decision.pending },
      })
    );
    return {
      kind: "sleep",
      seconds: args.options.interval,
      onDeadline: () =>
        stamp({
          kind: "TIMEOUT",
          terminal: true,
          exitCode: 5,
          reason: { kind: "pending-checks", pending: decision.pending },
        }),
    };
  };
  return pollUntilTerminal({
    dependencies: args.dependencies,
    options: args.options,
    stamp,
    step,
  });
}
export type QueueWork =
  | {
      readonly kind: "whole-stack-sweep";
      readonly remaining: T.NonEmpty<T.PrContext>;
    }
  | { readonly kind: "frontier-poll"; readonly frontier: T.PrContext };
export interface QueueState {
  readonly queue: T.NonEmpty<T.PrContext>;
  readonly snapshots: ReadonlyMap<T.PrNumber, T.PrSnapshot>;
  readonly work: QueueWork | null;
  readonly nextSweepAt: number;
  readonly frontier: T.PrContext | null;
  readonly lastWaitKey: string | null;
  readonly startedAt: number;
}
export const createQueueState = (
  queue: T.NonEmpty<T.PrContext>,
  now: number
): QueueState => ({
  queue,
  snapshots: new Map(),
  work: { kind: "whole-stack-sweep", remaining: queue },
  nextSweepAt: now,
  frontier: null,
  lastWaitKey: null,
  startedAt: now,
});
const orderedRows = (state: QueueState): T.PrSnapshot[] =>
  state.queue.flatMap((context) => {
    const row = state.snapshots.get(context.number);
    return row === undefined ? [] : [row];
  });
const activeRows = (state: QueueState): T.PrSnapshot[] =>
  orderedRows(state).filter((row) => row.kind !== "merged");
export function planQueue(state: QueueState, now: number): QueueState {
  if (state.work !== null) return state;
  if (state.snapshots.size === 0 || now >= state.nextSweepAt) {
    const remaining = nonEmpty(
      state.queue.filter(
        (context) => state.snapshots.get(context.number)?.kind !== "merged"
      )
    );
    if (remaining !== null)
      return { ...state, work: { kind: "whole-stack-sweep", remaining } };
  }
  const frontier = activeRows(state)[0]?.context;
  return frontier === undefined
    ? state
    : { ...state, work: { kind: "frontier-poll", frontier } };
}
export interface QueueSnapshotResult {
  readonly state: QueueState;
  readonly completedSweepRows: T.NonEmpty<T.PrSnapshot> | null;
}
export function applyQueueSnapshot(
  state: QueueState,
  snapshot: T.PrSnapshot,
  now: number,
  options: T.PollingOptions
): QueueSnapshotResult {
  if (state.work === null) throw new Error("queue has no read in flight");
  const snapshots = new Map(state.snapshots);
  snapshots.set(snapshot.context.number, snapshot);
  const base = { ...state, snapshots };
  if (state.work.kind === "frontier-poll")
    return { state: { ...base, work: null }, completedSweepRows: null };
  const [head, ...tail] = state.work.remaining;
  if (head.number !== snapshot.context.number)
    throw new Error("snapshot does not match sweep head");
  const remaining = nonEmpty(tail);
  if (remaining !== null)
    return {
      state: { ...base, work: { kind: "whole-stack-sweep", remaining } },
      completedSweepRows: null,
    };
  const rows = nonEmpty(
    state.queue.flatMap((context) => {
      const row = snapshots.get(context.number);
      return row === undefined ? [] : [row];
    })
  );
  if (rows === null || rows.length !== state.queue.length)
    throw new Error("sweep completed without every snapshot");
  return {
    state: { ...base, work: null, nextSweepAt: now + options.sweepInterval },
    completedSweepRows: rows,
  };
}
export type QueueEvaluation =
  | {
      readonly kind: "complete";
      readonly state: QueueState;
      readonly merged: T.NonEmpty<T.MergedPr>;
    }
  | {
      readonly kind: "blocker";
      readonly state: QueueState;
      readonly blocker: T.MergeBlocker;
    }
  | {
      readonly kind: "advance";
      readonly state: QueueState;
      readonly merged: T.PrContext;
      readonly frontier: T.PrContext;
      readonly remaining: number;
    }
  | {
      readonly kind: "timeout";
      readonly state: QueueState;
      readonly frontier: T.PrContext;
      readonly unmergedCount: number;
    }
  | {
      readonly kind: "waiting";
      readonly state: QueueState;
      readonly frontier: T.PrContext;
      readonly reason:
        | {
            readonly kind: "pending-checks";
            readonly pending: T.NonEmpty<T.PendingCheck>;
          }
        | { readonly kind: "merge-queue"; readonly unmergedCount: number };
      readonly emit: boolean;
    };
export function evaluateQueue(
  state: QueueState,
  now: number,
  options: T.PollingOptions
): QueueEvaluation {
  const active = activeRows(state);
  if (active.length === 0) {
    const merged = nonEmpty(
      orderedRows(state).flatMap((row) =>
        row.kind === "merged"
          ? [
              {
                kind: "merged-pr" as const,
                context: row.context,
                mergedAt: row.facts.mergedAt,
              },
            ]
          : []
      )
    );
    if (merged === null) throw new Error("empty queue cannot complete");
    return { kind: "complete", state, merged };
  }
  const rows = nonEmpty(active);
  if (rows === null) throw new Error("active queue cannot be empty");
  const decision = selectTierMajorStackDecision(rows, options.allowDraft);
  if (decision.kind === "blocker")
    return { kind: "blocker", state, blocker: decision.blocker };
  const frontier = rows[0].context;
  if (state.frontier !== null && state.frontier.number !== frontier.number)
    return {
      kind: "advance",
      state: { ...state, frontier, lastWaitKey: null },
      merged: state.frontier,
      frontier,
      remaining: active.length,
    };
  if (deadlinePassed(state.startedAt, options, now))
    return {
      kind: "timeout",
      state: { ...state, frontier },
      frontier,
      unmergedCount: active.length,
    };
  const row = rows[0];
  const pending =
    row.kind === "open" && row.ci.kind === "ci-pending" ? row.ci.pending : null;
  const reason =
    pending === null
      ? ({ kind: "merge-queue", unmergedCount: active.length } as const)
      : ({ kind: "pending-checks", pending } as const);
  const key =
    reason.kind === "pending-checks"
      ? `pending:${frontier.number}:${reason.pending.length}`
      : `queue:${frontier.number}:${reason.unmergedCount}`;
  return {
    kind: "waiting",
    state: { ...state, frontier, lastWaitKey: key },
    frontier,
    reason,
    emit: state.lastWaitKey !== key,
  };
}
export async function runQueued(args: {
  readonly dependencies: RunDependencies;
  readonly contexts: T.NonEmpty<T.PrContext>;
  readonly options: T.PollingOptions;
}): Promise<T.QueueTerminalVerdict> {
  let state = createQueueState(args.contexts, args.dependencies.clock.now());
  const stamp = verdictFactory(args.dependencies.clock, "queued-stack");
  args.dependencies.emit(
    stamp({ kind: "QUEUE", terminal: false, queue: args.contexts })
  );
  const step = async (): Promise<StepResult<T.QueueTerminalVerdict>> => {
    state = planQueue(state, args.dependencies.clock.now());
    if (state.work === null) {
      const complete = evaluateQueue(
        state,
        args.dependencies.clock.now(),
        args.options
      );
      if (complete.kind !== "complete")
        throw new Error("queue has no work while active");
      return {
        kind: "terminal",
        verdict: stamp({
          kind: "COMPLETE",
          terminal: true,
          exitCode: 0,
          queue: state.queue,
          merged: complete.merged,
        }),
      };
    }
    const context =
      state.work.kind === "whole-stack-sweep"
        ? state.work.remaining[0]
        : state.work.frontier;
    const snapshot = await readSnapshot({
      reader: args.dependencies.reader,
      context,
      pendingHistory: "omit",
      allowDraft: args.options.allowDraft,
    });
    const applied = applyQueueSnapshot(
      state,
      snapshot,
      args.dependencies.clock.now(),
      args.options
    );
    state = applied.state;
    if (applied.completedSweepRows !== null)
      args.dependencies.emit(
        stamp({
          kind: "STATUS",
          terminal: false,
          reason: "whole-stack-sweep",
          rows: applied.completedSweepRows,
        })
      );
    if (state.work !== null) return { kind: "continue" };
    const evaluation = evaluateQueue(
      state,
      args.dependencies.clock.now(),
      args.options
    );
    state = evaluation.state;
    switch (evaluation.kind) {
      case "complete":
        return {
          kind: "terminal",
          verdict: stamp({
            kind: "COMPLETE",
            terminal: true,
            exitCode: 0,
            queue: state.queue,
            merged: evaluation.merged,
          }),
        };
      case "blocker":
        return {
          kind: "terminal",
          verdict: blockerVerdict(stamp, evaluation.blocker),
        };
      case "advance":
        args.dependencies.emit(
          stamp({
            kind: "ADVANCE",
            terminal: false,
            merged: evaluation.merged,
            frontier: evaluation.frontier,
            remaining: evaluation.remaining,
          })
        );
        return { kind: "continue" };
      case "timeout":
        return {
          kind: "terminal",
          verdict: stamp({
            kind: "TIMEOUT",
            terminal: true,
            exitCode: 5,
            reason: {
              kind: "queued-stack",
              frontier: evaluation.frontier,
              unmergedCount: evaluation.unmergedCount,
            },
          }),
        };
      case "waiting":
        if (evaluation.emit)
          args.dependencies.emit(
            stamp({
              kind: "WAITING",
              terminal: false,
              frontier: evaluation.frontier,
              reason: evaluation.reason,
            })
          );
        return { kind: "sleep", seconds: args.options.interval };
      default: {
        const exhaustive: never = evaluation;
        return exhaustive;
      }
    }
  };
  return pollUntilTerminal({
    dependencies: args.dependencies,
    options: args.options,
    stamp,
    step,
  });
}
