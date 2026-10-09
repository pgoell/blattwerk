"""Pictures: where an upload's file lies, which uploads a document shows, and when one goes.

A file's time is the last save that showed the picture or took it away. Uploads, sheets and
templates all need it, so it imports none of them.
"""

import json
import logging
import os
import sqlite3
import time
from contextlib import suppress
from pathlib import Path

from blattwerk import db

log = logging.getLogger(__name__)

# How long a picture that nothing shows any more stays: undo, an open tab and the clipboard
# may still bring it back.
KEEP_DAYS = 30


def path(user_id: int, upload_id: int) -> Path:
    # Under the user's folder, so deleting the account deletes the pictures.
    return db.DATA_DIR / "users" / str(user_id) / "uploads" / str(upload_id)


def shown(doc: dict) -> set[int]:
    """The uploads the image blocks of a document show."""
    # A client wrote the document, so any part may be missing or of another kind. Only a number
    # names a file in the uploads folder.
    ids = set()
    pages = doc.get("pages")
    for page in pages if isinstance(pages, list) else []:
        blocks = page.get("blocks") if isinstance(page, dict) else None
        for block in blocks if isinstance(blocks, list) else []:
            props = block.get("props") if isinstance(block, dict) else None
            upload = props.get("upload") if isinstance(props, dict) else None
            if isinstance(upload, int) and block.get("type") == "image":
                ids.add(upload)
    return ids


def touch(user_id: int, doc: dict) -> None:
    """Counts the days of the document's pictures from now."""
    for upload_id in shown(doc):
        # A missing file, or one that will not take a time, must not fail the save.
        with suppress(OSError):
            os.utime(path(user_id, upload_id))


def sweep(con: sqlite3.Connection, user_id: int) -> None:
    """Deletes the user's uploads that none of their sheets and templates has shown for long."""
    limit = time.time() - KEEP_DAYS * 86400
    old = []
    for row in con.execute("SELECT id FROM uploads WHERE user_id = ?", (user_id,)):
        file = path(user_id, row["id"])
        try:
            if file.stat().st_mtime < limit:
                old.append((row["id"], file))
        except OSError:
            # The upload may be between its row and its file. No file error fails the save.
            pass
    if not old:
        return
    docs = con.execute(
        "SELECT doc FROM sheets WHERE user_id = ?1 UNION ALL"
        " SELECT doc FROM templates WHERE user_id = ?1",
        (user_id,),
    )
    used = set().union(*(shown(json.loads(row["doc"])) for row in docs))
    for upload_id, file in old:
        if upload_id in used:
            with suppress(OSError):
                os.utime(file)
            continue
        try:
            file.unlink(missing_ok=True)
        except OSError:
            # The row stays, so the next sweep tries again.
            log.error("Could not delete %s", file)
            continue
        con.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
