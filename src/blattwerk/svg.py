"""SVG: cleans an uploaded picture so that it draws and runs nothing but its own shapes."""

import math
import re
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)

SHAPES = {
    "svg",
    "g",
    "defs",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "use",
    "clipPath",
    "mask",
    "linearGradient",
    "radialGradient",
    "stop",
    "pattern",
    "marker",
    "symbol",
    "title",
    "desc",
    "style",
}
ALLOWED = {f"{{{SVG}}}{name}" for name in SHAPES}
HREF = {"href", f"{{{XLINK}}}href"}
KEPT_NAMESPACED = {f"{{{XLINK}}}href", f"{{{XML}}}space"}

# A DOCTYPE without an internal subset declares nothing, so it goes before the scan.
DOCTYPE = re.compile(rb"<!DOCTYPE[^\[>]*>", re.IGNORECASE)
# Markup that can pull in entities or stylesheets, which the parser would follow.
REFUSED = (b"<!doctype", b"<!entity", b"<?xml-stylesheet")

NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
DIMENSION = re.compile(rf"({NUMBER})(px)?")
SPLIT = re.compile(r"[\s,]+")
# A backslash can spell a word in CSS, so it goes before the search for the words.
BACKSLASH = re.compile(r"\\")
REMOVED = re.compile(r"@import[^;]*;?|expression\(|javascript:", re.IGNORECASE)
# Also covers -webkit-image-set. The whole call goes, its string is a URL the browser loads.
IMAGE_SET = re.compile(r"image-set\s*\([^)]*\)?", re.IGNORECASE)
URL = re.compile(r"url\s*\([^)]*\)?", re.IGNORECASE)


def clean(data: bytes) -> bytes | None:
    """The SVG as it may be shown, or None when it is no SVG or cannot be made safe."""
    data = DOCTYPE.sub(b"", data)
    if any(word in data.lower() for word in REFUSED):
        return None
    try:
        root = ET.fromstring(data.decode("utf-8-sig"))
        if root.tag != f"{{{SVG}}}svg" or not _size(root):
            return None
        _prune(root)
        return ET.tostring(root, encoding="utf-8")
    except ET.ParseError, ValueError, RecursionError:
        return None


def _prune(root: ET.Element) -> None:
    _clean_element(root)
    stack = [root]
    while stack:
        parent = stack.pop()
        for child in list(parent):
            if child.tag not in ALLOWED:
                parent.remove(child)
                continue
            _clean_element(child)
            stack.append(child)


def _dropped(key: str, value: str) -> bool:
    """Whether an attribute goes whatever it says: a handler, a foreign one, or a link out."""
    if key.rsplit("}", 1)[-1].lower().startswith("on"):
        return True
    if key.startswith("{") and key not in KEPT_NAMESPACED:
        return True
    return key in HREF and not value.startswith("#")


def _clean_element(el: ET.Element) -> None:
    for key in list(el.attrib):
        if _dropped(key, el.attrib[key]):
            del el.attrib[key]
        else:
            el.attrib[key] = _css(el.attrib[key])
    if el.tag == f"{{{SVG}}}style":
        # Child elements would hide CSS in their tails, so a style keeps only its text.
        for child in list(el):
            el.remove(child)
        if el.text:
            el.text = _css(el.text)


def _css(text: str) -> str:
    text = BACKSLASH.sub("", text)
    # Removing one bit can join two others into a new one, so repeat until none is left.
    while (cut := REMOVED.sub("", text)) != text:
        text = cut
    return URL.sub(_url, IMAGE_SET.sub("none", text))


def _url(match: re.Match) -> str:
    """Keeps a url() that points into this file, and turns any other into none."""
    text = match.group(0)
    target = text[text.index("(") + 1 :].removesuffix(")").strip().strip("'\"").strip()
    return text if target.startswith("#") else "none"


def _plain(text: str) -> str | None:
    """A finite number above zero as plain decimals, which the MCP tool reads: 2e2 is 200."""
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        return None
    plain = format(value, "f").rstrip("0").rstrip(".")
    return plain if float(plain) > 0 else None


def _box(text: str | None) -> tuple[str, str] | None:
    """The width and height of a viewBox of four numbers, as plain decimals above zero."""
    if text is None:
        return None
    parts = SPLIT.split(text.strip())
    if len(parts) != 4 or not all(re.fullmatch(NUMBER, part) for part in parts):
        return None
    width, height = _plain(parts[2]), _plain(parts[3])
    if width is None or height is None:
        return None
    return width, height


def _dimension(text: str | None) -> str | None:
    """A width or height as a plain number, when it is one, with or without px."""
    match = DIMENSION.fullmatch(text or "")
    return _plain(match.group(1)) if match else None


def _size(root: ET.Element) -> bool:
    """Gives the root a plain width, height and viewBox, or says it cannot."""
    box = _box(root.get("viewBox"))
    width = _dimension(root.get("width"))
    height = _dimension(root.get("height"))
    if box is None:
        if width is None or height is None:
            return False
        root.set("viewBox", f"0 0 {width} {height}")
    elif width is None or height is None:
        width, height = box
    root.set("width", width)
    root.set("height", height)
    return True
