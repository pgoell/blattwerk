"""What shows under an address is that address's sheet, however late another sheet's answer comes;
a save never writes one sheet's content under another's id; and no unsent change is lost when the
teacher leaves a sheet for another (issue #324).

Each sheet has one text block that names it, "Blatt A" in the block "a", so a save's body tells
whose content it carries. The tests hold back each sheet's loads, and its saves where they say
so, and let them go one by one. The editor has no link from one sheet to another: the tests change
the address as the router does, with no new document, and go back with the browser's Back. Each
sheet has an editor of its own, and a sheet is asked for when the save of the one left is done.

The docstrings name the lines of the issue's checklist.
"""

import json
import re
from contextlib import ExitStack
from itertools import permutations

import pytest
from playwright.sync_api import expect
from test_loading import READY, expect_loading, expect_ready, hold, window  # noqa: F401
from ui import TEXT, at, box, pick, sheet

# Goes to an address as the router does: the app stays, and the script of the editor with it.
GO = "(to) => { history.pushState(null, '', to); dispatchEvent(new PopStateEvent('popstate')); }"
# Two frames on, React has drawn what an answer or a new address brought.
FRAMES = "new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"
STATUS = "header [role=status]"


def named(client, name):
    """A sheet whose one block says whose it is."""
    words = {**TEXT, "text": f"Blatt {name.upper()}"}
    return sheet(client, [box(name, "text", words)], title=name)["id"]


def blocks(doc):
    return [(b["id"], b["props"]["text"]) for b in doc["pages"][0]["blocks"]]


class Gate:
    """Holds back a sheet's loads, and its saves while `keep` is set, each until the test lets
    it go."""

    def __init__(self, page, sheet_id):
        self.id, self.loads, self.saves, self.keep = sheet_id, [], [], False
        page.route(f"**/api/sheets/{sheet_id}", self.came)

    def came(self, route):
        if route.request.method == "GET":
            self.loads.append(route)
        elif self.keep:
            self.saves.append(route)
        else:
            route.continue_()

    def asks(self, method):
        """Whether a request is this sheet's load ("GET") or save ("PATCH")."""
        return lambda r: r.method == method and r.url.endswith(f"/api/sheets/{self.id}")

    def answers(self, method):
        return lambda r: self.asks(method)(r.request)


class Run:
    """A teacher's way through some sheets, from the sheet C, so the editor's script is there.

    It knows which load each visit waits for, and after each step it looks at what shows under
    the address: the loading page while the visit's own load is out, then that sheet, or that it
    is not there.
    """

    def __init__(self, page, client, server):
        self.page, self.client = page, client
        self.ids, self.gates, self.asked, self.sent = {}, {}, {}, []
        page.on("request", lambda r: r.method == "PATCH" and self.sent.append(r))
        self.make("a", "b", "c")
        with page.expect_request(self.gates["c"].asks("GET")):
            page.goto(f"{server}/blatt/{self.ids['c']}")
        self.here = {"name": "c", "state": "out"}
        self.asked["c"].append(self.here)
        page.evaluate(FRAMES)
        self.land("c")

    def make(self, *names):
        for name in names:
            self.ids[name] = named(self.client, name)
            self.gates[name] = Gate(self.page, self.ids[name])
            self.asked[name] = []

    def nudge(self):
        """Moves the sheet's block 1 mm to the right: an unsaved change."""
        pick(self.page, self.here["name"])
        self.page.keyboard.press("ArrowRight")

    def go(self, name, back=False, change=False, asks=True):
        """Goes on to the sheet, or back to it. With `change` it first changes the sheet it
        leaves, where one shows, and waits for that sheet's save to be answered. Without `asks`
        it does not wait for the sheet's load: that leaves only when the save of the sheet left
        is done."""
        was = self.here
        with ExitStack() as waits:
            if asks:
                waits.enter_context(self.page.expect_request(self.gates[name].asks("GET")))
            if change and was["state"] == "in":
                saved = self.gates[was["name"]].answers("PATCH")
                waits.enter_context(self.page.expect_response(saved))
                self.nudge()
            if back:
                self.page.go_back()
            else:
                self.page.evaluate(GO, f"/blatt/{self.ids[name]}")
        expect(self.page).to_have_url(re.compile(rf"/blatt/{self.ids[name]}$"))
        self.here = {"name": name, "state": "out"}
        self.asked[name].append(self.here)
        # The load is held by now, and the page drawn for the new address.
        self.page.evaluate(FRAMES)
        self.check()

    def land(self, name, n=0, fails=False):
        """Lets the sheet's n-th load that is still out be answered, or fail."""
        visit, route = self.asked[name].pop(n), self.gates[name].loads.pop(n)
        with self.page.expect_response(self.gates[name].answers("GET")) as got:
            if fails:
                route.fulfill(status=500)
            else:
                route.continue_()
        # The page has read the answer and drawn what it makes of it, where it makes anything. An
        # answer the test made up has no end to wait for.
        if not fails:
            got.value.finished()
        self.page.evaluate(FRAMES)
        visit["state"] = "gone" if fails else "in"
        self.check()

    def clash(self):
        """Another device saves the sheet that shows, the editor's own save is turned down, and
        the teacher asks for the other version: a load that is held as any other."""
        name = self.here["name"]
        address = f"/api/sheets/{self.ids[name]}"
        was = self.client.get(address).json()
        other = {"doc": was["doc"], "version": was["version"]}
        assert self.client.patch(address, json=other).status_code == 200
        self.nudge()
        with self.page.expect_request(self.gates[name].asks("GET")):
            self.page.get_by_role("button", name="Andere Version laden").click(timeout=10000)
        # Saving has stopped here, so leaving saves nothing.
        self.here["state"] = "clash"
        self.asked[name].append(self.here)
        self.page.evaluate(FRAMES)
        self.check()

    def check(self):
        name, state = self.here["name"], self.here["state"]
        if state == "out":
            expect_loading(self.page)
        elif state == "gone":
            expect(self.page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
        else:
            expect(self.page.locator(READY)).to_be_visible()
            first = self.page.locator(".sheet[data-page]").first
            expect(first.locator(".block[data-id]")).to_have_count(1)
            expect(at(self.page, name)).to_contain_text(f"Blatt {name.upper()}")

    def step(self, said):
        verb, name, *n = said.split()
        if verb == "new":
            self.make(name)
        if verb in ("go", "new", "back"):
            self.go(name, back=verb == "back", change=True)
        elif verb == "clash":
            self.clash()
        else:
            self.land(name, *map(int, n), fails=verb == "fail")

    def whose(self, request):
        """The sheet a save went to."""
        return next(name for name, gate in self.gates.items() if gate.asks("PATCH")(request))

    def held(self, name):
        """The sheet as the server holds it."""
        return self.client.get(f"/api/sheets/{self.ids[name]}").json()


@pytest.fixture
def run(window, server):  # noqa: F811
    page, client = window()
    return Run(page, client, server)


def test_a_late_sheet_does_not_show_under_the_next_ones_address(window, server):  # noqa: F811
    """A1"""
    page, client = window()
    a, b, c = (named(client, name) for name in "abc")
    # A third sheet shows, so the editor's script is there: before the fix one editor then
    # showed sheet after sheet.
    page.goto(f"{server}/blatt/{c}")
    expect_ready(page, 1)
    go_a, go_b = hold(page, f"**/api/sheets/{a}"), hold(page, f"**/api/sheets/{b}")
    for to in (a, b):
        with page.expect_request(f"**/api/sheets/{to}"):
            page.evaluate(GO, f"/blatt/{to}")
        page.evaluate(FRAMES)
    go_b()
    expect(at(page, "b")).to_contain_text("Blatt B")
    with page.expect_response(f"**/api/sheets/{a}") as late:
        go_a()
    late.value.finished()
    page.evaluate(FRAMES)
    expect(page).to_have_url(re.compile(rf"/blatt/{b}$"))
    expect(at(page, "b")).to_contain_text("Blatt B")
    expect(at(page, "a")).to_have_count(0)


def there_and_back():
    """A, on to B and back to A: the three loads answered in each order."""
    for order in permutations(("a", "b", "a2")):
        # A's second load is its first one still out once that has been answered.
        lands = [
            "land b" if load == "b" else f"land a {int(load == 'a2' and 'a' not in order[:i])}"
            for i, load in enumerate(order)
        ]
        yield "-".join(order), ["go a", "go b", "back a", *lands]


# Each way starts on C. `land a 1` lets A's second load that is still out be answered.
WAYS = {
    "b-then-a": ["go a", "go b", "land b", "land a"],
    "a-then-b": ["go a", "go b", "land a", "land b"],
    "a-fails-then-b": ["go a", "go b", "fail a", "land b"],
    "b-then-a-fails": ["go a", "go b", "land b", "fail a"],
    **dict(there_and_back()),
    "new-between": ["go a", "new n", "go b", "land n", "land b", "land a"],
    "new-last": ["go a", "go b", "new n", "land a", "land n", "land b"],
    "reload-then-b-first": ["go a", "land a", "clash a", "go b", "land b", "land a"],
    "reload-then-a-first": ["go a", "land a", "clash a", "go b", "land a", "land b"],
}


@pytest.mark.parametrize("way", WAYS.values(), ids=WAYS)
def test_the_address_shows_its_sheet_and_a_save_goes_to_its_own_sheet(run, way):
    """A2, A4"""
    for said in way:
        run.step(said)
    # Each sheet that showed was changed as it was left, and the last one is changed here.
    assert run.here["state"] == "in"
    with run.page.expect_response(run.gates[run.here["name"]].answers("PATCH")):
        run.nudge()
    assert run.sent
    for request in run.sent:
        name = run.whose(request)
        assert blocks(request.post_data_json["doc"]) == [(name, f"Blatt {name.upper()}")]
    for name in run.ids:
        assert blocks(run.held(name)["doc"]) == [(name, f"Blatt {name.upper()}")]


def test_the_sheet_left_no_longer_shows_while_the_next_one_loads(run):
    """A3"""
    run.go("a")
    run.land("a")
    run.go("b")
    expect_loading(run.page)
    expect(at(run.page, "a")).to_have_count(0)
    run.land("b")


def test_a_change_that_waits_for_its_save_is_saved_on_leaving_for_another_sheet(run):
    """A5 (a)"""
    run.go("a")
    run.land("a")
    b = run.held("b")
    run.nudge()
    with run.page.expect_response(run.gates["a"].answers("PATCH")):
        run.go("b")
    run.land("b")
    assert run.held("a")["doc"]["pages"][0]["blocks"][0]["x"] == 16
    assert [run.whose(request) for request in run.sent] == ["a"]
    assert run.held("b") == b


def test_a_change_behind_a_save_under_way_is_saved_after_it_on_leaving(run):
    """A5 (b)"""
    page, gate = run.page, run.gates["a"]
    run.go("a")
    run.land("a")
    b = run.held("b")
    gate.keep = True
    with page.expect_request(gate.asks("PATCH")):
        run.nudge()
    # The save is held by now.
    page.evaluate(FRAMES)
    page.keyboard.press("ArrowRight")
    run.go("b", asks=False)
    # The second save follows the first, and B is asked for when both are done.
    with page.expect_request(gate.asks("PATCH")) as second:
        gate.saves.pop().continue_()
    assert second.value.post_data_json["doc"]["pages"][0]["blocks"][0]["x"] == 17
    page.evaluate(FRAMES)
    assert not run.gates["b"].loads
    asked, saved = run.gates["b"].asks("GET"), gate.answers("PATCH")
    with page.expect_request(asked), page.expect_response(saved) as answer:
        gate.saves.pop().continue_()
    assert answer.value.status == 200
    page.evaluate(FRAMES)
    run.land("b")
    a = run.held("a")
    assert a["doc"]["pages"][0]["blocks"][0]["x"] == 17
    assert a["version"] == 3
    assert [run.whose(request) for request in run.sent] == ["a", "a"]
    assert run.held("b") == b
    run.check()


def test_back_shows_the_sheet_with_the_change_saved_on_leaving(run):
    """I6"""
    page = run.page
    run.go("a")
    run.land("a")
    left = at(page, "a").evaluate("el => getComputedStyle(el).left")
    run.nudge()
    expect(at(page, "a")).not_to_have_css("left", left)
    moved = at(page, "a").evaluate("el => getComputedStyle(el).left")
    with page.expect_response(run.gates["a"].answers("PATCH")):
        run.go("b")
    run.land("b")
    run.go("a", back=True)
    run.land("a")
    expect(at(page, "a")).to_have_css("left", moved)
    assert run.held("a")["doc"]["pages"][0]["blocks"][0]["x"] == 16


@pytest.mark.parametrize("over", ["sheet", "list"])
def test_a_sheet_is_asked_for_only_when_the_save_of_the_one_left_is_done(run, server, over):
    """I6"""
    page, gate = run.page, run.gates["a"]
    run.go("a")
    run.land("a")
    gate.keep = True
    left = at(page, "a").evaluate("el => getComputedStyle(el).left")
    # On to another sheet or to the list, and back before the save on leaving is answered.
    with page.expect_request(gate.asks("PATCH")):
        run.nudge()
        expect(at(page, "a")).not_to_have_css("left", left)
        moved = at(page, "a").evaluate("el => getComputedStyle(el).left")
        if over == "sheet":
            run.go("b", asks=False)
        else:
            page.get_by_label("Meine Blätter").click()
            expect(page).to_have_url(f"{server}/")
    run.go("a", back=True, asks=False)
    assert not gate.loads
    assert not run.gates["b"].loads
    gate.keep = False
    with page.expect_request(gate.asks("GET")):
        gate.saves.pop().continue_()
    page.evaluate(FRAMES)
    run.land("a")
    expect(at(page, "a")).to_have_css("left", moved)
    with page.expect_response(gate.answers("PATCH")) as saved:
        run.nudge()
    assert saved.value.status == 200
    expect(page.locator(".clash")).to_have_count(0)
    assert run.held("a")["doc"]["pages"][0]["blocks"][0]["x"] == 17


def test_a_large_sheet_is_saved_on_leaving_for_another_sheet(run):
    """A5"""
    page, gate = run.page, run.gates["a"]
    was = run.held("a")
    # Chromium turns down a request that may outlive the window when its body tops 64 KiB.
    heavy = [box(f"x{n}", "text", {**TEXT, "text": "schwer " * 20}) for n in range(300)]
    doc = {**was["doc"], "pages": [*was["doc"]["pages"], {"blocks": heavy}]}
    assert len(json.dumps(doc)) > 64 * 1024
    large = {"doc": doc, "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=large).status_code == 200
    run.go("a")
    run.land("a")
    with page.expect_response(gate.answers("PATCH"), timeout=10000) as saved:
        run.nudge()
        run.go("b")
    assert saved.value.status == 200
    run.land("b")
    assert [run.whose(request) for request in run.sent] == ["a"]
    assert run.held("a")["doc"]["pages"][0]["blocks"][0]["x"] == 16


def test_a_save_under_way_on_leaving_leaves_the_next_sheet_alone(run):
    """I7"""
    page, gate = run.page, run.gates["a"]
    run.go("a")
    run.land("a")
    gate.keep = True
    with page.expect_request(gate.asks("PATCH")):
        run.nudge()
    # The save is held by now.
    page.evaluate(FRAMES)
    run.go("b", asks=False)
    assert not run.gates["b"].loads
    # B is asked for when A's save is answered.
    asked, saved = run.gates["b"].asks("GET"), gate.answers("PATCH")
    with page.expect_request(asked), page.expect_response(saved):
        gate.saves.pop().continue_()
    page.evaluate(FRAMES)
    run.land("b")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    with page.expect_response(run.gates["b"].answers("PATCH")) as saved:
        run.nudge()
    assert saved.value.status == 200
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    # Leaving A sent nothing more: the save under way carried all of it.
    assert [run.whose(request) for request in run.sent] == ["a", "b"]
    assert run.held("a")["doc"]["pages"][0]["blocks"][0]["x"] == 16
    assert run.held("b")["doc"]["pages"][0]["blocks"][0]["x"] == 16
