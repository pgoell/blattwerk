// The Einmaleins-Reihen a teacher picks: the rows 1 to 10, and Kernaufgaben as the preset 1, 2, 5, 10.

export const KERN = [1, 2, 5, 10];

export function Reihen({
  reihen,
  onChange,
  disabled,
  lockLast,
}: {
  reihen: number[];
  onChange: (next: number[]) => void;
  disabled?: boolean;
  lockLast?: boolean;
}) {
  const kern = reihen.length === KERN.length && KERN.every((n) => reihen.includes(n));
  return (
    <>
      <div className="reihen">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => {
          const on = reihen.includes(n);
          return (
            <label key={n}>
              <input
                type="checkbox"
                aria-label={`${n}er-Reihe`}
                checked={on}
                disabled={disabled || (!!lockLast && on && reihen.length === 1)}
                onChange={() => onChange(on ? reihen.filter((x) => x !== n) : [...reihen, n].sort((a, b) => a - b))}
              />
              {n}
            </label>
          );
        })}
      </div>
      <div className="seg">
        <button type="button" aria-pressed={kern} disabled={disabled || kern} onClick={() => onChange([...KERN])}>
          Kernaufgaben
        </button>
      </div>
    </>
  );
}
