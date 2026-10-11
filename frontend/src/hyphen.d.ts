// The hyphen package ships no types.
declare module "hyphen" {
  const createHyphenator: (patterns: unknown, options?: { hyphenChar?: string; minWordLength?: number }) => (text: string) => string | Promise<string>;
  export default createHyphenator;
}
declare module "hyphen/patterns/de-1996" {
  const patterns: unknown;
  export default patterns;
}
