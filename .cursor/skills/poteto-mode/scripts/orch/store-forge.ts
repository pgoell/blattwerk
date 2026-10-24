import { execFileSync } from "node:child_process";
import {
  open,
} from "node:fs/promises";
import {
  join,
  resolve,
} from "node:path";
import {
  errorMessage,
  isRecord,
  isUnknownArray,
} from "./store-files.ts";
import {
  Forge,
  FrontierPrState,
  FrontierPr,
  UserError,
} from "./store-types.ts";

interface ForgePullRequestQuery {
  readonly stateField: string;
  readonly headField: string;
  readonly baseField: string;
  readonly states: ReadonlyMap<string, FrontierPrState>;
}

const FORGE_PULL_REQUEST_QUERIES: Readonly<
  Record<Forge, ForgePullRequestQuery>
> = {
  gh: {
    stateField: "state",
    headField: "headRefName",
    baseField: "baseRefName",
    states: new Map<string, FrontierPrState>([
      ["OPEN", "OPEN"],
      ["MERGED", "MERGED"],
      ["CLOSED", "CLOSED"],
    ]),
  },
  origin: {
    stateField: "status",
    headField: "headRef",
    baseField: "baseRef",
    states: new Map<string, FrontierPrState>([
      ["open", "OPEN"],
      ["draft", "OPEN"],
      ["merged", "MERGED"],
      ["closed", "CLOSED"],
    ]),
  },
};

export function parseForge(value: string): Forge {
  if (value === "gh" || value === "origin") {
    return value;
  }
  throw new UserError("forge must be gh or origin");
}

interface ForgePullRequest {
  readonly pr: number;
  readonly state: FrontierPrState;
  readonly branch: string;
  readonly base: string;
}

export function runTool({
  command,
  args,
  repo,
}: {
  command: string;
  args: readonly string[];
  repo: string;
}): string {
  try {
    return execFileSync(command, args, {
      cwd: repo,
      encoding: "utf8",
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    throw new UserError(
      `${command} ${args.join(" ")} failed: ${errorMessage(error)}`
    );
  }
}

export function listPullRequests({
  filter,
  branch,
  forge,
  repo,
}: {
  filter: "--head" | "--base";
  branch: string;
  forge: Forge;
  repo: string;
}): readonly ForgePullRequest[] {
  const query = FORGE_PULL_REQUEST_QUERIES[forge];
  const command = `${forge} pr list ${filter} ${branch}`;
  // Every state is fetched because a merged or closed PR still anchors the
  // chain, and a draft counts as OPEN.
  const raw = runTool({
    command: forge,
    args: [
      "pr",
      "list",
      filter,
      branch,
      "--state",
      "all",
      "--json",
      ["number", query.stateField, query.headField, query.baseField].join(
        ","
      ),
    ],
    repo,
  });
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new UserError(`${command} output is not valid JSON`);
  }
  if (!isUnknownArray(value)) {
    throw new UserError(`${command} output is not a JSON array`);
  }
  return value.map((row) => {
    const status = isRecord(row) ? row[query.stateField] : undefined;
    const state =
      typeof status === "string" ? (query.states.get(status) ?? null) : null;
    const head = isRecord(row) ? row[query.headField] : undefined;
    const base = isRecord(row) ? row[query.baseField] : undefined;
    if (
      !isRecord(row) ||
      typeof row.number !== "number" ||
      !Number.isSafeInteger(row.number) ||
      row.number < 1 ||
      state === null ||
      typeof head !== "string" ||
      head.length === 0 ||
      typeof base !== "string" ||
      base.length === 0
    ) {
      throw new UserError(`${command} output has an invalid PR row`);
    }
    return { pr: row.number, state, branch: head, base };
  });
}

export function branchPullRequest({
  branch,
  forge,
  repo,
}: {
  branch: string;
  forge: Forge;
  repo: string;
}): ForgePullRequest {
  const rows = listPullRequests({ filter: "--head", branch, forge, repo });
  const row = rows[0];
  if (row === undefined) {
    throw new UserError(
      `branch ${branch} has no pull request; open one with ${forge} pr create, or resolve the frontier from a branch whose chain is fully submitted`
    );
  }
  if (rows.length > 1) {
    throw new UserError(
      `branch ${branch} has multiple pull requests (${rows.map((item) => `#${item.pr}`).join(", ")}); close the stale ones first`
    );
  }
  return row;
}

export function openChildren({
  branch,
  forge,
  repo,
}: {
  branch: string;
  forge: Forge;
  repo: string;
}): readonly ForgePullRequest[] {
  return listPullRequests({ filter: "--base", branch, forge, repo }).filter(
    (row) => row.state === "OPEN"
  );
}

export function runGit({
  args,
  repo,
}: {
  args: readonly string[];
  repo: string;
}): string {
  return runTool({ command: "git", args, repo }).trim();
}

export function branchSha({
  branch,
  repo,
}: {
  branch: string;
  repo: string;
}): string {
  const sha = runGit({ args: ["rev-parse", branch], repo });
  if (!/^[0-9a-f]{40,64}$/i.test(sha)) {
    throw new UserError(`git rev-parse ${branch} returned an invalid SHA`);
  }
  return sha;
}

export function currentBranch(repo: string): string {
  return runGit({ args: ["symbolic-ref", "--short", "HEAD"], repo });
}

export function trunkBranch(repo: string): string {
  try {
    return runGit({
      args: ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
      repo,
    }).replace(/^origin\//, "");
  } catch {
    // Init-plus-fetch checkouts and local fixtures lack origin/HEAD.
    return "main";
  }
}

export function resolveFrontier(repo: string, forge: Forge): readonly FrontierPr[] {
  const trunk = trunkBranch(repo);
  const current = currentBranch(repo);
  if (current === trunk) {
    return [];
  }
  const seen = new Set([current]);
  let bottom = branchPullRequest({ branch: current, forge, repo });
  const chain = [bottom];
  while (bottom.base !== trunk) {
    if (seen.has(bottom.base)) {
      throw new UserError(
        `pull request base chain loops at branch ${bottom.base}`
      );
    }
    seen.add(bottom.base);
    bottom = branchPullRequest({ branch: bottom.base, forge, repo });
    chain.unshift(bottom);
  }
  let tip = current;
  for (;;) {
    const children = openChildren({ branch: tip, forge, repo });
    const child = children[0];
    if (child === undefined) {
      break;
    }
    if (children.length > 1) {
      throw new UserError(
        `stack is not linear: branches ${children.map((row) => row.branch).join(", ")} all target ${tip}`
      );
    }
    if (seen.has(child.branch)) {
      throw new UserError(
        `pull request base chain loops at branch ${child.branch}`
      );
    }
    seen.add(child.branch);
    chain.push(child);
    tip = child.branch;
  }
  if (new Set(chain.map((row) => row.pr)).size !== chain.length) {
    throw new UserError(
      "pull request base chain contains duplicate pull requests"
    );
  }
  return chain.map((row) => ({
    pr: row.pr,
    branches: row.branch,
    sha: branchSha({ branch: row.branch, repo }),
    state: row.state,
  }));
}

export function validateFrontierPin({
  actual,
  expected,
}: {
  actual: readonly number[];
  expected: readonly number[];
}): void {
  if (
    actual.length === expected.length &&
    actual.every((pr, index) => pr === expected[index])
  ) {
    return;
  }
  const actualSet = new Set(actual);
  const expectedSet = new Set(expected);
  const missing = expected.filter((pr) => !actualSet.has(pr));
  const extra = actual.filter((pr) => !expectedSet.has(pr));
  const drift: string[] = [];
  if (missing.length > 0) {
    drift.push(`missing from resolved chain: ${missing.join(",")}`);
  }
  if (extra.length > 0) {
    drift.push(`extra in resolved chain: ${extra.join(",")}`);
  }
  if (missing.length === 0 && extra.length === 0) {
    drift.push(
      `order differs: expected ${expected.join(",")}; resolved ${actual.join(",")}`
    );
  }
  throw new UserError(`frontier pin mismatch: ${drift.join("; ")}`);
}

