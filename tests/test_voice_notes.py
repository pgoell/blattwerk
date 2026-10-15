"""The feedback form's voice notes stop the mic when the form shuts while recording (#656)."""

from playwright.sync_api import expect
from ui import TEXT, box

FORM = "dialog.feedback"
CLIPS = "ul.clips li"
KEPT = "Deine Aufnahme lief noch, als das Formular zuging. Sie ist unten gespeichert."
DONE = "Aufnahme beendet. Hör sie dir an und drück dann nochmal auf Abschicken."
REFUSED = "Kein Zugriff aufs Mikrofon. Bitte in den Browser-Einstellungen erlauben."

# A microphone that counts its tracks in window.__tracks, and a recorder that stops like the
# real one: the clip comes a task after stop().
FAKE = """
(refuse) => {
  window.__tracks = [];
  const mic = async () => {
    if (refuse) throw new DOMException("denied", "NotAllowedError");
    const track = { stopped: false, stop() { this.stopped = true; } };
    window.__tracks.push(track);
    return { getTracks: () => [track] };
  };
  const devices = { getUserMedia: mic };
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: devices });
  window.MediaRecorder = class {
    static isTypeSupported() { return true; }
    constructor(stream, options) {
      this.mimeType = options?.mimeType ?? "audio/webm";
      this.state = "inactive";
    }
    start() { this.state = "recording"; }
    stop() {
      this.state = "inactive";
      setTimeout(() => {
        this.ondataavailable?.({ data: new Blob(["x"]) });
        this.onstop?.();
      }, 0);
    }
  };
}
"""


def button(page):
    return page.get_by_label("Feedback", exact=True)


def form(page):
    return page.locator(FORM)


def open_form(page, refuse=False):
    """Installs the fake, which the record button reads only when it is pressed."""
    page.evaluate(FAKE, refuse)
    button(page).click()
    expect(form(page)).to_be_visible()


def record(page):
    form(page).get_by_role("button", name="● Aufnahme starten").click()
    expect(form(page).get_by_role("button", name="■ Aufnahme beenden")).to_be_visible()


def stopped(page):
    return page.evaluate("window.__tracks.map((t) => t.stopped)")


def mic_off(page, mics=1):
    """Waits until the page has asked for `mics` microphones and every track of them is stopped."""
    page.wait_for_function(
        "(n) => window.__tracks.length === n && window.__tracks.every((t) => t.stopped)", arg=mics
    )


def test_escape_while_recording_shuts_the_form_and_stops_the_mic(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page)
    record(page)
    page.keyboard.press("Escape")
    expect(form(page)).to_have_count(0)
    mic_off(page)


def test_close_button_while_recording_stops_the_mic(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page)
    record(page)
    form(page).get_by_role("button", name="Schließen").click()
    expect(form(page)).to_have_count(0)
    mic_off(page)


def test_submit_while_recording_stops_the_mic_and_keeps_the_clip_unsent(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page)
    record(page)
    form(page).get_by_role("button", name="Abschicken").click()
    expect(form(page).get_by_role("status")).to_have_text(DONE)
    expect(form(page)).to_be_visible()
    expect(page.locator(CLIPS)).to_have_count(1)
    mic_off(page)


def test_click_beside_the_form_while_recording_keeps_it_open(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page)
    record(page)
    page.mouse.click(5, 5)
    expect(form(page)).to_be_visible()
    expect(form(page).get_by_role("button", name="■ Aufnahme beenden")).to_be_visible()


def test_form_shut_while_recording_says_the_clip_was_kept_when_opened_again(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page)
    record(page)
    page.keyboard.press("Escape")
    expect(form(page)).to_have_count(0)
    button(page).click()
    expect(form(page)).to_be_visible()
    expect(form(page).get_by_role("status")).to_have_text(KEPT)
    expect(page.locator(CLIPS)).to_have_count(1)
    expect(form(page).get_by_role("button", name="● Aufnahme starten")).to_be_visible()
    record(page)
    form(page).get_by_role("button", name="■ Aufnahme beenden").click()
    expect(page.locator(CLIPS)).to_have_count(2)
    mic_off(page, 2)


def test_stopped_by_hand_then_escape_keeps_one_clip_and_no_kept_note(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page)
    record(page)
    form(page).get_by_role("button", name="■ Aufnahme beenden").click()
    expect(page.locator(CLIPS)).to_have_count(1)
    page.keyboard.press("Escape")
    expect(form(page)).to_have_count(0)
    button(page).click()
    expect(form(page)).to_be_visible()
    expect(page.locator(CLIPS)).to_have_count(1)
    expect(form(page)).to_be_visible()
    expect(form(page)).not_to_contain_text("Deine Aufnahme lief noch")


def test_refused_mic_shows_the_hint_and_records_nothing(editor):
    page = editor(box("a", "text", TEXT))
    open_form(page, refuse=True)
    form(page).get_by_role("button", name="● Aufnahme starten").click()
    expect(form(page).locator("p.hint")).to_have_text(REFUSED)
    expect(form(page).get_by_role("button", name="● Aufnahme starten")).to_be_visible()
    page.keyboard.press("Escape")
    expect(form(page)).to_have_count(0)
    assert stopped(page) == []
