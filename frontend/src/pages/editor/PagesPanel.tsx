// The pages, the ground and the templates.
import type { CSSProperties } from "react";
import { CopyPlus, FilePlus, FileX, Wallpaper, LayoutTemplate, Plus, X } from "lucide-react";
import { sizeOf } from "../../sheet";
import { next } from "../../cells";
import { holdName, Tool } from "./Tool";
import { span, Thumb } from "./palette";
import { useTools } from "./useTools";


export default function PagesPanel({ s: session }: { s: ReturnType<typeof useTools> }) {
  const addPage = session.addPage;
  const aim = session.aim;
  const brand = session.brand;
  const chosenNow = session.chosenNow;
  const copyPages = session.copyPages;
  const ctrl = session.ctrl;
  const ctrlMenu = session.ctrlMenu;
  const dragged = session.dragged;
  const file = session.file;
  const from = session.from;
  const group = session.group;
  const haul = session.haul;
  const k = session.k;
  const landing = session.landing;
  const leaf = session.leaf;
  const left = session.left;
  const page = session.page;
  const pageKey = session.pageKey;
  const pages = session.pages;
  const pressed = session.pressed;
  const quit = session.quit;
  const release = session.release;
  const removePages = session.removePages;
  const scrollEdge = session.scrollEdge;
  const setChosen = session.setChosen;
  const side = session.side;
  const small = session.small;
  const strip = session.strip;
  const style = session.style;
  const thumb = session.thumb;
  const thumbMenu = session.thumbMenu;
  const title = session.title;
  const tools = session.tools;
  const touch = session.touch;
  const tug = session.tug;
  const visit = session.visit;
  return (
    <>
      {/* A wide window's left panel has two tabs: the blocks that can go on the page, and the pages. The first is not
          called "Einfügen": that is the bar's button for what was copied. A narrower one has the
          pages alone, behind the bar's button, and the tools at the desk's foot. */}
      {(leaf || left) && (
        <aside className="left">
          {leaf && brand}
          {leaf && (
            <div className="tabs sides" role="tablist">
              {["Blöcke", "Seiten"].map((t) => (
                <button key={t} role="tab" data-tour={t} aria-selected={(t === "Seiten") === side} onClick={() => session.showLeft(t === "Seiten")}>
                  {t}
                </button>
              ))}
            </div>
          )}
          {leaf && !side && (
            <div className="insert" role="toolbar" aria-label="Einfügen" onPointerOver={(e) => holdName(e, e.currentTarget.parentElement!)}>
              {tools}
            </div>
          )}
          {left && (
          <>
          <div className="head">
            Seiten
            <span>
              <Tool icon={CopyPlus} label="Seite duplizieren" title="Seite duplizieren" onClick={() => copyPages()} />
              <Tool icon={FileX} label="Seite löschen" title="Seite löschen" disabled={chosenNow.length >= pages.length} onClick={() => removePages()} />
            </span>
          </div>
          {/* As many thumbnails in a row as fit, 12 px apart, in the 206 px that two take at first. */}
          <div className="pages" ref={strip} style={{ "--thumb": `${thumb}px` } as CSSProperties}>
            {pages.map((_, n) => (
              <button
                key={n}
                data-thumb={n}
                title="Ziehen verschiebt die Seite"
                className={[chosenNow.includes(n) && "on", n === haul?.from && "drag"].filter(Boolean).join(" ")}
                aria-pressed={chosenNow.includes(n)}
                // The click after a drag is the drag's end, not a visit. The next one, also by Enter, visits again.
                onClick={(e) => {
                  // Ctrl+click on a Mac is the right click. Its menu has already chosen the pages.
                  if (ctrlMenu.current) {
                    ctrlMenu.current = false;
                    dragged.current = false;
                    return;
                  }
                  if (!dragged.current) {
                    if (e.shiftKey) {
                      // From the page in use to this one; the page in use stays.
                      setChosen(Array.from({ length: Math.abs(n - page) + 1 }, (_, j) => Math.min(n, page) + j));
                    } else if (e.ctrlKey || e.metaKey) {
                      // Adds this page to the choice, or drops it; the last one stays.
                      const next = chosenNow.includes(n) ? (chosenNow.length > 1 ? chosenNow.filter((i) => i !== n) : chosenNow) : [...chosenNow, n].sort((a, b) => a - b);
                      if (next.includes(page)) setChosen(next);
                      else {
                        visit(next[0]);
                        setChosen(next);
                      }
                    } else {
                      visit(n);
                    }
                    // The keys of a thumbnail need its focus, and a click leaves it with the page.
                    e.currentTarget.focus({ preventScroll: true });
                  }
                  dragged.current = false;
                }}
                onKeyDown={(e) => pageKey(e, n)}
                // The mouse and the pen drag once they have moved 4 px. A finger holds first: see the listeners on the thumbnails.
                onPointerDown={(e) => {
                  dragged.current = false;
                  // A Ctrl+click's menu may have taken the click. The next press is a new one.
                  ctrlMenu.current = false;
                  touch.current = e.pointerType === "touch";
                  if (e.pointerType === "touch" || e.button) return;
                  tug.current = { from: n, x: e.clientX, y: e.clientY, ctrl: e.ctrlKey };
                  e.currentTarget.setPointerCapture(e.pointerId);
                }}
                onPointerMove={(e) => {
                  const t = tug.current;
                  if (e.pointerType === "touch" || !t) return;
                  if (t.slot !== undefined || Math.hypot(e.clientX - t.x, e.clientY - t.y) >= 4) {
                    aim(e.clientX, e.clientY);
                    scrollEdge(e.clientX, e.clientY);
                  }
                }}
                onPointerUp={(e) => e.pointerType !== "touch" && release()}
                onPointerCancel={(e) => e.pointerType !== "touch" && quit()}
                // A held finger would open the browser's menu and end the touch. The mouse gets the page's menu.
                // A Ctrl+click on a Mac is that right click. Chrome can send the press as the main button, so a
                // drag has already started, and this event comes while the button is still down. A drag that has
                // not moved is that click: drop it and open the menu. The click of the press must not also choose.
                onContextMenu={(e) => {
                  // The press recorded Ctrl, or this event carries it. Either one is the Mac right click.
                  const asRight = !!(e.ctrlKey || tug.current?.ctrl);
                  if (asRight && tug.current && tug.current.slot === undefined) quit();
                  if (tug.current || !touch.current) e.preventDefault();
                  if (!tug.current && !touch.current) {
                    if (asRight) ctrlMenu.current = true;
                    thumbMenu(n, e.clientX, e.clientY);
                  }
                }}
              >
                {/* The thumbnails draw late: a new page has its button before its picture. */}
                {n < small.pages.length && <Thumb doc={small} k={thumb / sizeOf(small, n)[0]} page={n} />}
                Seite {n + 1}
                {/* The line where the dragged page will land: before this thumbnail, or after it. */}
                {haul && haul.slot - +haul.after === n && (
                  <span className={haul.after ? "mark end" : "mark"} data-to={landing(haul.from, haul.slot)} />
                )}
              </button>
            ))}
            <button onClick={() => addPage()}>
              <i style={{ aspectRatio: small.landscape ? "297 / 210" : "210 / 297" }}>
                <Plus size={16} aria-hidden />
              </i>
              Neue Seite
            </button>
          </div>
          </>
          )}
        </aside>
      )}
    </>
  );
}
