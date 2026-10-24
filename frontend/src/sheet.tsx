// The sheet document and how a page of it draws, shared by the editor, the list's thumbnails and the PDF.
// The parts live under sheet/. The names here are the ones the rest of the app already imports.

export { KARO, PT, mathsHeight } from "./height";
export { decimalsOf } from "./decimal";
export { MARGIN, K, turned, dir, tall, fitWidth } from "./sheet/box";
export type { Box, Kind, Corner, Align, Valign } from "./sheet/box";
export { TINTS, GREYS, FONTS, fontOf, fontScale, dottedFamily, traceOf, fadeOf, fadeAt, FONT_GROUPS, RULINGS, kindOf, houseOf, houseTintOf, bandOf, bandColorOf, shade, HOUSE, houseWidth, indentOf, rowsOf, colsOf, keepsFractions, writtenStyle, textStyle, inset } from "./sheet/look";
export type { Font, Ruling, Tints, Trace, Fade } from "./sheet/look";
export { listColsOf, holesOf, lineOf, isLine, far, boxed, parasOf, shownParas, stored, listed, cleared, symbol } from "./sheet/text";
export type { List, Run, Para, TextProps, TextBlock, ShapeBlock } from "./sheet/text";
export { startOf, listOf, tied, foldsOf, squares, rowsNeeded, lengthened } from "./sheet/ruling";
export type { ListMode, RulingBlock } from "./sheet/ruling";
export { FIELDS, sizeOf, EMPTY, read, wordsIn } from "./sheet/doc";
export type { NameBlock, PointsBlock, SymbolBlock, ImageBlock, Block, Axis, Guides, Page, Ground, Doc, PageNumbers, Sheet } from "./sheet/doc";
export { SIGNS } from "./sheet/maths";
export type { Op, Range, Grid, Calc, Side, Compare, Exercise, Limits, Made, MathsProps, MathsBlock } from "./sheet/maths";
export { sum, spliced } from "./sheet/table";
export type { TableBlock } from "./sheet/table";
export type { Ways, SuchselProps, SuchselBlock, Typed, ZahlenmauerProps, ZahlenmauerBlock, RechendreieckBlock, ZahlenhausBlock, ZahlenketteBlock, PfeilbildBlock, OperatorfeldBlock, RechenradBlock, RechentabelleBlock, MagischesQuadratBlock, MalquadratBlock, ZerlegungsfeldBlock, HalbschriftlichBlock, ZehnerfeldBlock, ZahlenstrahlBlock, HunderterfeldBlock, UhrBlock, SelbstkontrolleBlock } from "./sheet/tasks";
export { LOOKS, lookOf, counts, numbers, Count } from "./sheet/numbering";
export { Words, Whole, useBreaks } from "./sheet/context";
export { reachOf, lowest, rightmost, overFoot, stepOf, fromOf, tailOf, tailReach, innerOf, tipOf, fitOf, radiusOf, handleOf, adjusted } from "./sheet/shape";
export { splitting, useSplitter, pairOf, bowed } from "./sheet/bows";
export { Numbers } from "./sheet/rich";
export { subscribe, scaleOf } from "./sheet/mathsView";
export { Draw, Mark, pageNumbersOf, folioOf, PageNumber, Paper } from "./sheet/page";
export { score, ScoreInput } from "./sheet/score";
