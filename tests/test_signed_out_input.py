"""Changes made with the session run out: a maths click and typed words are kept and saved after the
sign-in (issues #810 and #813). The session goes by `page.context.clear_cookies()`, the login by hand,
as in test_signed_out.py.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

import json

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_saves import NOTICE, STATUS
from test_signed_out import WATCH, expect_login, expect_sheet, login
from ui import TEXT, at, box, maths, pick, sheet, user

WAITS = "Die letzte Änderung an „m“ ist noch nicht gespeichert. Melde dich neu an, dann wird sie gespeichert."


def count_of(client, sheet_id):
    """The Aufgaben count of the maths block on the server's copy of the sheet."""
    doc = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    return doc["pages"][0]["blocks"][0]["props"]["count"]


def maths_sheet(window, server, count):
    """A sheet with one maths block of `count` Aufgaben, opened and picked. Gives the page, the client and the sheet id."""
    page, client = window()
    props = maths(client, format="row", ops=["+"], max=20, count=count)
    made = sheet(client, [box("m", "maths", props, y=20, h=60)], title="m")
    page.goto(f"{server}/blatt/{made['id']}")
    expect_sheet(page)
    pick(page, "m")
    return page, client, made["id"]


def test_a8_eine_aufgabe_weniger_after_the_session_ran_out_is_kept_and_saved_after_the_sign_in(
    window, server
):
    """A8: the login shows with the red bar, and after the sign-in the block has one task less, saved."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    login(page, server, client)
    expect_sheet(page)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    # The redo comes after the login, from the server's maths, and its save follows it.
    for _ in range(50):
        if count_of(client, sheet_id) == 13:
            break
        page.wait_for_timeout(100)
    assert count_of(client, sheet_id) == 13


def seed_of(client, sheet_id):
    """The seed of the maths block on the server's copy of the sheet."""
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"][0]["props"][
        "seed"
    ]


def test_a9_neu_wuerfeln_after_the_session_ran_out_is_redone_and_saved_after_the_sign_in(
    window, server
):
    """A9: the login shows with the red bar, and after the sign-in the block has other numbers, saved."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    before = seed_of(client, sheet_id)
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.get_by_role("button", name="Neu würfeln").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    login(page, server, client)
    expect_sheet(page)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    for _ in range(50):
        if seed_of(client, sheet_id) != before:
            break
        page.wait_for_timeout(100)
    assert seed_of(client, sheet_id) != before


def test_a10_eine_spalte_mehr_after_the_session_ran_out_is_saved_after_the_sign_in(window, server):
    """A10: a plain change still brings the login with the red bar, and is saved after the sign-in."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    columns = client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"][0]["props"][
        "columns"
    ]
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.get_by_label("Eine Spalte mehr").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    login(page, server, client)
    expect_sheet(page)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    doc = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    assert doc["pages"][0]["blocks"][0]["props"]["columns"] == columns + 1


def text_sheet(window, server):
    """A sheet with one text, opened and picked for typing. Gives the page, the client and the sheet id."""
    page, client = window()
    made = sheet(client, [box("t", "text", TEXT)], title="t")
    page.goto(f"{server}/blatt/{made['id']}")
    expect_sheet(page)
    pick(page, "t")
    page.keyboard.press("Enter")
    return page, client, made["id"]


def words_of(client, sheet_id):
    return json.dumps(client.get(f"/api/sheets/{sheet_id}").json()["doc"])


def test_a11_words_typed_after_the_session_ran_out_are_kept_and_saved_after_the_sign_in(
    window, server
):
    """A11: words typed with the session gone are in the text and saved after the sign-in (#813)."""
    page, client, sheet_id = text_sheet(window, server)
    address = f"{server}/blatt/{sheet_id}"
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.keyboard.type(" Katze")
    expect_login(page, address)
    login(page, server, client)
    expect_sheet(page)
    expect(at(page, "t")).to_contain_text("Katze")
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert "Katze" in words_of(client, sheet_id)


def test_a11_words_typed_after_the_login_shows_are_kept_and_saved_after_the_sign_in(window, server):
    """A11b: words typed once the login form shows are in the text after the sign-in (#813)."""
    page, client, sheet_id = text_sheet(window, server)
    address = f"{server}/blatt/{sheet_id}"
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.keyboard.type(" Katze")
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS.replace("„m“", "„t“"))
    page.keyboard.type(" Hund")
    login(page, server, client)
    expect_sheet(page)
    expect(at(page, "t")).to_contain_text("Katze")
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert "Katze" in words_of(client, sheet_id)
    assert "Hund" not in words_of(client, sheet_id)


def count_after_click(window, server):
    """A maths sheet with 14 Aufgaben, whose one-less click the session ran out on. Gives the page, the client, the sheet id and its address."""
    page, client, sheet_id = maths_sheet(window, server, 14)
    address = f"{server}/blatt/{sheet_id}"
    page.evaluate(WATCH)
    page.context.clear_cookies()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    return page, client, sheet_id, address


def wait_count(client, sheet_id, page, count):
    """Waits for the server's count, which the saves of a redo bring along."""
    for _ in range(50):
        if count_of(client, sheet_id) == count:
            break
        page.wait_for_timeout(100)
    assert count_of(client, sheet_id) == count


def test_a8r_the_one_less_click_is_kept_by_a_reload_of_the_login_page(window, server):
    """A8 reload: the click owed is kept in the browser, so a reload of the login page still redoes it."""
    page, client, sheet_id, address = count_after_click(window, server)
    page.reload()
    expect_login(page, address)
    login(page, server, client)
    expect_sheet(page)
    wait_count(client, sheet_id, page, 13)


def test_i5_one_undo_after_the_sign_in_takes_the_redone_click_back(window, server):
    """I5: after the sign-in one Ctrl+Z takes the redone click back: the count is 14 again."""
    page, client, sheet_id, _ = count_after_click(window, server)
    login(page, server, client)
    expect_sheet(page)
    wait_count(client, sheet_id, page, 13)
    pick(page, "m")
    page.keyboard.press("Control+z")
    wait_count(client, sheet_id, page, 14)


def test_i6_another_teacher_signing_in_at_that_login_gets_none_of_the_owed_click(window, server):
    """I6: B signs in at the login A's click brought. B sees nothing of A's sheet and the server keeps A's count."""
    page, client, sheet_id, address = count_after_click(window, server)
    other = user()
    login(page, server, other)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    expect(page.locator(NOTICE)).to_have_count(0)
    assert count_of(client, sheet_id) == 14
    page.context.clear_cookies()
    page.goto(address)
    expect_login(page, address)
    login(page, server, client)
    expect_sheet(page)
    wait_count(client, sheet_id, page, 13)
