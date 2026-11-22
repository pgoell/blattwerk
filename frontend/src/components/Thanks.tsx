// What stands in a form's place once its send has arrived: a check mark, the thanks, and one button, which takes the focus.
export default function Thanks({ button, onClick }: { button: string; onClick: () => void }) {
  return (
    <div className="thanks">
      <div className="check" aria-hidden="true">✓</div>
      <p role="status">Danke! Ist angekommen.</p>
      <button type="button" className="primary" autoFocus onClick={onClick}>{button}</button>
    </div>
  );
}
