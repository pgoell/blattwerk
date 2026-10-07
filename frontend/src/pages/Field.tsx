// The field a text is typed in: ProseMirror, with a document as flat as the sheet's own paragraphs. Only the
// editor loads it; the sheet draws without it.
import { useLayoutEffect, useRef, type RefObject } from "react";
import { baseKeymap, chainCommands, splitBlockAs } from "prosemirror-commands";
import { keymap } from "prosemirror-keymap";
import { Schema, type Attrs, type MarkSpec, type Node } from "prosemirror-model";
import { EditorState, Selection, type Command } from "prosemirror-state";
import { EditorView } from "prosemirror-view";
import { parasOf, stored, type List, type Para, type Run, type TextProps } from "../sheet";

// The look a run can have of its own.
export type Marks = Omit<Run, "text">;
// What the format panel shows of the field: the list the caret stands in, and the look of the picked words. With
// only a caret there are none, and the panel's settings are the whole block's.
export type Picked = { list?: List; marks?: Marks };

// A colour is drawn first and so lies around the others: an underline takes the colour of its words.
const NAMES = ["color", "bold", "italic", "underline"] as const;
const HEX = /^#[0-9a-f]{6}$/i;
// A mark holds what its run holds, in `v`: on or off for bold and italic, on for an underline, a colour.
type Name = (typeof NAMES)[number];
const fits = (name: Name, v: unknown) =>
  name === "color" ? typeof v === "string" && HEX.test(v) : name === "underline" ? v === true : typeof v === "boolean";
// A mark is drawn as a span that says what it is, so a copy within the field keeps it. Of a paste from elsewhere
// only bold, italic and underline stay, by their tags.
const mark = (name: Name, css: (v: string | boolean) => string, tag?: string): MarkSpec => ({
  attrs: { v: { default: true } },
  toDOM: (m) => ["span", { [`data-${name}`]: String(m.attrs.v), style: css(m.attrs.v) }, 0],
  parseDOM: [
    {
      tag: `span[data-${name}]`,
      getAttrs(el) {
        const said = el.getAttribute(`data-${name}`)!;
        const v = name === "color" ? said : said === "true";
        return fits(name, v) && { v };
      },
    },
    // Google Docs wraps all it copies in a <b> that is not bold.
    ...(tag ? [{ tag, getAttrs: (el: HTMLElement) => el.style.fontWeight !== "normal" && null }] : []),
  ],
});
const schema = new Schema({
  nodes: {
    doc: { content: "paragraph+" },
    paragraph: {
      content: "text*",
      attrs: { list: { default: null }, level: { default: 0 } },
      toDOM: (n) => ["p", { "data-list": n.attrs.list, "data-level": n.attrs.level || null }, 0],
      parseDOM: [{ tag: "p", getAttrs: (el) => ({ list: ["bullet", "number"].includes(el.dataset.list!) ? el.dataset.list : null, level: Math.min(2, +el.dataset.level! || 0) }) }],
    },
    text: {},
  },
  marks: {
    color: mark("color", (v) => `color: ${v}`),
    bold: mark("bold", (v) => `font-weight: ${v ? 700 : 400}`, "b, strong"),
    italic: mark("italic", (v) => `font-style: ${v ? "italic" : "normal"}`, "i, em"),
    underline: mark("underline", () => "text-decoration: underline", "u"),
  },
});

const docOf = (p: TextProps) =>
  schema.node(
    "doc",
    null,
    parasOf(p).map((para) =>
      schema.node(
        "paragraph",
        { list: para.list ?? null, level: para.level ?? 0 },
        para.runs.filter((r) => r.text).map((r) => schema.text(r.text, NAMES.filter((name) => fits(name, r[name])).map((name) => schema.mark(name, { v: r[name] })))),
      ),
    ),
  );
// The field's document as the sheet stores it.
function read(doc: Node) {
  const paras: Para[] = [];
  doc.forEach((p) => {
    const runs: Run[] = [];
    p.forEach((t) => runs.push({ text: t.text!, ...Object.fromEntries(t.marks.map((m) => [m.type.name, m.attrs.v])) }));
    paras.push({ runs, ...(p.attrs.list && { list: p.attrs.list, ...(p.attrs.level && { level: p.attrs.level }) }) });
  });
  return stored(paras);
}
// The look of the picked words over the block's own, `base`: a setting is on when any of them has it. With only a
// caret, the look of what is typed next.
function looks(state: EditorState, base: TextProps) {
  const { from, to, empty, $from } = state.selection;
  const out: Marks = {};
  const see = (marks: Node["marks"]) => {
    for (const name of NAMES) {
      const m = schema.marks[name].isInSet(marks);
      if (name === "color") out.color ??= m?.attrs.v ?? base.color;
      else out[name] ||= m ? m.attrs.v : !!base[name];
    }
  };
  if (empty) see(state.storedMarks ?? $from.marks());
  else
    state.doc.nodesBetween(from, to, (n) => {
      if (n.isText) see(n.marks);
    });
  return out;
}
const picked = (state: EditorState, base: TextProps): Picked => ({
  list: state.selection.$from.parent.attrs.list ?? undefined,
  marks: state.selection.empty ? undefined : looks(state, base),
});
// Gives the picked words a look, or with only a caret what is typed next. Bold and italic as the block has them
// need no mark. `key` merges a run of changes into one undo step.
export function tint(view: EditorView, props: Marks, base: TextProps, key = "") {
  const { from, to, empty } = view.state.selection;
  const tr = view.state.tr.setMeta("key", key);
  for (const name of NAMES) {
    const v = props[name];
    if (v === undefined) continue;
    const type = schema.marks[name];
    if (name === "color" || (name === "underline" ? v : v !== !!base[name])) {
      if (empty) tr.addStoredMark(type.create({ v }));
      else tr.addMark(from, to, type.create({ v }));
    } else if (empty) tr.removeStoredMark(type);
    else tr.removeMark(from, to, type);
  }
  view.dispatch(tr);
}
// Changes the paragraphs the selection touches, in one undo step.
function paras(state: EditorState, to: (attrs: Attrs) => Attrs | undefined) {
  const tr = state.tr.setMeta("key", "");
  state.doc.nodesBetween(state.selection.from, state.selection.to, (n, pos) => {
    const attrs = n.isTextblock && to(n.attrs);
    if (attrs) tr.setNodeMarkup(pos, null, attrs);
  });
  return tr;
}
// Makes the paragraphs items of a list, or plain again when the first of them is such an item already.
export function list(view: EditorView, kind: List) {
  const on = view.state.selection.$from.parent.attrs.list === kind;
  view.dispatch(paras(view.state, (attrs) => (on ? {} : { ...attrs, list: kind })));
}
// Tab moves the items of a list in by a level, Shift+Tab out. In plain text the key stays the browser's.
const shift = (by: number): Command => (state, dispatch) => {
  let items = 0;
  const tr = paras(state, (attrs) => (attrs.list && ++items ? { ...attrs, level: Math.max(0, Math.min(2, attrs.level + by)) } : undefined));
  if (items) dispatch?.(tr);
  return items > 0;
};
// Backspace at the start of an item, or Enter in an item with no text, ends the list there.
const leave = (blank: boolean): Command => (state, dispatch) => {
  const { empty, $from } = state.selection;
  if (!empty || !$from.parent.attrs.list || $from.parentOffset || (blank && $from.parent.content.size)) return false;
  dispatch?.(paras(state, () => ({})));
  return true;
};

type Props = {
  // The editor reaches the field through this, for the format panel.
  view: RefObject<EditorView | null>;
  props: TextProps;
  // Whether the field says "Text" while it is empty.
  hint: boolean;
  change: (props: Pick<TextProps, "text" | "rich">, key: string) => void;
  pick: (picked?: Picked) => void;
  blur: () => void;
  end: () => void;
};

// It has no history of its own: every change goes to the editor, whose undo then puts the text back from outside.
export default function Field({ view, props, hint, ...on }: Props) {
  const el = useRef<HTMLDivElement>(null);
  // What the field last took or gave: a text that differs has changed outside it.
  const known = useRef<Pick<TextProps, "text" | "rich">>(props);
  // The field lives across renders and calls what the latest one passed.
  const now = useRef({ props, ...on });
  now.current = { props, ...on };
  const flip = (name: "bold" | "italic" | "underline"): Command => (state, _, field) => {
    tint(field!, { [name]: !looks(state, now.current.props)[name] }, now.current.props);
    return true;
  };
  const stateOf = (p: TextProps, doc = docOf(p)) =>
    EditorState.create({
      doc,
      // A copy, or a text put back by undo, would start with the caret before the text.
      selection: Selection.atEnd(doc),
      plugins: [
        keymap({
          "Mod-b": flip("bold"),
          "Mod-i": flip("italic"),
          "Mod-u": flip("underline"),
          Tab: shift(1),
          "Shift-Tab": shift(-1),
          // A new paragraph is what the one before it is: the next item of its list.
          Enter: chainCommands(leave(true), splitBlockAs((n) => ({ type: n.type, attrs: n.attrs }))),
          Backspace: chainCommands(leave(false), baseKeymap.Backspace),
          Escape: () => (now.current.end(), true),
        }),
        keymap(baseKeymap),
      ],
    });

  useLayoutEffect(() => {
    const field = new EditorView(el.current!, {
      state: stateOf(props),
      dispatchTransaction(tr) {
        const state = field.state.apply(tr);
        field.updateState(state);
        if (tr.docChanged) {
          known.current = read(state.doc);
          // Typing merges into one undo step; a look or a list is a step of its own.
          now.current.change(known.current, tr.getMeta("key") ?? "text");
        }
        now.current.pick(picked(state, now.current.props));
      },
      handleDOMEvents: { blur: () => now.current.blur() },
      // The field knows no line break within a paragraph.
      transformPastedHTML: (html) => html.replace(/<br\b[^>]*>/gi, " "),
    });
    view.current = field;
    field.focus();
    on.pick(picked(field.state, props));
    return () => {
      field.destroy();
      view.current = null;
      now.current.pick();
    };
  }, []);
  useLayoutEffect(() => {
    if (props.text === known.current.text && props.rich === known.current.rich) return;
    known.current = props;
    view.current!.updateState(stateOf(props));
    on.pick(picked(view.current!.state, props));
  }, [props.text, props.rich]);

  return <div ref={el} className="rich" data-hint={hint && !props.text ? "" : undefined} />;
}
