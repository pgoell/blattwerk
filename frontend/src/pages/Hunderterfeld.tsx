// The format panel's settings for a Hunderterfeld block: its look, its numbers, its tints and its cut-out.
// Stub: the panel task fills it in as the contract at the top of hunderterfeld.ts says.
import type { HunderterfeldBlock } from "../sheet";
import { sane, type HunderterfeldProps } from "../hunderterfeld";

export default function Hunderterfeld({ block, apply }: { block: HunderterfeldBlock; apply: (props: Partial<HunderterfeldProps>, key?: string) => void }) {
  const p = sane(block.props);
  return (
    <>
      <h2>Hunderterfeld</h2>
      <select aria-label="Darstellung" value={p.look} onChange={(e) => apply({ look: e.target.value as HunderterfeldProps["look"] })}>
        <option value="tafel">Hundertertafel</option>
        <option value="punkte">Punktefeld</option>
      </select>
    </>
  );
}
