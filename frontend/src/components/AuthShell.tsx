import type { ReactNode } from "react";
import Logo from "./Logo";

// The logged-out pages: what Blattomat is on one side, the form on the other.
export default function AuthShell({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  return (
    <main className="auth">
      <section className="pitch">
        <Logo />
        <p className="claim">Arbeitsblätter, wie du sie brauchst.</p>
        <p className="lead">
          Ein Editor für die Grundschule, mit Lineaturen, Schulschriften und Rechenaufgaben nach Maß. Er entsteht
          gerade, zusammen mit Lehrkräften.
        </p>
        <div className="sample" aria-hidden="true">
          <div className="sample-head"><span>Name:</span><span>Datum:</span></div>
          <strong>Rechnen bis 20</strong>
          <div className="sample-sums">
            <span>7 + 5 =</span><span>14 − 6 =</span>
            <span>9 + 8 =</span><span>17 − 9 =</span>
            <span>6 + 6 =</span><span>12 − 4 =</span>
          </div>
          <div className="sample-lines" />
        </div>
      </section>
      <section className="auth-form">
        <h1>{title}</h1>
        <p className="lead">{lead}</p>
        {children}
      </section>
    </main>
  );
}
