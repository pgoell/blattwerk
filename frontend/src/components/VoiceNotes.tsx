import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import { useObjectUrl } from "./useObjectUrl";

type Props = { clips: Blob[]; onChange: (clips: Blob[]) => void; stopper?: Ref<() => boolean> };

// Set when the form shut while a clip was recording: the next opening of the form says the clip was kept.
export const lost = { recording: false };

export default function VoiceNotes({ clips, onChange, stopper }: Props) {
  const recorder = useRef<MediaRecorder | null>(null);
  const mic = useRef<MediaStream | null>(null);
  const gone = useRef(false);
  const asking = useRef(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  // The stop handler runs long after the click, so it reads the latest clips from here.
  const latest = useRef(clips);
  latest.current = clips;

  // Shut in the middle of a recording, the mic goes off at once and the clip still comes through onChange.
  useEffect(() => {
    gone.current = false;
    return () => {
      gone.current = true;
      if (recorder.current?.state === "recording") {
        lost.recording = true;
        recorder.current.stop();
      }
      mic.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // Stops a recording, if there is one, and says whether there was.
  useImperativeHandle(stopper, () => () => {
    if (recorder.current?.state !== "recording") return false;
    recorder.current.stop();
    return true;
  });

  async function toggle() {
    if (recorder.current) return recorder.current.stop();
    // A second click while the browser asks would open a second mic, which no stop reaches.
    if (asking.current) return;
    asking.current = true;
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Kein Zugriff aufs Mikrofon. Bitte in den Browser-Einstellungen erlauben.");
      return;
    } finally {
      asking.current = false;
    }
    // The form shut while the browser asked: no mic for a form that is gone.
    if (gone.current) return stream.getTracks().forEach((t) => t.stop());
    mic.current = stream;
    setError("");
    // Safari records mp4, the others webm.
    const type = ["audio/webm", "audio/mp4", "audio/ogg"].find((t) => MediaRecorder.isTypeSupported(t));
    const rec = new MediaRecorder(stream, type ? { mimeType: type } : {});
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      recorder.current = null;
      setRecording(false);
      onChange([...latest.current, new Blob(chunks, { type: rec.mimeType })]);
    };
    rec.start();
    recorder.current = rec;
    setRecording(true);
  }

  return (
    <>
      <button type="button" className={recording ? "rec on" : "rec"} onClick={toggle}>
        {recording ? "■ Aufnahme beenden" : "● Aufnahme starten"}
      </button>
      {error && <p className="hint">{error}</p>}
      <ul className="clips">
        {clips.map((clip, i) => (
          <li key={i}>
            <Clip blob={clip} />
            <button type="button" className="plain" onClick={() => onChange(clips.filter((c) => c !== clip))}>
              Löschen
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

function Clip({ blob }: { blob: Blob }) {
  return <audio controls src={useObjectUrl(blob)} />;
}
