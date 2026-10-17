"""Two tabs on one sheet that another device deleted: the teacher keeps it once, in the tab that
presses first (#718). The two tabs share one browser context, so the store's storage event fires
between them. No save is held here: the server answers each save at once.
"""

import re

import pytest
from playwright.sync_api import expect
from ui import TEXT, box, pick, sheet, user

KEEP, DROP = "Als neues Blatt behalten", "Verwerfen"
GONE = re.compile("gelöscht")
WORD = "Das hat nicht geklappt. Prüfe deine Verbindung und versuche es noch einmal."
NOTICE = "#root > .notice"


def record(page, sheet_id):
    """What the browser keeps of the sheet's unsaved change."""
    return page.evaluate("(id) => JSON.parse(localStorage.getItem('unsaved:' + id))", sheet_id)


@pytest.fixture
def tabs(browser, server):
    """Two tabs on the sheet A, which is then deleted. Gives the client, A's id and the tabs."""
    client = user()
    sheet_id = sheet(client, [box("a", "text", TEXT)], title="a")["id"]
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    context.add_init_script("window.saveAfter = 300")
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    page1, page2 = context.new_page(), context.new_page()
    for page in (page1, page2):
        page.goto(f"{server}/blatt/{sheet_id}")
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    assert client.delete(f"/api/sheets/{sheet_id}").status_code == 200
    yield client, sheet_id, page1, page2
    context.close()


def change_and_keep(client, sheet_id, page1):
    """Tab 1 moves A, finds A gone and keeps it as new. Gives the new sheet's id."""
    pick(page1, "a")
    page1.keyboard.press("ArrowRight")
    expect(page1.locator(".clash")).to_contain_text(GONE)
    expect(page1.get_by_role("button", name=KEEP)).to_be_enabled()
    page1.get_by_role("button", name=KEEP).click()
    expect(page1).to_have_url(re.compile(rf"/blatt/(?!{sheet_id}$)\d+$"))
    return page1.url.rsplit("/", 1)[1]


def test_a_second_tab_with_other_work_keeps_into_the_same_new_sheet(tabs):
    """Tab 2 changes other work and keeps: it goes to tab 1's sheet, no second sheet is made, and
    its change shows as a clash."""
    client, sheet_id, page1, page2 = tabs
    new = change_and_keep(client, sheet_id, page1)
    count = len(client.get("/api/sheets").json())
    expect(page2.locator(".clash")).to_have_count(0)
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    page2.get_by_role("button", name=KEEP).click()
    expect(page2).to_have_url(f"{page1.url.rsplit('/', 1)[0]}/{new}")
    expect(page2.locator(".clash")).to_be_visible()
    assert len(client.get("/api/sheets").json()) == count


def test_a_second_tab_with_the_same_work_ends_there_without_a_press(tabs):
    """Tab 2 holds the move tab 1 kept: its choice ends at once and it goes to tab 1's sheet."""
    client, sheet_id, page1, page2 = tabs
    new = change_and_keep(client, sheet_id, page1)
    count = len(client.get("/api/sheets").json())
    pick(page2, "a")
    page2.keyboard.press("ArrowRight")
    expect(page2).to_have_url(f"{page1.url.rsplit('/', 1)[0]}/{new}")
    expect(page2.locator(".clash")).to_have_count(0)
    assert len(client.get("/api/sheets").json()) == count


def test_a_keep_after_another_tab_dropped_makes_one_sheet(tabs):
    """Tab 1 drops A. Tab 2 then keeps its other work: exactly one new sheet is made."""
    client, sheet_id, page1, page2 = tabs
    pick(page1, "a")
    page1.keyboard.press("ArrowRight")
    expect(page1.locator(".clash")).to_contain_text(GONE)
    page1.once("dialog", lambda dialog: dialog.accept())
    page1.get_by_role("button", name=DROP).click()
    expect(page1).not_to_have_url(re.compile(rf"/blatt/{sheet_id}$"))
    count = len(client.get("/api/sheets").json())
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    page2.get_by_role("button", name=KEEP).click()
    expect(page2).not_to_have_url(re.compile(rf"/blatt/{sheet_id}$"))
    expect(page2).to_have_url(re.compile(r"/blatt/\d+$"))
    assert len(client.get("/api/sheets").json()) == count + 1


def test_tab_one_keeps_its_own_unsaved_change_when_tab_two_hands_over_its_work(tabs):
    """Tab 2's work lands on tab 1's new sheet without a write to the store: tab 1's own unsaved
    record of that sheet stays as it was."""
    client, sheet_id, page1, page2 = tabs
    new = change_and_keep(client, sheet_id, page1)
    page1.route(
        f"**/api/sheets/{new}",
        lambda route: None if route.request.method == "PATCH" else route.continue_(),
    )
    pick(page1, "a")
    page1.keyboard.press("ArrowRight")
    page1.wait_for_function(f"localStorage.getItem('unsaved:{new}') !== null")
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    page2.get_by_role("button", name=KEEP).click()
    expect(page2).to_have_url(re.compile(rf"/blatt/{new}$"))
    expect(page2.locator(".clash")).to_be_visible()
    assert record(page1, new) is not None


def test_a_failed_lookup_of_the_new_sheet_says_so_and_makes_no_second_sheet(tabs):
    """A 500 from the new sheet's address is a failure, not a missing sheet: the keep says so and
    makes no second sheet."""
    client, sheet_id, page1, page2 = tabs
    new = change_and_keep(client, sheet_id, page1)
    count = len(client.get("/api/sheets").json())
    page2.route(
        f"**/api/sheets/{new}",
        lambda route: (
            route.fulfill(status=500) if route.request.method == "GET" else route.continue_()
        ),
    )
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    page2.get_by_role("button", name=KEEP).click()
    expect(page2.locator(".clash")).to_contain_text(WORD)
    assert len(client.get("/api/sheets").json()) == count


def test_a_tab_reloaded_after_another_kept_still_keeps_into_the_same_new_sheet(tabs):
    """Tab 2 finds A gone with other work before tab 1 keeps; it is reloaded after that, so it heard
    no choice in this page. Its keep still lands on tab 1's sheet."""
    client, sheet_id, page1, page2 = tabs
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    new = change_and_keep(client, sheet_id, page1)
    count = len(client.get("/api/sheets").json())
    page2.reload()
    expect(page2.locator(NOTICE)).to_contain_text(GONE)
    page2.locator(NOTICE).get_by_role("button", name=KEEP).click()
    expect(page2).to_have_url(re.compile(rf"/blatt/{new}$"))
    assert len(client.get("/api/sheets").json()) == count


def test_a_tab_whose_choice_another_tab_ended_leaves_no_record_to_ask_again(tabs):
    """Tab 2 holds the work tab 1 kept, and its save finds A gone only after tab 1's keep: its
    choice ends, and the record of the deleted sheet goes with it: the next start asks nothing."""
    client, sheet_id, page1, page2 = tabs
    held = []
    page2.route(
        f"**/api/sheets/{sheet_id}",
        lambda route: held.append(route) if route.request.method == "PATCH" else route.continue_(),
    )
    pick(page2, "a")
    with page2.expect_request(lambda r: r.method == "PATCH"):
        page2.keyboard.press("ArrowRight")
    new = change_and_keep(client, sheet_id, page1)
    held[0].continue_()
    expect(page2).to_have_url(re.compile(rf"/blatt/{new}$"))
    page2.goto(page2.url.rsplit("/blatt/", 1)[0])
    expect(page2.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    expect(page2.locator(NOTICE)).to_have_count(0)
    assert record(page2, sheet_id) is None


def test_a_keep_from_a_tab_open_on_the_other_tabs_sheet_makes_its_own_and_loses_nothing(tabs):
    """Tab 2 finds A gone with other work, then opens the sheet tab 1 made: that sheet's editor
    would not take the change up, so the keep from the line makes a sheet of its own."""
    client, sheet_id, page1, page2 = tabs
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    new = change_and_keep(client, sheet_id, page1)
    page2.goto(page1.url)
    expect(page2.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    line = page2.locator(NOTICE)
    expect(line).to_contain_text(GONE)
    count = len(client.get("/api/sheets").json())
    line.get_by_role("button", name=KEEP).click()
    expect(page2).not_to_have_url(re.compile(rf"/blatt/({new}|{sheet_id})$"))
    expect(page2).to_have_url(re.compile(r"/blatt/\d+$"))
    sheets = client.get("/api/sheets").json()
    assert len(sheets) == count + 1
    made = client.get(f"/api/sheets/{page2.url.rsplit('/', 1)[1]}").json()
    assert made["doc"]["pages"][0]["blocks"][0]["x"] == 14


def test_when_both_tabs_hold_changes_tab_two_clashes_and_overwrites_nothing(tabs):
    """Tab 1 keeps A and changes the new sheet again; tab 2 then keeps its other work. Tab 1 ends
    with its change, saved; tab 2 ends on the same sheet with its own change on screen and the
    clash's choice; the server holds tab 1's change until tab 2 chooses."""
    client, sheet_id, page1, page2 = tabs
    new = change_and_keep(client, sheet_id, page1)
    pick(page1, "a")
    page1.keyboard.press("ArrowRight")
    expect(page1.locator("header [role=status]")).to_have_text("Gespeichert")
    tab1 = client.get(f"/api/sheets/{new}").json()["doc"]["pages"][0]["blocks"][0]["x"]
    assert tab1 == 17
    pick(page2, "a")
    page2.keyboard.press("ArrowLeft")
    expect(page2.locator(".clash")).to_contain_text(GONE)
    page2.get_by_role("button", name=KEEP).click()
    expect(page2).to_have_url(re.compile(rf"/blatt/{new}$"))
    clash = page2.locator(".clash")
    expect(clash.get_by_role("button", name="Andere Version laden")).to_be_visible()
    expect(clash.get_by_role("button", name="Mit dieser überschreiben")).to_be_visible()
    # Tab 2 sends nothing while it shows the clash: the server keeps tab 1's change.
    with page2.expect_request(lambda r: r.method == "GET" and "/api/sheets" in r.url):
        page2.goto(page2.url.rsplit("/blatt/", 1)[0])
    assert client.get(f"/api/sheets/{new}").json()["doc"]["pages"][0]["blocks"][0]["x"] == 17
    expect(page1.locator(".clash")).to_have_count(0)
    expect(page1.locator("header [role=status]")).to_have_text("Gespeichert")
    # Tab 2's own change is still kept for the clash: back on the sheet it shows again.
    page2.goto(page1.url)
    expect(
        page2.locator(".clash").get_by_role("button", name="Mit dieser überschreiben")
    ).to_be_visible()
    assert record(page2, int(new))["doc"]["pages"][0]["blocks"][0]["x"] == 14


def test_an_unchanged_tab_follows_the_drop_another_unchanged_tab_chose(tabs):
    """#736: neither tab has a change. Tab 1 learns of the delete as it gets the focus and drops
    the sheet; tab 2, as it gets the focus, follows that choice and asks nothing."""
    _, sheet_id, page1, page2 = tabs
    page1.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page1.locator(".clash")).to_contain_text(GONE)
    page1.once("dialog", lambda dialog: dialog.accept())
    page1.get_by_role("button", name=DROP).click()
    expect(page1).not_to_have_url(re.compile(rf"/blatt/{sheet_id}$"))
    page2.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page2).not_to_have_url(re.compile(rf"/blatt/{sheet_id}$"))
    expect(page2.locator(".clash")).to_have_count(0)
