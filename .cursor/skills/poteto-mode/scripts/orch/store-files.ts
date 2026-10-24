import { randomUUID } from "node:crypto";
import type { Dirent } from "node:fs";
import {
  access,
  open,
  readFile,
  readdir,
  rename,
  rm,
  unlink,
  writeFile,
} from "node:fs/promises";
import {
  basename,
  dirname,
  join,
} from "node:path";
import {
  Verdict,
  Unit,
  LedgerEntry,
  InboxPointer,
  OpenGate,
  Gate,
  FrontierPrState,
  FrontierPr,
  Frontier,
  StandingLine,
  Counts,
  StatusSummary,
  OpenStoreOptions,
  UserError,
} from "./store-types.ts";

export const UNIT_HEADER = "id\ttrack\tstate\tbranch\tpr\tsha\tbrief";
export const LEDGER_HEADER = "pr\tsha\tverdict\tevidence\tverifier\tts";
export const LOCK_FILE = ".orch.lock";

export function errorCode(error: unknown): string | null {
  if (
    error !== null &&
    typeof error === "object" &&
    "code" in error &&
    typeof error.code === "string"
  ) {
    return error.code;
  }
  return null;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function isUnknownArray(value: unknown): value is readonly unknown[] {
  return Array.isArray(value);
}

export function verdictOrNull(value: string): Verdict | null {
  switch (value) {
    case "live-ui-verified":
    case "unit-test-verified":
    case "type-check-only":
    case "verifier-blocked":
    case "verifier-failed":
      return value;
    default:
      return null;
  }
}

export function frontierPrStateOrNull(value: unknown): FrontierPrState | null {
  switch (value) {
    case "OPEN":
    case "MERGED":
    case "CLOSED":
      return value;
    default:
      return null;
  }
}

export function parseVerdict(value: string): Verdict {
  const verdict = verdictOrNull(value);
  if (verdict === null) {
    throw new UserError(
      "verdict must be live-ui-verified, unit-test-verified, type-check-only, verifier-blocked, or verifier-failed"
    );
  }
  return verdict;
}

export function cleanCell(value: string): string {
  const cleaned = value.replace(/[\t\n\r]/g, " ");
  return /^[=+\-@]/.test(cleaned) ? `'${cleaned}` : cleaned;
}

export function requiredCell(value: string, label: string): string {
  const cleaned = cleanCell(value);
  if (cleaned.trim().length === 0) {
    throw new UserError(`${label} must not be empty`);
  }
  return cleaned;
}

export function requiredLine(value: string, label: string): string {
  const cleaned = value.replace(/[\n\r]/g, " ").trim();
  if (cleaned.length === 0) {
    throw new UserError(`${label} must not be empty`);
  }
  return cleaned;
}

export function positiveInteger(value: number, label: string): number {
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new UserError(`${label} must be a positive integer`);
  }
  return value;
}

export async function exists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      return false;
    }
    throw error;
  }
}

export async function atomicWrite(path: string, contents: string): Promise<void> {
  const temporary = join(
    dirname(path),
    `.${basename(path)}.${process.pid}.${randomUUID()}.tmp`
  );
  try {
    await writeFile(temporary, contents, { flag: "wx" });
    await rename(temporary, path);
  } finally {
    await rm(temporary, { force: true });
  }
}

export async function writeIfMissing(path: string, contents: string): Promise<void> {
  if (!(await exists(path))) {
    await atomicWrite(path, contents);
  }
}

export async function requiredFile(path: string): Promise<string> {
  try {
    return await readFile(path, "utf8");
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      throw new UserError(
        `store is not initialized at ${dirname(path)}; run orch init`
      );
    }
    throw error;
  }
}

export function holderIsDead(holder: string): boolean {
  const pid = Number.parseInt(holder, 10);
  if (!Number.isSafeInteger(pid) || pid <= 0 || String(pid) !== holder) {
    return false;
  }
  try {
    process.kill(pid, 0);
    return false;
  } catch (error) {
    return errorCode(error) === "ESRCH";
  }
}

export async function acquireLock(
  store: string,
  options: OpenStoreOptions
): Promise<() => Promise<void>> {
  const path = join(store, LOCK_FILE);
  const pid = String(process.pid);
  const create = async (): Promise<void> => {
    const handle = await open(path, "wx");
    await handle.writeFile(`${pid}\n`);
    await handle.close();
  };

  const takeOver = async (): Promise<void> => {
    await unlink(path);
    try {
      await create();
    } catch (retryError) {
      if (errorCode(retryError) === "EEXIST") {
        const retryHolder =
          (await readFile(path, "utf8")).trim() || "unknown";
        throw new UserError(`store lock held by pid ${retryHolder}`);
      }
      throw retryError;
    }
  };

  try {
    await create();
  } catch (error) {
    if (errorCode(error) !== "EEXIST") {
      throw error;
    }
    let holder = "unknown";
    try {
      holder = (await readFile(path, "utf8")).trim() || "unknown";
    } catch {
      holder = "unknown";
    }
    if (holderIsDead(holder)) {
      options.onStaleLock?.(holder);
      await takeOver();
    } else if (options.force) {
      options.onLockStolen?.(holder);
      await takeOver();
    } else {
      throw new UserError(`store lock held by pid ${holder}`);
    }
  }

  return async (): Promise<void> => {
    try {
      if ((await readFile(path, "utf8")).trim() === pid) {
        await unlink(path);
      }
    } catch (error) {
      if (errorCode(error) !== "ENOENT") {
        throw error;
      }
    }
  };
}

export async function readTsv(
  path: string,
  header: string,
  width: number
): Promise<readonly (readonly string[])[]> {
  const lines = (await requiredFile(path)).replace(/\r/g, "").split("\n");
  if (lines.shift() !== header) {
    throw new UserError(`${basename(path)} has an invalid header`);
  }
  return lines
    .filter((value) => value.length > 0)
    .map((value) => {
      const cells = value.split("\t");
      if (cells.length !== width) {
        throw new UserError(`${basename(path)} has a malformed row`);
      }
      return cells;
    });
}

export async function writeTsv(
  path: string,
  header: string,
  rows: readonly (readonly string[])[]
): Promise<void> {
  const body = rows.map((row) => row.map(cleanCell).join("\t")).join("\n");
  await atomicWrite(path, `${header}\n${body}${body.length > 0 ? "\n" : ""}`);
}

export async function readUnits(store: string): Promise<readonly Unit[]> {
  return (await readTsv(join(store, "units.tsv"), UNIT_HEADER, 7)).map(
    (row) => ({
      id: row[0] ?? "",
      track: row[1] ?? "",
      state: row[2] ?? "",
      branch: row[3] ?? "",
      pr: row[4] ?? "",
      sha: row[5] ?? "",
      brief: row[6] ?? "",
    })
  );
}

export function unitCells(unit: Unit): readonly string[] {
  return [
    unit.id,
    unit.track,
    unit.state,
    unit.branch,
    unit.pr,
    unit.sha,
    unit.brief,
  ];
}

export async function saveUnits(store: string, rows: readonly Unit[]): Promise<void> {
  await writeTsv(
    join(store, "units.tsv"),
    UNIT_HEADER,
    rows.map(unitCells)
  );
}

export async function readLedger(store: string): Promise<readonly LedgerEntry[]> {
  return (await readTsv(join(store, "ledger.tsv"), LEDGER_HEADER, 6)).map(
    (row) => {
      const rawVerdict = row[2] ?? "";
      const verdict = verdictOrNull(rawVerdict);
      if (verdict === null) {
        throw new UserError(`ledger.tsv has invalid verdict ${rawVerdict}`);
      }
      return {
        pr: row[0] ?? "",
        sha: row[1] ?? "",
        verdict,
        evidence: row[3] ?? "",
        verifier: row[4] ?? "",
        ts: row[5] ?? "",
      };
    }
  );
}

export function ledgerCells(row: LedgerEntry): readonly string[] {
  return [
    row.pr,
    row.sha,
    row.verdict,
    row.evidence,
    row.verifier,
    row.ts,
  ];
}

export async function saveLedger(
  store: string,
  rows: readonly LedgerEntry[]
): Promise<void> {
  await writeTsv(
    join(store, "ledger.tsv"),
    LEDGER_HEADER,
    rows.map(ledgerCells)
  );
}

export function pointerCells(pointer: InboxPointer): readonly string[] {
  return [
    pointer.ts,
    pointer.agent,
    pointer.unit,
    pointer.status,
    pointer.report,
  ];
}

export async function readPointers(
  directory: string
): Promise<readonly InboxPointer[]> {
  let entries: Dirent[];
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      throw new UserError(
        `store is not initialized at ${dirname(directory)}; run orch init`
      );
    }
    throw error;
  }
  const result: InboxPointer[] = [];
  const files = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".tsv"))
    .sort((left, right) => left.name.localeCompare(right.name));
  for (const entry of files) {
    const raw = (await readFile(join(directory, entry.name), "utf8")).replace(
      /\r?\n$/,
      ""
    );
    const row = raw.split("\t");
    if (/[\r\n]/.test(raw) || row.length !== 5) {
      throw new UserError(`inbox pointer ${entry.name} is malformed`);
    }
    result.push({
      ts: row[0] ?? "",
      agent: row[1] ?? "",
      unit: row[2] ?? "",
      status: row[3] ?? "",
      report: row[4] ?? "",
    });
  }
  return result;
}

export function renderGates(rows: readonly Gate[]): string {
  if (rows.length === 0) {
    return "";
  }
  const blocks = rows.map((gate) => {
    const answer =
      gate.kind === "resolved" ? `\n- Answer: ${gate.answer}` : "";
    return `## ${gate.id}

- Status: ${gate.kind}
- Question: ${gate.question}
- Options: ${gate.options}
- Default: ${gate.defaultAnswer}${answer}`;
  });
  return `# Gates\n\n${blocks.join("\n\n")}\n`;
}

export async function readGates(store: string): Promise<readonly Gate[]> {
  const raw = (await requiredFile(join(store, "gates.md")))
    .replace(/\r/g, "")
    .trim();
  if (raw.length === 0) {
    return [];
  }
  const prefix = "# Gates\n\n## ";
  if (!raw.startsWith(prefix)) {
    throw new UserError("gates.md has an invalid heading");
  }
  const result: Gate[] = [];
  for (const block of raw.slice(prefix.length).split("\n\n## ")) {
    const lines = block.split("\n").filter((value) => value.length > 0);
    const id = lines.shift() ?? "";
    const fields = new Map<string, string>();
    for (const value of lines) {
      const match = /^- ([^:]+): (.*)$/.exec(value);
      if (match === null) {
        throw new UserError(`gates.md has a malformed gate ${id}`);
      }
      fields.set(match[1] ?? "", match[2] ?? "");
    }
    const status = fields.get("Status");
    const question = fields.get("Question");
    const options = fields.get("Options");
    const defaultAnswer = fields.get("Default");
    if (
      id.length === 0 ||
      question === undefined ||
      options === undefined ||
      defaultAnswer === undefined
    ) {
      throw new UserError(`gates.md has a malformed gate ${id}`);
    }
    if (status === "open") {
      result.push({ kind: "open", id, question, options, defaultAnswer });
    } else if (status === "resolved" && fields.has("Answer")) {
      result.push({
        kind: "resolved",
        id,
        question,
        options,
        defaultAnswer,
        answer: fields.get("Answer") ?? "",
      });
    } else {
      throw new UserError(`gates.md has invalid status ${status ?? ""}`);
    }
  }
  if (new Set(result.map((gate) => gate.id)).size !== result.length) {
    throw new UserError("gates.md has duplicate gate ids");
  }
  return result;
}

export function parseFrontier(raw: string): Frontier {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new UserError("frontier.json is not valid JSON");
  }
  if (!isRecord(value)) {
    throw new UserError("frontier.json must contain an object");
  }
  if (Object.keys(value).length === 0) {
    return { generation: 0, prs: [], lowestUnmerged: null };
  }
  if (
    typeof value.generation !== "number" ||
    !Number.isSafeInteger(value.generation) ||
    value.generation < 0 ||
    !isUnknownArray(value.prs) ||
    !(
      value.lowestUnmerged === null ||
      (typeof value.lowestUnmerged === "number" &&
        Number.isSafeInteger(value.lowestUnmerged))
    )
  ) {
    throw new UserError("frontier.json has an invalid shape");
  }
  const prs: FrontierPr[] = [];
  for (const row of value.prs) {
    const state = isRecord(row)
      ? frontierPrStateOrNull(row.state)
      : null;
    if (
      !isRecord(row) ||
      typeof row.pr !== "number" ||
      !Number.isSafeInteger(row.pr) ||
      row.pr < 1 ||
      typeof row.branches !== "string" ||
      row.branches.length === 0 ||
      typeof row.sha !== "string" ||
      state === null
    ) {
      throw new UserError("frontier.json has an invalid PR row");
    }
    prs.push({
      pr: row.pr,
      branches: row.branches,
      sha: row.sha,
      state,
    });
  }
  return {
    generation: value.generation,
    prs,
    lowestUnmerged: value.lowestUnmerged,
  };
}

export async function readFrontier(store: string): Promise<Frontier> {
  return parseFrontier(await requiredFile(join(store, "frontier.json")));
}

export async function readStanding(
  store: string
): Promise<readonly StandingLine[]> {
  const raw = (await requiredFile(join(store, "preferences.md"))).replace(
    /\r/g,
    ""
  );
  if (raw.trim().length === 0) {
    return [];
  }
  const result: StandingLine[] = [];
  for (const value of raw.split("\n").filter((item) => item.length > 0)) {
    const match = /^([1-9]\d*)\. (.+)$/.exec(value);
    const number = Number(match?.[1] ?? 0);
    if (match === null || number !== result.length + 1) {
      throw new UserError("preferences.md has malformed numbering");
    }
    result.push({ number, line: match[2] ?? "" });
  }
  return result;
}

export function countValues(values: readonly string[]): Counts {
  const result: Record<string, number> = {};
  for (const value of values) {
    result[value] = (result[value] ?? 0) + 1;
  }
  return Object.fromEntries(
    Object.entries(result).sort(([left], [right]) =>
      left.localeCompare(right)
    )
  );
}

export function summarize(
  unitRows: readonly Unit[],
  ledgerRows: readonly LedgerEntry[],
  currentFrontier: Frontier,
  gateRows: readonly Gate[]
): StatusSummary {
  return {
    unitStates: countValues(unitRows.map((unit) => unit.state)),
    ledgerVerdicts: countValues(ledgerRows.map((row) => row.verdict)),
    frontierGeneration: currentFrontier.generation,
    openGateIds: gateRows
      .filter((gate): gate is OpenGate => gate.kind === "open")
      .map((gate) => gate.id)
      .sort(),
  };
}

export function countRecord(value: unknown): Record<string, number> | null {
  if (!isRecord(value)) {
    return null;
  }
  const result: Record<string, number> = {};
  for (const [name, count] of Object.entries(value)) {
    if (
      typeof count !== "number" ||
      !Number.isSafeInteger(count) ||
      count < 0
    ) {
      return null;
    }
    result[name] = count;
  }
  return result;
}

export function previousSummary(raw: string): StatusSummary | null {
  const match = /<!-- orch-summary (.+) -->/.exec(raw);
  if (match === null) {
    return null;
  }
  let value: unknown;
  try {
    value = JSON.parse(match[1] ?? "");
  } catch {
    return null;
  }
  if (
    !isRecord(value) ||
    typeof value.frontierGeneration !== "number" ||
    !isUnknownArray(value.openGateIds)
  ) {
    return null;
  }
  const unitStates = countRecord(value.unitStates);
  const ledgerVerdicts = countRecord(value.ledgerVerdicts);
  const openGateIds = value.openGateIds.filter(
    (item): item is string => typeof item === "string"
  );
  if (
    unitStates === null ||
    ledgerVerdicts === null ||
    openGateIds.length !== value.openGateIds.length
  ) {
    return null;
  }
  return {
    unitStates,
    ledgerVerdicts,
    frontierGeneration: value.frontierGeneration,
    openGateIds,
  };
}

export function changed(before: StatusSummary | null, after: StatusSummary): string {
  if (before === null) {
    return "first render";
  }
  const result: string[] = [];
  const groups: readonly {
    readonly label: string;
    readonly oldCounts: Counts;
    readonly newCounts: Counts;
  }[] = [
    {
      label: "units",
      oldCounts: before.unitStates,
      newCounts: after.unitStates,
    },
    {
      label: "ledger",
      oldCounts: before.ledgerVerdicts,
      newCounts: after.ledgerVerdicts,
    },
  ];
  for (const { label, oldCounts, newCounts } of groups) {
    const names = [
      ...new Set([...Object.keys(oldCounts), ...Object.keys(newCounts)]),
    ].sort();
    for (const name of names) {
      const oldCount = oldCounts[name] ?? 0;
      const newCount = newCounts[name] ?? 0;
      if (oldCount !== newCount) {
        result.push(`${label} ${name} ${oldCount}->${newCount}`);
      }
    }
  }
  if (before.frontierGeneration !== after.frontierGeneration) {
    result.push(
      `frontier generation ${before.frontierGeneration}->${after.frontierGeneration}`
    );
  }
  if (before.openGateIds.join("\0") !== after.openGateIds.join("\0")) {
    result.push(
      `open gates ${before.openGateIds.length}->${after.openGateIds.length}`
    );
  }
  return result.length === 0 ? "no derived changes" : result.join("; ");
}

export function markdown(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\|/g, "\\|");
}

export function table(
  headers: readonly string[],
  rows: readonly (readonly string[])[]
): string {
  if (rows.length === 0) {
    return "(none)";
  }
  return [
    `| ${headers.join(" | ")} |`,
    `| ${headers.map(() => "---").join(" | ")} |`,
    ...rows.map((row) => `| ${row.map(markdown).join(" | ")} |`),
  ].join("\n");
}

export function statusMarkdown(
  unitRows: readonly Unit[],
  ledgerRows: readonly LedgerEntry[],
  currentFrontier: Frontier,
  gateRows: readonly Gate[],
  currentSummary: StatusSummary
): string {
  return `# Orchestrate status

Generated: ${new Date().toISOString()}

## Units

States: ${countLine(currentSummary.unitStates)}

${table(
  ["ID", "Track", "State", "Branch", "PR", "SHA", "Brief"],
  unitRows.map(unitCells)
)}

## Verification ledger

Verdicts: ${countLine(currentSummary.ledgerVerdicts)}

${table(
  ["PR", "SHA", "Verdict", "Evidence", "Verifier", "Timestamp"],
  ledgerRows.map(ledgerCells)
)}

## Frontier

Generation: ${currentFrontier.generation}
Lowest unmerged: ${currentFrontier.lowestUnmerged ?? "none"}

${table(
  ["Branch", "PR", "SHA", "State"],
  currentFrontier.prs.map((row) => [
    row.branches,
    String(row.pr),
    row.sha,
    row.state,
  ])
)}

## Gates

${table(
  ["ID", "Status", "Question", "Options", "Default", "Answer"],
  gateRows.map((gate) => [
    gate.id,
    gate.kind,
    gate.question,
    gate.options,
    gate.defaultAnswer,
    gate.kind === "resolved" ? gate.answer : "",
  ])
)}

<!-- orch-summary ${JSON.stringify(currentSummary)} -->
`;
}

export function countLine(value: Counts): string {
  const entries = Object.entries(value);
  return entries.length === 0
    ? "none"
    : entries.map(([name, count]) => `${name}=${count}`).join(", ");
}

