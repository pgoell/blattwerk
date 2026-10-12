// A whole number of the smallest place as German schools write it: 350 with 2 places is 3,5, and 3,50 as money.
export function decimal(n: number, places: number, money = false): string {
  if (places === 0) return String(n);
  const digits = String(n).padStart(places + 1, "0");
  const whole = digits.slice(0, -places);
  const fraction = money ? digits.slice(-places) : digits.slice(-places).replace(/0+$/, "");
  return fraction ? `${whole},${fraction}` : whole;
}
