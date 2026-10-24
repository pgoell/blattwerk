"""Page grounds: a JPEG, a PNG, or a PDF page turned into a picture at print size.

The picture is an upload of the account, the same kind an image block shows. A PDF is not
kept: each chosen page becomes a JPEG at 300 dpi, which is print size on A4.
"""

import io
import threading

import pypdfium2 as pdfium
from fastapi import APIRouter, Form, HTTPException, UploadFile
from PIL import Image
from starlette.concurrency import run_in_threadpool

from blattwerk.auth import Teacher
from blattwerk.db import Con
from blattwerk.pictures import path

# A textbook scan is larger than a picture on a block, and a whole book is not a worksheet.
MAX_GROUND_BYTES = 30 * 2**20
MAX_GROUND_PAGES = 20
DPI = 300
JPEG_QUALITY = 90
# One render at a time: a page at 300 dpi is a large bitmap.
RENDER = threading.BoundedSemaphore(1)

TOO_BIG = "Die Datei ist zu groß. Ein Hintergrund darf 30 MB haben."
TOO_MANY = "Die PDF hat zu viele Seiten. Es gehen 20 Seiten."
NOT_KIND = "Es gehen JPEG, PNG und PDF."
BAD_PDF = "Die PDF ließ sich nicht lesen."
BAD_IMAGE = "Das Bild ließ sich nicht lesen."
NO_PAGE = "Die PDF hat keine Seite."
WHICH = "Die Seitenangabe ist keine Seitenzahl."

router = APIRouter(prefix="/api")


def kind_of(data: bytes) -> str | None:
    """The type the first bytes show. What the file declares is no evidence."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"%PDF"):
        return "application/pdf"
    return None


def keep(con, user_id: int, data: bytes, type_: str) -> int:
    upload_id = con.execute(
        "INSERT INTO uploads (user_id, type) VALUES (?, ?)", (user_id, type_)
    ).lastrowid
    assert upload_id is not None
    out = path(user_id, upload_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return upload_id


def measure(data: bytes) -> tuple[int, int] | None:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        width, height = image.size
    except OSError, ValueError:
        return None
    if width < 1 or height < 1:
        return None
    return width, height


def indexes(which: str, count: int) -> list[int] | None:
    """The pages to render, from 0. None is a probe: the caller only learns the count.

    A PDF of one page is rendered at once, so the teacher does not send it twice.
    """
    if which == "":
        return [0] if count == 1 else None
    if which == "all":
        return list(range(count))
    found = []
    for bit in which.split(","):
        bit = bit.strip()
        if not bit.isdigit() or int(bit) < 1:
            raise HTTPException(422, detail=WHICH)
        number = int(bit)
        if number > count:
            raise HTTPException(422, detail=f"Die PDF hat keine Seite {number}. Sie hat {count}.")
        if number - 1 not in found:
            found.append(number - 1)
    if not found:
        raise HTTPException(422, detail=WHICH)
    return found


def render_page(doc: pdfium.PdfDocument, index: int) -> tuple[bytes, int, int]:
    page = doc[index]
    try:
        bitmap = page.render(scale=DPI / 72)
        try:
            image = bitmap.to_pil()
        finally:
            bitmap.close()
    finally:
        page.close()
    if image.mode != "RGB":
        image = image.convert("RGB")
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=JPEG_QUALITY)
    return out.getvalue(), image.width, image.height


def render_pdf(data: bytes, which: str) -> tuple[int, list[tuple[int, bytes, int, int]]]:
    """The page count, and each rendered page as (page number from 1, jpeg, width, height)."""
    with RENDER:
        try:
            doc = pdfium.PdfDocument(data)
        except pdfium.PdfiumError, OSError, ValueError:
            raise HTTPException(422, detail=BAD_PDF) from None
        try:
            count = len(doc)
            if count < 1:
                raise HTTPException(422, detail=NO_PAGE)
            if count > MAX_GROUND_PAGES:
                raise HTTPException(422, detail=TOO_MANY)
            chosen = indexes(which, count)
            if chosen is None:
                return count, []
            made = []
            for index in chosen:
                jpeg, width, height = render_page(doc, index)
                made.append((index + 1, jpeg, width, height))
            return count, made
        finally:
            doc.close()


def answer(pages: int, made: list[dict]) -> dict:
    return {
        "pages": pages,
        "bytes": MAX_GROUND_BYTES,
        "page_limit": MAX_GROUND_PAGES,
        "made": made,
    }


@router.post("/grounds")
async def grounds(
    file: UploadFile,
    user: Teacher,
    con: Con,
    which: str = Form(""),
) -> dict:
    data = await file.read(MAX_GROUND_BYTES + 1)
    if len(data) > MAX_GROUND_BYTES:
        raise HTTPException(413, detail=TOO_BIG)
    type_ = kind_of(data)
    if type_ is None:
        raise HTTPException(415, detail=NOT_KIND)
    if type_ != "application/pdf":
        size = await run_in_threadpool(measure, data)
        if size is None:
            raise HTTPException(415, detail=BAD_IMAGE)
        upload_id = keep(con, user["id"], data, type_)
        width, height = size
        return answer(1, [{"page": 1, "id": upload_id, "width": width, "height": height}])
    count, rendered = await run_in_threadpool(render_pdf, data, which)
    made = []
    for number, jpeg, width, height in rendered:
        upload_id = keep(con, user["id"], jpeg, "image/jpeg")
        made.append({"page": number, "id": upload_id, "width": width, "height": height})
    return answer(count, made)
