// The editor of one sheet. The hooks own the behaviour; the panels own what is drawn.
import type { RefObject } from "react";
import type { User } from "../../api";
import type { Sheet } from "../../sheet";
import { useDocument } from "./useDocument";
import { useSelectionState } from "./useSelectionState";
import { useLayoutState } from "./useLayoutState";
import { useSelection } from "./useSelection";
import { useTextFit } from "./useTextFit";
import { useField } from "./useField";
import { useDrop } from "./useDrop";
import { useKeys } from "./useKeys";
import { useKeyCommands } from "./useKeyCommands";
import { usePointers } from "./usePointers";
import { useDocChange } from "./useDocChange";
import { useBlockStyle } from "./useBlockStyle";
import { useBrush } from "./useBrush";
import { usePages } from "./usePages";
import { usePageScroll } from "./usePageScroll";
import { useInsert } from "./useInsert";
import { useClipboard } from "./useClipboard";
import { useArrange } from "./useArrange";
import { useMove } from "./useMove";
import { useTable } from "./useTable";
import { useGuides } from "./useGuides";
import { usePrint } from "./usePrint";
import { useTemplates } from "./useTemplates";
import { usePick } from "./usePick";
import { useMenus } from "./useMenus";
import { useTools } from "./useTools";
import type { Opened } from "./palette";
import type { EditorProps } from "./props";
import EditorMain from "./EditorMain";
import EditorBar from "./EditorBar";
import PagesPanel from "./PagesPanel";
import Stage from "./Stage";
import FormatPanel from "./FormatPanel";
import EditorMenus from "./EditorMenus";

export default function Canvas({ file, user, reload, over, choice, asNew, discard, renew, opened, waiting }: { file: Sheet; user: User; reload: () => void; over: () => void; choice?: "busy" | "failed"; asNew: () => void; discard: () => void; renew: (sheet: Sheet, variants?: Opened) => void; opened?: Opened; waiting: RefObject<boolean | undefined> }) {
  const props: EditorProps = { file, user, reload, over, choice, asNew, discard, renew, opened, waiting };
  const useDocumentOut = useDocument(props);
  const useSelectionStateOut = useSelectionState(useDocumentOut);
  const useLayoutStateOut = useLayoutState(useSelectionStateOut);
  const useSelectionOut = useSelection(useLayoutStateOut);
  const useTextFitOut = useTextFit(useSelectionOut);
  const useFieldOut = useField(useTextFitOut);
  const useDropOut = useDrop(useFieldOut);
  const useKeysOut = useKeys(useDropOut);
  const useKeyCommandsOut = useKeyCommands(useKeysOut);
  const usePointersOut = usePointers(useKeyCommandsOut);
  const useDocChangeOut = useDocChange(usePointersOut);
  const useBlockStyleOut = useBlockStyle(useDocChangeOut);
  const useBrushOut = useBrush(useBlockStyleOut);
  const usePagesOut = usePages(useBrushOut);
  const usePageScrollOut = usePageScroll(usePagesOut);
  const useInsertOut = useInsert(usePageScrollOut);
  const useClipboardOut = useClipboard(useInsertOut);
  const useArrangeOut = useArrange(useClipboardOut);
  const useMoveOut = useMove(useArrangeOut);
  const useTableOut = useTable(useMoveOut);
  const useGuidesOut = useGuides(useTableOut);
  const usePrintOut = usePrint(useGuidesOut);
  const useTemplatesOut = useTemplates(usePrintOut);
  const usePickOut = usePick(useTemplatesOut);
  const useMenusOut = useMenus(usePickOut);
  const session = useTools(useMenusOut);
  return (
    <EditorMain s={session}>
      <EditorBar s={session} />
      <PagesPanel s={session} />
      <Stage s={session} />
      <FormatPanel s={session} />
      <EditorMenus s={session} />
    </EditorMain>
  );
}
