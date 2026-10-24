"""Each block type takes another seed: typed numbers go, and the settings that are not tasks stay."""

from blattwerk import variants


def test_a_zahlenmauer_gets_another_seed_and_loses_its_typed_numbers():
    """I2 of #82: B to D give a wall block a seed of its own and drop `typed`; A is as stored."""
    wall = {"base": 3, "count": 4, "columns": 2, "max": 20, "op": "+", "given": "base"}
    wall = {**wall, "empty": False, "seed": 7, "typed": [[0, 0, 5]]}
    doc = {"pages": [{"blocks": [{"id": "w", "type": "zahlenmauer", "props": wall}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**{k: v for k, v in wall.items() if k != "typed"}, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == wall


def test_a_zahlenstrahl_gets_another_seed_and_keeps_its_marks():
    """B to D give a Zahlenstrahl a seed of its own; its `marks` stay, as the teacher set them."""
    strahl = {
        "start": 0,
        "end": 20,
        "minor": 1,
        "major": 5,
        "labels": "major",
        "size": 12,
        "cut": False,
        "tasks": "free",
        "boxes": 3,
        "arrows": 0,
        "jumps": False,
        "marks": [[5, "box"]],
        "seed": 7,
    }
    doc = {"pages": [{"blocks": [{"id": "z", "type": "zahlenstrahl", "props": strahl}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**strahl, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4


def test_a_hunderterfeld_gets_another_seed_and_keeps_its_settings():
    """B to D give a Hunderterfeld a seed of its own; its hidden, tinted, cut, filled stay."""
    field = {
        "look": "tafel",
        "from": 1,
        "show": "random",
        "hide": 20,
        "hidden": [0, 5, 99],
        "tint": "free",
        "times": 2,
        "line": 1,
        "color": 2,
        "tints": [[11, 1], [12, 2]],
        "cut": True,
        "shape": [34, 43, 44, 45, 54],
        "given": 44,
        "fill": "free",
        "dots": 0,
        "filled": [3, 4],
        "seed": 7,
    }
    doc = {"pages": [{"blocks": [{"id": "f", "type": "hunderterfeld", "props": field}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**field, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == field


def test_an_uhr_gets_another_seed_and_keeps_its_settings():
    """B to D give an Uhr a seed of its own; its times, faces and task stay."""
    clock = {
        "numbers": "quarters",
        "minutes": False,
        "ring": True,
        "task": "draw",
        "answer": "line",
        "format": "words",
        "region": "viertel",
        "count": 4,
        "cols": 2,
        "step": 5,
        "fill": "free",
        "times": [210, 585, 720, 370],
        "seed": 7,
    }
    doc = {"pages": [{"blocks": [{"id": "u", "type": "uhr", "props": clock}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**clock, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == clock


def test_a_rechendreieck_gets_another_seed_and_loses_its_typed_numbers():
    """I2 of #83: B to D give a triangle block a seed of its own, drop `typed`; A is as stored."""
    triangle = {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False, "seed": 7}
    triangle = {**triangle, "typed": [[0, 0, 5]]}
    doc = {"pages": [{"blocks": [{"id": "r", "type": "rechendreieck", "props": triangle}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in triangle.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == triangle


def test_a_zahlenhaus_gets_another_seed_and_loses_its_typed_numbers():
    """A of #819 (Varianten re-seed): B to D give a Zahlenhaus a seed of its own, drop `typed`; A is as stored."""
    house = {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side", "seed": 7}
    house = {**house, "typed": [[0, 0, 9]]}
    doc = {"pages": [{"blocks": [{"id": "h", "type": "zahlenhaus", "props": house}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in house.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == house


def test_a_zahlenkette_gets_another_seed_and_loses_its_typed_numbers():
    """A of #820 (Varianten re-seed): B to D give a Zahlenkette a seed of its own, drop `typed`; A is as stored."""
    chain = {
        "count": 4,
        "columns": 2,
        "rings": 6,
        "max": 20,
        "op": "+",
        "given": "start",
        "seed": 7,
    }
    chain = {**chain, "typed": [[0, 0, 9]]}
    doc = {"pages": [{"blocks": [{"id": "k", "type": "zahlenkette", "props": chain}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in chain.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == chain


def test_an_operatorfeld_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #822: B to D give an Operatorfeld a seed of its own, drop `typed`; A is as stored."""
    field = {
        "centre": False,
        "count": 2,
        "columns": 2,
        "boxes": 4,
        "max": 20,
        "ops": ["+", "-"],
        "only": "none",
        "given": "start",
        "drawOps": True,
        "seed": 7,
        "typed": [[0, 0, 9]],
    }
    doc = {"pages": [{"blocks": [{"id": "o", "type": "operatorfeld", "props": field}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in field.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == field


def test_a_rechenrad_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #823: B to D give a Rechenrad a seed of its own, drop `typed`; A is as stored."""
    wheel = {
        "count": 2,
        "columns": 2,
        "rings": 2,
        "segments": 8,
        "max": 20,
        "op": "+",
        "task": "outer",
        "seed": 7,
        "typed": [[0, 0, 0, 5]],
    }
    doc = {"pages": [{"blocks": [{"id": "r", "type": "rechenrad", "props": wheel}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in wheel.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == wheel


def test_a_rechentabelle_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #824: B to D give a Rechentabelle a seed of its own, drop `typed`; A is as stored."""
    table = {
        "count": 2,
        "columns": 2,
        "rows": 4,
        "cols": 4,
        "op": "+",
        "max": 20,
        "carry": ["either", "either"],
        "seed": 7,
        "typed": [[0, 0, 0, 5]],
    }
    doc = {"pages": [{"blocks": [{"id": "t", "type": "rechentabelle", "props": table}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in table.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == table


def test_a_magischesquadrat_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #825: B to D give a Magisches Quadrat a seed of its own, drop `typed`; A is as stored."""
    square = {
        "count": 2,
        "columns": 2,
        "size": 3,
        "max": 20,
        "given": 4,
        "showSum": False,
        "seed": 7,
        "typed": [[0, 1, 1, 5]],
    }
    doc = {"pages": [{"blocks": [{"id": "q", "type": "magischesquadrat", "props": square}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in square.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == square


def test_a_malquadrat_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #826: B to D give a Malquadrat a seed of its own, drop `typed`; A is as stored."""
    square = {
        "count": 2,
        "columns": 2,
        "size": 3,
        "op": "*",
        "reihen": [2, 3, 4, 5, 6, 7, 8, 9],
        "max": 20,
        "task": "factors",
        "seed": 7,
        "typed": [[0, 1, 1, 5]],
    }
    doc = {"pages": [{"blocks": [{"id": "q", "type": "malquadrat", "props": square}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in square.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == square


def test_a_zerlegungsfeld_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #827: B to D give a Zerlegungsfeld a seed of its own, drop `typed`; A is as stored."""
    zerlegung = {
        "count": 6,
        "columns": 3,
        "op": "+",
        "max": 20,
        "step": "zehner",
        "big": False,
        "task": "task",
        "seed": 7,
        "typed": [[0, 0, 7]],
    }
    doc = {"pages": [{"blocks": [{"id": "q", "type": "zerlegungsfeld", "props": zerlegung}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in zerlegung.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == zerlegung


def test_a_zehnerfeld_gets_another_seed_loses_its_typed_numbers_and_keeps_its_marks():
    """Varianten of #829: B to D give a Zehnerfeld a seed of its own and drop `typed`; the dots set by hand
    (`marks`) stay; A is as stored."""
    zehner = {
        "count": 4,
        "columns": 2,
        "field": "zwanzig",
        "op": "+",
        "task": "dots",
        "max": 20,
        "cross": "any",
        "lines": True,
        "colors": "color",
        "manual": False,
        "marks": [[0, 0, 1], [0, 1, 3]],
        "seed": 7,
        "typed": [[0, 0, 7]],
    }
    doc = {"pages": [{"blocks": [{"id": "q", "type": "zehnerfeld", "props": zehner}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in zehner.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == zehner


def test_a_halbschriftlich_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #828: B to D give a Halbschriftlich block a seed of its own, drop `typed`; A is as stored."""
    halb = {
        "count": 6,
        "columns": 2,
        "op": "+",
        "max": 1000,
        "digits": 3,
        "einer": "any",
        "zehner": "any",
        "grid": True,
        "head": False,
        "tint": False,
        "ops": True,
        "seed": 7,
        "typed": [[0, 0, 7]],
    }
    doc = {"pages": [{"blocks": [{"id": "q", "type": "halbschriftlich", "props": halb}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in halb.items() if k != "typed"}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == halb


def test_a_pfeilbild_gets_another_seed_and_loses_its_typed_numbers():
    """Varianten of #821 and #921: B to D give a Pfeilbild a seed of its own, drop `typed` and
    `typedOps`; A is as stored."""
    picture = {
        "count": 4,
        "columns": 2,
        "boxes": 4,
        "max": 20,
        "ops": ["+", "-"],
        "arrows": "one",
        "given": "start",
        "drawOps": True,
        "seed": 7,
        "typed": [[0, 0, 9]],
        "typedOps": [[0, 1, "-", 3]],
    }
    doc = {"pages": [{"blocks": [{"id": "p", "type": "pfeilbild", "props": picture}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {7}
    kept = {k: v for k, v in picture.items() if k not in ("typed", "typedOps")}
    for letter in "BCD":
        props = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert props == {**kept, "seed": props["seed"]}
        seeds.add(props["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == picture
