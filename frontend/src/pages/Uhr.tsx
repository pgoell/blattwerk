// The format panel's settings for an Uhr block: its face, its task, how a time is written, and the times.
// STUB: the panel's subagent writes it as the contract at the top of uhr.ts says.
import type { UhrBlock } from "../sheet";
import type { UhrProps } from "../uhr";

type Apply = (props: Partial<UhrProps>, key?: string) => void;

export default function Uhr({ block, apply }: { block: UhrBlock; apply: Apply }) {
  void block;
  void apply;
  return <div className="uhr-panel" />;
}
