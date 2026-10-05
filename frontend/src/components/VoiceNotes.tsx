import { useRef, useState } from "react";
import { useObjectUrl } from "./useObjectUrl";

type Props = { clips: Blob[]; onChange: (clips: Blob[]) => void };

export default function VoiceNotes({ clips, onChange }: Props) {
  const recorder = useRef<MediaRecorder | null>(null);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  // The stop handler runs long after the click, so it reads the latest clips from here.
  const latest = useRef(clips);
  latest.current = clips;

  async function toggle() {
    if (recorder.current) return recorder.current.stop();
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Kein Zugriff aufs Mikrofon. Bitte in den Browser-Einstellungen erlauben.");
      return;
    }
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
