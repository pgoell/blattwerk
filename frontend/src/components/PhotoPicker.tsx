import { useObjectUrl } from "./useObjectUrl";

// `name` is what one picture is called: a page of a sheet unless said otherwise.
type Props = { photos: File[]; onChange: (photos: File[]) => void; name?: string };

export default function PhotoPicker({ photos, onChange, name = "Seite" }: Props) {
  return (
    <>
      <label className="pick">
        ＋ Foto hinzufügen
        <input
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => {
            onChange([...photos, ...(e.target.files ?? [])]);
            e.target.value = "";
          }}
        />
      </label>
      <div className="grid">
        {photos.map((photo, i) => (
          <figure key={i}>
            <Thumb file={photo} />
            <button type="button" aria-label={`${name} ${i + 1} entfernen`} onClick={() => onChange(photos.filter((p) => p !== photo))}>
              ×
            </button>
            <figcaption>{name} {i + 1}</figcaption>
          </figure>
        ))}
      </div>
    </>
  );
}

function Thumb({ file }: { file: File }) {
  return <img src={useObjectUrl(file)} alt="" />;
}

// Phone photos run to several MB each. Shrink to 2400 px on the long edge as
// JPEG, which is plenty to read a printed sheet; send the original if the
// browser cannot decode it.
export async function shrink(file: File): Promise<Blob> {
  try {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, 2400 / Math.max(bmp.width, bmp.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.85));
    return blob ?? file;
  } catch {
    return file;
  }
}
