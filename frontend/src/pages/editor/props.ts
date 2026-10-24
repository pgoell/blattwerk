import type { RefObject } from "react";
import type { User } from "../../api";
import type { Sheet } from "../../sheet";
import type { Opened } from "./palette";

// What the route hands the editor of one sheet.
export type EditorProps = {
  file: Sheet;
  user: User;
  reload: () => void;
  over: () => void;
  choice?: "busy" | "failed";
  asNew: () => void;
  discard: () => void;
  renew: (sheet: Sheet, variants?: Opened) => void;
  opened?: Opened;
  waiting: RefObject<boolean | undefined>;
};
