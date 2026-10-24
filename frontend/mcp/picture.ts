import { Fail } from "./errors.ts";

// The EXIF orientation (tag 0x0112 of the first IFD) of the TIFF block at `tiff`, or 1 when it has none.
function orientation(buf: Buffer, tiff: number): number {
  const le = buf.subarray(tiff, tiff + 2).toString("latin1") === "II";
  const u16 = (at: number) => (le ? buf.readUInt16LE(at) : buf.readUInt16BE(at));
  const u32 = (at: number) => (le ? buf.readUInt32LE(at) : buf.readUInt32BE(at));
  const ifd = tiff + u32(tiff + 4);
  for (let i = 0; i < u16(ifd); i++) {
    const entry = ifd + 2 + 12 * i;
    if (u16(entry) === 0x0112) return u16(entry + 8);
  }
  return 1;
}

// The size of an SVG picture: the root's numeric width and height, or else the viewBox's.
function svgSize(svg: string): [number, number] {
  const root = svg.match(/<svg\b[^>]*>/)?.[0] ?? "";
  const attr = (name: string) => Number(root.match(new RegExp(`\\s${name}\\s*=\\s*["']([\\d.]+)(?:px)?["']`))?.[1]);
  let [w, h] = [attr("width"), attr("height")];
  if (!(w > 0 && h > 0)) {
    const box = root.match(/\sviewBox\s*=\s*["']([^"']*)["']/)?.[1].trim().split(/[\s,]+/).map(Number);
    [w, h] = box ? [box[2], box[3]] : [0, 0];
  }
  if (!(w > 0 && h > 0)) throw new Fail("The SVG picture has no size: it needs a viewBox.");
  return [w, h];
}

// Width and height in pixels from a picture's header: PNG, GIF, JPEG or WebP, as the browser shows it.
export function dimensions(buf: Buffer): [number, number] {
  if (/^\s*<(svg|\?xml)/.test(buf.subarray(0, 64).toString("latin1"))) return svgSize(buf.toString("utf8"));
  if (buf.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])))
    return [buf.readUInt32BE(16), buf.readUInt32BE(20)];
  if (buf.subarray(0, 3).toString("latin1") === "GIF") return [buf.readUInt16LE(6), buf.readUInt16LE(8)];
  if (buf[0] === 0xff && buf[1] === 0xd8) {
    let at = 2;
    // A photo taken upright says so in its EXIF orientation (5 to 8): the browser, and so the editor, turns it.
    let turned = false;
    while (at + 9 < buf.length) {
      if (buf[at] !== 0xff) throw new Fail("The picture's header is broken.");
      const marker = buf[at + 1];
      if (marker === 0xe1 && buf.subarray(at + 4, at + 10).toString("latin1") === "Exif\0\0") turned = orientation(buf, at + 10) >= 5;
      // The frame headers (SOF0 to SOF15, but not DHT, JPG and DAC) hold the size.
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        const [w, h] = [buf.readUInt16BE(at + 7), buf.readUInt16BE(at + 5)];
        return turned ? [h, w] : [w, h];
      }
      at += 2 + buf.readUInt16BE(at + 2);
    }
  }
  if (buf.subarray(0, 4).toString("latin1") === "RIFF" && buf.subarray(8, 12).toString("latin1") === "WEBP") {
    const chunk = buf.subarray(12, 16).toString("latin1");
    if (chunk === "VP8X") return [buf.readUIntLE(24, 3) + 1, buf.readUIntLE(27, 3) + 1];
    if (chunk === "VP8L") {
      const bits = buf.readUInt32LE(21);
      return [(bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1];
    }
    if (chunk === "VP8 ") return [buf.readUInt16LE(26) & 0x3fff, buf.readUInt16LE(28) & 0x3fff];
  }
  throw new Fail("The picture is not a PNG, GIF, JPEG or WebP.");
}
