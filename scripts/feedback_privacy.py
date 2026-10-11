"""What must never stand in a public issue. Standard library only."""

import re

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

# (?<=_) lets "user_id=3" hit, since \b does not sit between "_" and "i".
ID = re.compile(
    r"(?:\b|(?<=_))(users?|nutzer\w*|benutzer\w*|konto|account|teacher|lehrer\w*|uid|id)"
    r"\s*[#:=/_-]?\s*\d+\b",
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


def _whole_word(piece: str, text: str) -> bool:
    # Not glued to other letters: "kraus" hits "kraus98", not "krause".
    pattern = rf"(?<![^\W\d_]){re.escape(piece)}(?![^\W\d_])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _pieces(s: str, min_len: int) -> list[str]:
    parts = re.split(r"[^a-zA-ZäöüÄÖÜß]+", s)
    return [p for p in parts if len(p) >= min_len and p.lower() not in STOP]


def _name_hit(email: str, text: str) -> bool:
    local, _, domain = email.lower().partition("@")
    if len(local) >= 3 and local not in STOP and local in text.lower():
        return True
    if any(_whole_word(p, text) for p in _pieces(local, 3)):
        return True
    if domain in PROVIDERS:
        return False
    if domain in text.lower():
        return True
    return any(_whole_word(p, text) for p in _pieces(domain.rsplit(".", 1)[0], 4))


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
    low = text.lower()
    found = []
    if any(e.lower() in low for e in emails):
        found.append("user email")
    if any(_name_hit(e, text) for e in emails):
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
    return found
