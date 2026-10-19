"""What must never stand in a public issue. Standard library only."""

import re
import unicodedata

# Generic local parts and labels: "info" or "schule" say nothing about a person.
STOP = set(
    """info mail post kontakt admin office lehrer lehrerin schule grundschule
    sekretariat verwaltung""".split()  # noqa: SIM905 (a word list reads better than a literal)
)
# A free mail provider says nothing about a school, so its domain is not checked.
PROVIDERS = set(
    """gmail.com googlemail.com gmx.de gmx.net web.de t-online.de outlook.com outlook.de
    hotmail.com hotmail.de yahoo.com yahoo.de icloud.com me.com posteo.de mailbox.org
    freenet.de live.de live.com aol.com proton.me protonmail.com""".split()  # noqa: SIM905
)

# English sentence starts: a send may be English, so these are no names.
SAID = set(
    """The And But For Not You Why How Can When What This That There With""".split()  # noqa: SIM905
) | {"Blattomat"}  # the app's own name, which an AI's send names

# The app's own block names (Editor.tsx, NAMES and PLURALS): the app's words, no person's.
BLOCK_NAMES = set(
    """Text Texte Bild Bilder Symbol Symbole Lineatur Lineaturen Suchsel Zahlenmauer
    Zahlenmauern Zahlenhaus Zahlenhäuser Rechendreieck Rechendreiecke Zahlenstrahl
    Zahlenstrahlen Zahlenkette Zahlenketten Pfeilbild Pfeilbilder
    Hunderterfeld Hunderterfelder Uhr Uhren Selbstkontrolle
    Selbstkontrollen Namenszeile Namenszeilen Punkte Punkteblöcke Rechnen Rechenblöcke
    Form Formen Tabelle Tabellen""".split()  # noqa: SIM905 (a word list reads better than a literal)
)

# (?<=_) lets "user_id=3" hit, since \b does not sit between "_" and "i".
ID = re.compile(
    r"(?:\b|(?<=_))(user\w*|nutzer\w*|benutzer\w*|konto\w*|account\w*|teacher\w*|lehrer\w*|uid|id)"
    r"[\s#:=/_.-]*(?:(?:nr|no|nummer|number|id)\b[\s#:=/_.-]*)?\d+\b",
    re.IGNORECASE,
)
FILE_GENERIC = re.compile(
    r"feedback\.json|\b(photo|audio|screenshot)-\d+\.\w+|/blatt/\d+"
    r"|\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}",
    re.IGNORECASE,
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LINK = re.compile(r"https?://|\bwww\.", re.IGNORECASE)
MENTION = re.compile(r"(?<!\w)@\w")
CLASS = re.compile(
    r"\b(Klasse|Kl\.|class|grade|Jahrgang|Jahrgangsstufe)\s*\d{1,2}\s?[a-zA-Z]?\b"
    r"|\b(1[0-3]|[1-9])[a-eA-E]\b",
    re.IGNORECASE,
)
# Case-sensitive: a school name starts with a capital.
SCHOOL = [
    re.compile(r"[A-ZÄÖÜ]\w+-(Grund|Gesamt|Real|Haupt|Ober|Förder)?[Ss]chule\b"),
    re.compile(r"[Ss]chule\s+(am|an der|in|im|zu|auf)\s+[A-ZÄÖÜ]"),
    re.compile(r"\b(Grundschule|GS|School)\s+[A-ZÄÖÜ][a-zäöüß]+"),
    re.compile(r"\b[A-Z][a-z]+\s+(Primary|Elementary)\s+School\b"),
]


def _clean(s: str) -> str:
    # Full-width forms become plain letters; zero-width marks (Cf) go.
    s = unicodedata.normalize("NFKC", s)
    return "".join(c for c in s if unicodedata.category(c) != "Cf")


def _fold(s: str) -> str:
    # Accents and case do not count: "Müller", "MULLER" and "muller" are one name.
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _whole_word(piece: str, text: str, flags: int = re.IGNORECASE) -> bool:
    # Not glued to other letters: "kraus" hits "kraus98", not "krause".
    pattern = rf"(?<![^\W\d_]){re.escape(piece)}(?![^\W\d_])"
    return re.search(pattern, text, flags) is not None


def _send_word(source: str, text: str) -> bool:
    # A capitalised word of the send (a name, a noun) kept in the same spelling.
    # Case-sensitive: "Text" in the send is no hit for "text" in English.
    words = set(re.findall(r"(?<![^\W\d_])[A-ZÄÖÜ][a-zäöüß]{2,}(?![^\W\d_])", source))
    words -= SAID | BLOCK_NAMES
    return any(_whole_word(w, text, 0) for w in words)


def _pieces(s: str, min_len: int) -> list[str]:
    parts = re.split(r"[\W\d_]+", s)
    return [p for p in parts if len(p) >= min_len and p not in STOP]


def _name_hit(email: str, folded: str) -> bool:
    local, _, domain = _fold(email).partition("@")
    if len(local) >= 3 and local not in STOP and local in folded:
        return True
    if any(_whole_word(p, folded) for p in _pieces(local, 3)):
        return True
    if domain in PROVIDERS:
        return False
    if domain in folded:
        return True
    return any(_whole_word(p, folded) for p in _pieces(domain.rsplit(".", 1)[0], 4))


def _copied(source: str, text: str) -> bool:
    def grams(s: str) -> set[tuple[str, ...]]:
        w = re.findall(r"\w+", s.lower())
        return {tuple(w[i : i + 4]) for i in range(len(w) - 3)}

    return bool(grams(source) & grams(text))


def check(text: str, emails: list[str], names: list[str], source: str) -> list[str]:
    """The kinds of private thing found in text, [] when it is clean.

    emails: every e-mail address in the users table.
    names: the send's folder name, its file names and its page path.
    source: the teacher's own text, for the copied-words check.
    A reason names the kind only, never the hit, so it can go into a log.
    """
    text = _clean(text)
    source = _clean(source)
    folded = _fold(text)
    low = text.lower()
    found = []
    if any(_fold(e) in folded for e in emails):
        found.append("user email")
    if any(_name_hit(e, folded) for e in emails):
        found.append("user name")
    if ID.search(text):
        found.append("user id")
    # An empty name is a substring of everything, so skip it.
    if any(n and n.lower() in low for n in names) or FILE_GENERIC.search(text):
        found.append("file name")
    if EMAIL.search(text):
        found.append("email address")
    if LINK.search(text):
        found.append("link")
    if MENTION.search(text):
        found.append("mention")
    if CLASS.search(text):
        found.append("class name")
    if any(p.search(text) for p in SCHOOL):
        found.append("school name")
    if _copied(source, text):
        found.append("copied words")
    if _send_word(source, text):
        found.append("word from the send")
    return found
