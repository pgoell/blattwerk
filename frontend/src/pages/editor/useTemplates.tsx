// Saving the sheet as a template.
import { useRef, useState } from "react";
import { post, type Refusal } from "../../api";
import type { Template } from "./palette";
import { attempt } from "../../fault";
import { signed } from "../../saves";
import { usePrint } from "./usePrint";

export function useTemplates(session: ReturnType<typeof usePrint>) {
  const live = session.live;
  const name = session.name;
  const setName = session.setName;
// A template stored with the session run out brings the login. A second press while one is on its way
  // stores no second template. The name stays until the template is stored.
  const storing = useRef(false);
  // The name of the template stored last, which the panel says.
  const [stored, setStored] = useState("");
  async function store() {
    const made = { name: name.trim() };
    await attempt(
      "Die Vorlage konnte nicht gespeichert werden.",
      async () => {
        if (storing.current) return;
        storing.current = true;
        try {
          // The page as it stands at the try: a later one stores what the teacher sees then.
          const saved = await signed(post<Template>("/templates", { ...made, doc: live.current.doc }));
          setStored(saved.name);
          setName((now) => (now.trim() === made.name ? "" : now));
        } finally {
          storing.current = false;
        }
      },
      // A template the server refuses names what is wrong in it, and a try again would end the same.
      (_, e) => {
        const problems = (e as Refusal).problems;
        return problems ? `Die Vorlage konnte nicht gespeichert werden: das Blatt passt nicht zum Format. ${problems.join("; ")}` : undefined;
      },
    );
  }
    return Object.assign(session, { storing, store, stored });
}
