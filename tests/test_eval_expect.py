"""Each eval task of a how-to checks what the how-to teaches: its recipe's doc passes the task's
`expect`, and the same doc without that one thing fails it."""

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("eval_script", ROOT / "scripts/eval.py")
assert spec and spec.loader
eval_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_script)


def doc_of(stem):
    text = (ROOT / f"docs/okf/recipes/{stem}.md").read_text()
    return json.loads(re.findall(r"```json\n(.*?)\n```", text, re.S)[0])


def blocks(doc):
    return [b for page in doc["pages"] for b in page["blocks"]]


def one_page(doc):
    doc["pages"] = doc["pages"][:1]


def upright(doc):
    doc.pop("landscape", None)
    for page in doc["pages"]:
        page.pop("landscape", None)


def no_guides(doc):
    doc["guides"] = {"x": [], "y": []}
    for page in doc["pages"]:
        page.pop("guides", None)


def unlinked(doc):
    doc.pop("words", None)
    for b in blocks(doc):
        b["props"].pop("list", None)


def no_bows(doc):
    for b in blocks(doc):
        b["props"].pop("syllables", None)


def no_gaps(doc):
    for b in blocks(doc):
        for para in b["props"].get("rich", []):
            for run in para["runs"]:
                run.pop("gap", None)


def no_bank(doc):
    for b in blocks(doc):
        b["props"].pop("bank", None)


# task, recipe, a reply that says what the teacher does, and the one thing taken away.
CASES = [
    ("seiten_zwei", "seiten", "", one_page),
    ("quer_tabelle", "quer", "", upright),
    ("hilfslinien_spalten", "hilfslinien", "", no_guides),
    ("lernwoerter_verknuepft", "lernwoerter-verknuepfen", "", unlinked),
    ("silbenboegen_text", "silbenboegen", "", no_bows),
    ("varianten_rechnen", "varianten", "Drücke „Varianten drucken“.", None),
    ("luecken_loesungen", "loesungen", "Mit „Lösungen zeigen“ siehst du sie.", no_gaps),
    ("luecken_loesungen", "loesungen", "Mit „Lösungen zeigen“ siehst du sie.", no_bank),
]


@pytest.mark.parametrize(("task", "stem", "reply", "strip"), CASES)
def test_a_task_fails_without_what_its_how_to_teaches(task, stem, reply, strip):
    expect = json.loads((ROOT / f"tests/evals/{task}.json").read_text())["expect"]
    doc = doc_of(stem)
    assert eval_script.missing(doc, expect, reply) == []
    if strip is None:
        # What it teaches is in the answer: the teacher prints the variants herself.
        assert eval_script.missing(doc, expect, "Fertig.") != []
        return
    stripped = copy.deepcopy(doc)
    strip(stripped)
    assert eval_script.missing(stripped, expect, reply) != []
