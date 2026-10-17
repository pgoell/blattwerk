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
