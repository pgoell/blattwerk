// The results a linked block asks the child to write, one list per task.
import type { Block } from "../sheet";
import { decimal, decimalsOf } from "../decimal";
import { at, made as wallsOf, sane as saneWall } from "../zahlenmauer";
import { made as trianglesOf, sane as saneDreieck } from "../rechendreieck";
import { made as strahlOf, sane as saneStrahl } from "../zahlenstrahl";
import { made as feldOf, sane as saneFeld } from "../hunderterfeld";
import { sane as saneUhr, timesOf, written } from "../uhr";
import type { Result } from "./props";

export function tasksOf(b: Block): Result[][] | undefined {
  switch (b.type) {
    case "maths": {
      const p = b.props;
      const [d, money] = moneyOf(b);
      const euro = money ? " €" : "";
      // A client wrote the exercises: what is not a task with a number or a sign to find gives no result.
      const tasks = (Array.isArray(p.exercises) ? p.exercises : []).filter(
        (e) => !!e && typeof e === "object" && ("sign" in e || typeof e[e.hide ?? "result"] === "number"),
      );
      return tasks.map((e): Result[] => {
        if ("sign" in e) return [{ text: String(e.sign) }];
        if (e.rest > 0) return [{ text: `${decimal(e.result, d, money)}${euro} R ${decimal(e.rest, 0)}`, value: e.result }];
        const v = e[e.hide ?? "result"] as number;
        return [{ text: decimal(v, d, money) + euro, value: v }];
      });
    }
    case "zahlenmauer": {
      const p = saneWall(b.props);
      if (p.empty) return [];
      const out: Result[][] = [];
      for (const w of wallsOf(p).walls) {
        if (w.wrong) continue;
        const task: Result[] = [];
        for (let r = p.base - 1; r >= 0; r--) {
          for (let c = 0; c < p.base - r; c++) {
            const s = at(p.base, r, c);
            if (!w.given[s]) task.push({ text: String(w.numbers[s]), value: w.numbers[s] });
          }
        }
        if (task.length) out.push(task);
      }
      return out;
    }
    case "rechendreieck": {
      const p = saneDreieck(b.props);
      if (p.empty) return [];
      const out: Result[][] = [];
      for (const t of trianglesOf(p).triangles) {
        if (t.wrong) continue;
        const task: Result[] = [];
        t.numbers.forEach((n, j) => {
          if (!t.given[j]) task.push({ text: String(n), value: n });
        });
        if (task.length) out.push(task);
      }
      return out;
    }
    case "zahlenstrahl":
      return strahlOf(saneStrahl(b.props), b.w).ticks.filter((t) => t.task === "box").map((t) => [{ text: String(t.value), value: t.value }]);
    case "hunderterfeld": {
      const p = saneFeld(b.props);
      if (p.look === "punkte") return [];
      return feldOf(p).cells.filter((c) => c.drawn && !c.shown).map((c) => [{ text: String(c.value), value: c.value }]);
    }
    case "uhr": {
      const p = saneUhr(b.props);
      if (p.task !== "read") return [];
      return timesOf(p).map((t) => [{ text: written(t, p) }]);
    }
    default:
      return undefined;
  }
}

export const worded = (b: Block): boolean => b.type === "maths" || b.type === "zahlenmauer" || b.type === "rechendreieck" || b.type === "uhr";

// Decimals and " €" of a block's results, as its answer key prints them.
// Stored limits without `ops` (a client wrote them) count as whole numbers.
export const moneyOf = (b: Block): [number, boolean] => {
  if (b.type !== "maths" || !Array.isArray(b.props.ops)) return [0, false];
  const d = decimalsOf(b.props);
  return [d, d > 0 && !!b.props.money];
};
