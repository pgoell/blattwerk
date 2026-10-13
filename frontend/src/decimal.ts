// The gap between the groups of a big number: a narrow no-break space, as the school books set it.
export const GAP = String.fromCharCode(0x202f);

// A whole number of the smallest place as German schools write it: 350 with 2 places is 3,5, and 3,50 as money.
// A whole part of five digits or more is set in threes from the right: 270 091, and 9999 has no gap.
// Two places keep their zeros, as money does: 17,30 and 7,00. One place drops them: 3,5 and 3.
export function decimal(n: number, places: number, money = false): string {
  const digits = String(n).padStart(places + 1, "0");
  const cut = digits.length - places;
  const whole = digits.slice(0, cut);
  const grouped = whole.length < 5 ? whole : whole.replace(/\B(?=(\d{3})+$)/g, GAP);
  const fraction = money || places === 2 ? digits.slice(cut) : digits.slice(cut).replace(/0+$/, "");
  return fraction ? `${grouped},${fraction}` : grouped;
}
