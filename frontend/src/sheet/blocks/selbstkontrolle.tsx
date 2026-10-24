// Draws one Selbstkontrolle block.

import { PT } from "../../height";
import { sane as saneSelbst, checked } from "../../selbstkontrolle";
import { Whole } from "../context";
import type { SelbstkontrolleBlock } from "../tasks";
import { useContext, useRef, useLayoutEffect } from "react";

// A Selbstkontrolle, drawn as the contract at the top of selbstkontrolle.ts says. Its text is in Andika at its size,
// and a content taller than the block shrinks it, as Maths does. Its hint shows in the editor only: Paper hides it.
export function Selbstkontrolle({ block, k, solved }: { block: SelbstkontrolleBlock; k: number; solved: boolean }) {
  const p = saneSelbst(block.props);
  const doc = useContext(Whole);
  const check = checked(p, doc);
  const root = useRef<HTMLDivElement>(null);
  function fit() {
    const el = root.current;
    if (!el) return;
    el.style.removeProperty("--fit");
    // A block with no height to speak of has no scale: it would come out below nothing.
    // Too tall or too wide (a long table): it takes the smaller of the two scales. Lines of a pixel do not shrink
    // with the type, so it measures again, up to three times.
    let fit = 1;
    for (let round = 0; round < 3; round++) {
      const tall = el.clientHeight > 2 && el.scrollHeight > el.clientHeight + 1 ? (el.clientHeight - 2) / el.scrollHeight : 1;
      // The content's own width: turned, a table too wide spills to the left, where the block's scrollWidth misses it.
      const inner = (el.querySelector(".inner") as HTMLElement | null)?.scrollWidth ?? 0;
      const spill = Math.max(el.scrollWidth, inner);
      const wide = el.clientWidth > 2 && spill > el.clientWidth + 1 ? (el.clientWidth - 2) / spill : 1;
      if (Math.min(tall, wide) >= 1) break;
      fit *= Math.min(tall, wide);
      el.style.setProperty("--fit", String(fit));
    }
  }
  useLayoutEffect(() => {
    fit();
  });
  useLayoutEffect(() => {
    document.fonts.ready.then(fit);
    document.fonts.addEventListener("loadingdone", fit);
    return () => document.fonts.removeEventListener("loadingdone", fit);
  }, []);
  const whole = check.lost.length === 0;
  const hint = check.lost.length ? "Die Selbstkontrolle hat ihre Quelle verloren." : check.empty && check.bare ? "Füge zuerst Aufgaben ein, dann wähle sie rechts unter „Blöcke“." : check.empty ? "Wähle rechts unter „Blöcke“ die Blöcke, die die Selbstkontrolle prüft." : check.fault;
  return (
    <div ref={root} className={`selbstkontrolle${solved ? " solved" : ""}${p.turn === "none" ? "" : ` ${p.turn}`}`} style={{ fontSize: `calc(${p.size * PT * k}px * var(--fit, 1))` }}>
      {whole && p.turn === "fold" && <div className="fold">Hier umknicken</div>}
      <div className="inner">
        {whole && p.title && <h3 className="title">{p.title}</h3>}
        {whole && p.form === "mixed" && <ul className="mixed">{check.mixed.map((text, i) => <li key={i}><span className="tick" />{text}</li>)}</ul>}
        {whole && p.form === "sum" && <ul className="sums">{check.sums.map(([label, text], i) => <li key={i}>{`${label}: ${text}`}</li>)}</ul>}
        {whole && p.form === "word" && !check.fault && (
          <>
            <table className="word">
              <tbody>
                <tr className="results">{check.table.map(([text], i) => <td key={i}>{text}</td>)}</tr>
                <tr className="letters">{check.table.map(([, letter], i) => <td key={i}>{letter}</td>)}</tr>
              </tbody>
            </table>
            {solved && <p className="answer">{p.word}</p>}
          </>
        )}
      </div>
      {/* Outside the turned content and out of the flow: it reads upright and does not shrink the type. */}
      {hint && <p className="hint">{hint}</p>}
    </div>
  );
}
