"""Makes the stage's test teacher and prints its login.

    STAGE_INVITE=<token> python - <url> < scripts/stage-teacher.py

Runs in the stage's container with the image's own python, fed on stdin, so it is one file and
needs the standard library only. It signs the teacher up with the invite, logs in once, and wants
that account to own nothing: the stage runs on a copy of real data, and no sheet or template of
another account may show. Stdout holds the two lines of the login and nothing else.
"""

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from typing import Never
from urllib.parse import urljoin

EMAIL = "teacher-run@stage.invalid"
url = sys.argv[1]
step = "invite"


def fail(reason: str) -> Never:
    print(f"stage teacher failed: {step}: {reason}", file=sys.stderr)
    sys.exit(1)


def call(path: str, body: dict | None = None, cookie: str = "") -> tuple[object, str]:
    """Asks the app and wants a 200. Gives the answer and the session cookie."""
    global step
    step = path
    headers = {"Cookie": f"session={cookie}"} if cookie else {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(urljoin(url, path), data, headers)
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        fail(f"status {error.code}")
    with response:
        session = SimpleCookie(response.headers.get("Set-Cookie", "")).get("session")
        return json.load(response), session.value if session else ""


try:
    token = os.environ.get("STAGE_INVITE", "").rsplit("/", 1)[-1]
    if not token:
        # Before the first request, so a run that cannot finish writes nothing.
        fail("STAGE_INVITE is not set")
    password = secrets.token_urlsafe(18)
    call("/api/signup", {"token": token, "email": EMAIL, "password": password})
    # The login as the teacher will type it, not the session of the sign-up.
    me, session = call("/api/login", {"email": EMAIL, "password": password})
    if not session:
        fail("no session cookie")
    if not isinstance(me, dict) or me["admin"]:
        fail("the teacher is an admin")
    if call("/api/sheets", cookie=session)[0] != []:
        fail("the teacher sees a sheet")
    templates = call("/api/templates", cookie=session)[0]
    # The built-in templates are everyone's, and their ids lie below zero.
    if not isinstance(templates, list) or any(t["id"] > 0 for t in templates):
        fail("the teacher sees a template of an account")
except Exception as error:
    # The class and no more: a message may hold the invite.
    fail(type(error).__name__)
print(f"E-Mail: {EMAIL}")
print(f"Passwort: {password}")
