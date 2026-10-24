import { randomUUID } from "node:crypto";
import {
  mkdir,
  open,
  readFile,
  rename,
  rm,
} from "node:fs/promises";
import {
  join,
  resolve,
} from "node:path";
import {
  Unit,
  LedgerEntry,
  InboxPointer,
  OpenGate,
  ResolvedGate,
  Frontier,
  StandingLine,
  OpenStoreOptions,
  Store,
  UserError,
  NotFoundError,
} from "./store-types.ts";
import {
  LEDGER_HEADER,
  UNIT_HEADER,
  parseVerdict,
  cleanCell,
  requiredCell,
  requiredLine,
  positiveInteger,
  exists,
  atomicWrite,
  writeIfMissing,
  acquireLock,
  readUnits,
  saveUnits,
  readLedger,
  saveLedger,
  pointerCells,
  readPointers,
  renderGates,
  readGates,
  readFrontier,
  readStanding,
  countValues,
  summarize,
  previousSummary,
  changed,
  statusMarkdown,
} from "./store-files.ts";
import {
  parseForge,
  resolveFrontier,
  validateFrontierPin,
} from "./store-forge.ts";

export type {
  Forge,
  Verdict,
  Unit,
  LedgerEntry,
  InboxPointer,
  InboxPushResult,
  OpenGate,
  ResolvedGate,
  Gate,
  FrontierPrState,
  FrontierPr,
  Frontier,
  StandingLine,
  Counts,
  StatusSummary,
  StatusReport,
  AddUnitParams,
  SetUnitParams,
  ListUnitsParams,
  RecordLedgerParams,
  CheckLedgerParams,
  PushInboxParams,
  ParkGateParams,
  ResolveGateParams,
  SetFrontierParams,
  AddStandingParams,
  OpenStoreOptions,
  Store,
  NotFoundOutput,
} from "./store-types.ts";
export {
  UserError,
  UsageError,
  NotFoundError,
} from "./store-types.ts";
export { parseVerdict } from "./store-files.ts";
export { parseForge } from "./store-forge.ts";

export function openStore(
  directory: string,
  options: OpenStoreOptions = {}
): Store {
  const store = resolve(directory);
  let closed = false;
  let releaseLock: (() => Promise<void>) | null = null;
  let lockRequest: Promise<void> | null = null;

  const ensureOpen = (): void => {
    if (closed) {
      throw new UserError("store is closed");
    }
  };

  const ensureLock = async (): Promise<void> => {
    ensureOpen();
    if (releaseLock !== null) {
      return;
    }
    if (lockRequest === null) {
      lockRequest = acquireLock(store, options).then((release) => {
        releaseLock = release;
      });
    }
    try {
      await lockRequest;
    } catch (error) {
      lockRequest = null;
      throw error;
    }
  };

  const beginWrite = async (): Promise<void> => {
    ensureOpen();
    if (!(await exists(store))) {
      throw new UserError(
        `store is not initialized at ${store}; run orch init`
      );
    }
    await ensureLock();
  };

  return {
    units: {
      add: async (params) => {
        await beginWrite();
        const row: Unit = {
          id: requiredCell(params.id, "unit id"),
          track: requiredCell(params.track, "track"),
          state: "pending",
          branch: "",
          pr: "",
          sha: "",
          brief:
            params.brief === undefined
              ? ""
              : requiredCell(params.brief, "brief"),
        };
        const rows = [...(await readUnits(store))];
        if (rows.some((unit) => unit.id === row.id)) {
          throw new UserError(`unit ${row.id} already exists`);
        }
        rows.push(row);
        await saveUnits(store, rows);
        return row;
      },
      set: async (params) => {
        await beginWrite();
        const id = requiredCell(params.id, "unit id");
        const state = requiredCell(params.state, "state");
        const rows = [...(await readUnits(store))];
        const index = rows.findIndex((unit) => unit.id === id);
        const old = rows[index];
        if (index < 0 || old === undefined) {
          throw new NotFoundError(`unit ${id} not found`);
        }
        const row: Unit = {
          ...old,
          state,
          branch:
            params.branch === undefined
              ? old.branch
              : requiredCell(params.branch, "branch"),
          pr:
            params.pr === undefined
              ? old.pr
              : String(positiveInteger(params.pr, "PR")),
          sha:
            params.sha === undefined
              ? old.sha
              : requiredCell(params.sha, "SHA"),
        };
        rows[index] = row;
        await saveUnits(store, rows);
        return row;
      },
      get: async (id) => {
        ensureOpen();
        const cleanId = requiredCell(id, "unit id");
        const row = (await readUnits(store)).find(
          (unit) => unit.id === cleanId
        );
        if (row === undefined) {
          throw new NotFoundError(`unit ${cleanId} not found`);
        }
        return row;
      },
      list: async (params = {}) => {
        ensureOpen();
        const state =
          params.state === undefined
            ? undefined
            : requiredCell(params.state, "state");
        const track =
          params.track === undefined
            ? undefined
            : requiredCell(params.track, "track");
        return (await readUnits(store)).filter(
          (unit) =>
            (state === undefined || unit.state === state) &&
            (track === undefined || unit.track === track)
        );
      },
      counts: async () => {
        ensureOpen();
        return countValues(
          (await readUnits(store)).map((unit) => unit.state)
        );
      },
    },
    ledger: {
      record: async (params) => {
        await beginWrite();
        const verdict = parseVerdict(params.verdict);
        const row: LedgerEntry = {
          pr: String(positiveInteger(params.pr, "PR")),
          sha: requiredCell(params.sha, "SHA"),
          verdict,
          evidence: requiredCell(params.evidence, "evidence"),
          verifier:
            params.verifier === undefined
              ? ""
              : requiredCell(params.verifier, "verifier"),
          ts: new Date().toISOString(),
        };
        const rows = [...(await readLedger(store))];
        const index = rows.findIndex(
          (old) => old.pr === row.pr && old.sha === row.sha
        );
        if (index < 0) {
          rows.push(row);
        } else {
          rows[index] = row;
        }
        await saveLedger(store, rows);
        return row;
      },
      check: async (params) => {
        ensureOpen();
        const pr = String(positiveInteger(params.pr, "PR"));
        const sha = requiredCell(params.sha, "SHA");
        const row = (await readLedger(store)).find(
          (value) => value.pr === pr && value.sha === sha
        );
        if (row === undefined) {
          throw new NotFoundError("NOT-VERIFIED", {
            compact: "NOT-VERIFIED",
            json: { pr, sha, verdict: "NOT-VERIFIED" },
          });
        }
        return row;
      },
      summary: async () => {
        ensureOpen();
        return countValues(
          (await readLedger(store)).map((row) => row.verdict)
        );
      },
    },
    inbox: {
      push: async (params) => {
        await beginWrite();
        const pointer: InboxPointer = {
          ts: new Date().toISOString(),
          agent: requiredCell(params.agent, "agent"),
          unit: requiredCell(params.unit, "unit"),
          status: requiredCell(params.status, "status"),
          report:
            params.report === undefined
              ? ""
              : requiredCell(params.report, "report"),
        };
        const inbox = join(store, "inbox");
        if (!(await exists(inbox))) {
          throw new UserError(
            `store is not initialized at ${store}; run orch init`
          );
        }
        const timestamp = pointer.ts.replace(/[:.]/g, "-");
        const filename = `${timestamp}-${process.pid}-${randomUUID()}.tsv`;
        const contents = `${pointerCells(pointer).map(cleanCell).join("\t")}\n`;
        await atomicWrite(join(inbox, filename), contents);
        return { pointer, filename };
      },
      drain: async () => {
        await beginWrite();
        const inbox = join(store, "inbox");
        const rows = await readPointers(inbox);
        const drained = join(
          store,
          `.inbox-drain-${process.pid}-${randomUUID()}`
        );
        await rename(inbox, drained);
        try {
          await mkdir(inbox);
        } catch (error) {
          await rename(drained, inbox);
          throw error;
        }
        await rm(drained, { recursive: true, force: true });
        return rows;
      },
      peek: async () => {
        ensureOpen();
        return readPointers(join(store, "inbox"));
      },
      count: async () => {
        ensureOpen();
        return (await readPointers(join(store, "inbox"))).length;
      },
    },
    gates: {
      park: async (params) => {
        await beginWrite();
        const gate: OpenGate = {
          kind: "open",
          id: requiredLine(params.id, "gate id"),
          question: requiredLine(params.question, "question"),
          options: requiredLine(params.options, "options"),
          defaultAnswer: requiredLine(
            params.defaultAnswer,
            "default"
          ),
        };
        const rows = [...(await readGates(store))];
        const index = rows.findIndex((old) => old.id === gate.id);
        if (index < 0) {
          rows.push(gate);
        } else {
          rows[index] = gate;
        }
        await atomicWrite(join(store, "gates.md"), renderGates(rows));
        return gate;
      },
      list: async () => {
        ensureOpen();
        return (await readGates(store)).filter(
          (gate): gate is OpenGate => gate.kind === "open"
        );
      },
      resolve: async (params) => {
        await beginWrite();
        const id = requiredLine(params.id, "gate id");
        const rows = [...(await readGates(store))];
        const index = rows.findIndex((gate) => gate.id === id);
        const old = rows[index];
        if (index < 0 || old === undefined) {
          throw new NotFoundError(`gate ${id} not found`);
        }
        const gate: ResolvedGate = {
          kind: "resolved",
          id: old.id,
          question: old.question,
          options: old.options,
          defaultAnswer: old.defaultAnswer,
          answer: requiredLine(params.answer, "answer"),
        };
        rows[index] = gate;
        await atomicWrite(join(store, "gates.md"), renderGates(rows));
        return gate;
      },
    },
    frontier: {
      set: async (params) => {
        await beginWrite();
        const repo = resolve(requiredLine(params.repo, "repo directory"));
        const forge = parseForge(params.forge ?? "gh");
        const pin =
          params.prs === undefined
            ? undefined
            : params.prs.map((pr) => positiveInteger(pr, "PR"));
        if (pin !== undefined && new Set(pin).size !== pin.length) {
          throw new UserError("--prs must not contain duplicates");
        }
        const old = await readFrontier(store);
        const prs = resolveFrontier(repo, forge);
        if (pin !== undefined) {
          validateFrontierPin({
            actual: prs.map((row) => row.pr),
            expected: pin,
          });
        }
        const value: Frontier = {
          generation: old.generation + 1,
          prs,
          lowestUnmerged: prs.find((row) => row.state === "OPEN")?.pr ?? null,
        };
        await atomicWrite(
          join(store, "frontier.json"),
          `${JSON.stringify(value, null, 2)}\n`
        );
        return value;
      },
      show: async () => {
        ensureOpen();
        return readFrontier(store);
      },
    },
    standing: {
      show: async () => {
        ensureOpen();
        return readStanding(store);
      },
      add: async (params) => {
        await beginWrite();
        const rows = [...(await readStanding(store))];
        const item: StandingLine = {
          number: rows.length + 1,
          line: requiredLine(params.line, "standing order"),
        };
        rows.push(item);
        await atomicWrite(
          join(store, "preferences.md"),
          `${rows.map((row) => `${row.number}. ${row.line}`).join("\n")}\n`
        );
        return item;
      },
    },
    status: {
      render: async () => {
        await beginWrite();
        const unitRows = await readUnits(store);
        const ledgerRows = await readLedger(store);
        const currentFrontier = await readFrontier(store);
        const gateRows = await readGates(store);
        const currentSummary = summarize(
          unitRows,
          ledgerRows,
          currentFrontier,
          gateRows
        );
        const path = join(store, "status.md");
        const before = (await exists(path))
          ? previousSummary(await readFile(path, "utf8"))
          : null;
        const change = changed(before, currentSummary);
        await atomicWrite(
          path,
          statusMarkdown(
            unitRows,
            ledgerRows,
            currentFrontier,
            gateRows,
            currentSummary
          )
        );
        return {
          units: unitRows,
          ledger: ledgerRows,
          frontier: currentFrontier,
          gates: gateRows,
          summary: currentSummary,
          changed: change,
        };
      },
    },
    init: async () => {
      ensureOpen();
      await mkdir(store, { recursive: true });
      await ensureLock();
      await writeIfMissing(join(store, "units.tsv"), `${UNIT_HEADER}\n`);
      await writeIfMissing(join(store, "ledger.tsv"), `${LEDGER_HEADER}\n`);
      await mkdir(join(store, "inbox"), { recursive: true });
      await writeIfMissing(join(store, "gates.md"), "");
      await writeIfMissing(join(store, "preferences.md"), "");
      await writeIfMissing(join(store, "frontier.json"), "{}\n");
      return { store };
    },
    close: async () => {
      if (closed) {
        return;
      }
      if (lockRequest !== null) {
        try {
          await lockRequest;
        } catch {
          // A failed acquisition has no lock to release.
        }
      }
      const release = releaseLock;
      releaseLock = null;
      closed = true;
      if (release !== null) {
        await release();
      }
    },
  };
}
