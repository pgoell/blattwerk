"""What a page of a PowerPoint or Word file holds: pictures and text boxes, in mm and pt."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Picture:
    """A picture on a page: its place in mm, and the file."""

    x: float
    y: float
    w: float
    h: float
    data: bytes
    ext: Literal["png", "jpg"]
    alt: str
    # Lies under everything, the text line of the Word file included: the page's own picture.
    under: bool = False


@dataclass
class Run:
    text: str
    bold: bool
    italic: bool
    underline: bool
    color: str


@dataclass
class Text:
    """A text box on a page: its place and insets in mm, sizes in pt, colours as rrggbb."""

    x: float
    y: float
    w: float
    h: float
    paras: list[list[Run]]
    font: str
    size: float
    line: float
    tracking: float
    align: Literal["left", "center", "right"]
    valign: Literal["top", "middle", "bottom"]
    fill: str | None
    stroke: str | None
    stroke_w: float
    inset: tuple[float, float]


@dataclass
class Page:
    w: float
    h: float
    items: list[Picture | Text] = field(default_factory=list)
