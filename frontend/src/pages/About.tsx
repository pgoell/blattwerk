import { Link } from "react-router";

// The symbols' and the fonts' licenses ask for these credits; the same stand in NOTICE.
export default function About() {
  return (
    <main>
      <p><Link to="/">← Blattwerk</Link></p>
      <h1>Über Blattwerk</h1>
      <p className="lead">Arbeitsblätter für die Grundschule. Blattwerk nutzt freie Symbole und Schriften:</p>
      <div className="card">
        <label>Symbole</label>
        <p>
          Alle Symbole stammen von <a href="https://openmoji.org">OpenMoji</a>, dem quelloffenen Emoji- und Icon-Projekt,
          und stehen unter der Lizenz <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.de">CC BY-SA 4.0</a>.
          Blattwerk zeigt sie unverändert. <a href="/openmoji/LICENSE.txt">Lizenztext</a>
        </p>
      </div>
      <div className="card">
        <label>Schriften</label>
        <p>
          Playwrite DE Grund, DE VA, DE SAS und DE LA: Copyright 2023 The Playwrite Project Authors
          (<a href="https://github.com/TypeTogether/Playwrite">TypeTogether</a>). <a href="/fonts/playwrite/OFL.txt">Lizenztext</a>
        </p>
        <p>
          Andika: Copyright 2004 bis 2025 <a href="https://software.sil.org/andika/">SIL Global</a>. <a href="/fonts/andika/OFL.txt">Lizenztext</a>
        </p>
        <p className="hint">Alle Schriften stehen unter der SIL Open Font License 1.1.</p>
      </div>
    </main>
  );
}
