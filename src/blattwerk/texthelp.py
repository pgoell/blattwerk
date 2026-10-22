"""Text help: the selected words only, and only to the address Pascal sets.

No provider is chosen here. With ``BLATTWERK_TEXT_HELP_URL`` unset, or not an
http address, the route answers 503 and sends nothing.
"""

import os
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from blattwerk.auth import Teacher

router = APIRouter(prefix="/api")
CAP = 20_000
MISSING = "Die Texthilfe ist nicht eingerichtet."
DOWN = "Die Texthilfe hat nicht geantwortet."


class Ask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=CAP)
    kind: Literal["simpler", "shorter", "levels"]


class One(BaseModel):
    text: str = Field(max_length=CAP)


class Three(BaseModel):
    texts: list[Annotated[str, Field(max_length=CAP)]] = Field(min_length=3, max_length=3)


def address() -> str:
    url = os.environ.get("BLATTWERK_TEXT_HELP_URL", "").strip()
    if url.startswith(("http://", "https://")):
        return url
    raise HTTPException(503, MISSING)


def answer(kind: str, payload: object) -> dict:
    try:
        if kind == "levels":
            return {"texts": Three.model_validate(payload).texts}
        return {"text": One.model_validate(payload).text}
    except ValidationError as error:
        raise HTTPException(502, DOWN) from error


@router.post("/text/help")
def help_text(body: Ask, _user: Teacher) -> dict:
    url = address()
    try:
        response = httpx.post(url, json={"text": body.text, "kind": body.kind}, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(502, DOWN) from error
    return answer(body.kind, payload)
