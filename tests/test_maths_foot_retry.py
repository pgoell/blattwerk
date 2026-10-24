"""A refused click adds no undo step, and a late answer does not land over a newer one."""

from playwright.sync_api import expect
from test_maths_foot import (
    FOOT,
    FRAMES,
    asked,
    click,
    height,
    refusal,
    tasks,
)
from ui import (
    at,
    box,
    maths,
    pick,
    saved,
    user,
)


def test_i1_a_refused_click_is_no_step_of_undo(editor):
    """I1: a refused change is no undo step: one Control+z takes back the last change that went."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(tasks(page).first).to_have_text("11 Aufgaben")
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(tasks(page).first).to_have_text("11 Aufgaben")


def test_i1b_a_quick_second_click_keeps_the_first_when_its_answer_is_late(editor):
    """I1b: two quick clicks on "mehr": the first answer comes late, and it still counts; the second is refused."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    sent = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on, and later ones too.
        sent.append(route)
        if len(sent) == 2:
            sent[0].continue_()
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(tasks(page).first).to_have_text("11 Aufgaben")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(tasks(page).first).to_have_text("11 Aufgaben")


def test_i1c_a_quick_more_then_less_ends_at_the_height_it_had(editor):
    """I1c: "mehr" then "weniger" quickly, the first answer late: the second is measured on the
    block the first left, so the block ends with its 9 tasks at the height of 3 rows."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    sent = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on, and later ones too.
        sent.append(route)
        if len(sent) == 2:
            sent[0].continue_()
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe weniger").click()
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    expect(tasks(page).first).to_have_text("9 Aufgaben")
    (block,) = saved(page, client)
    assert block["h"] == height(props)


def test_i1d_two_quick_clicks_that_both_count_are_two_undo_steps(editor):
    """I1d: "mehr" twice quickly, the first answer late, both fit: one Control+z takes back one."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    sent = []

    def hold(route):
        # The first answer waits until the second click is sent; then both go on, and later ones too.
        sent.append(route)
        if len(sent) == 2:
            sent[0].continue_()
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(at(page, "m").locator(".maths > div")).to_have_count(11)
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    expect(tasks(page).first).to_have_text("10 Aufgaben")


def test_i1e_a_retried_old_click_does_not_land_over_a_newer_one(editor):
    """I1e: "mehr" fails, its retry comes late, "weniger" was clicked meanwhile: "weniger" stays."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    pick(page, "m")
    page.route("**/api/maths", lambda route: route.abort())
    page.get_by_label("Eine Aufgabe mehr").click()
    again = page.get_by_role("button", name="Erneut versuchen")
    expect(again).to_be_visible()
    held = []
    page.unroute("**/api/maths")
    page.route("**/api/maths", lambda route: held.append(route) if not held else route.continue_())
    again.click()
    asked(click("Eine Aufgabe weniger"))(page)
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    with page.expect_response(lambda r: r.url.endswith("/api/maths")):
        held.pop().continue_()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    expect(tasks(page).first).to_have_text("9 Aufgaben")


def test_i1f_a_click_before_a_refused_answer_builds_on_the_blocks_own(editor):
    """I1f: "mehr" is refused for want of room, "Spalte mehr" is clicked before that answer lands: it builds on the block's own 12 tasks."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    sent = []

    def hold(route):
        # Only the first request waits; the ones after it, "Spalte mehr" too, go on.
        sent.append(route)
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Spalte mehr").click()
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    sent[0].continue_()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    (block,) = saved(page, client)
    assert block["props"]["columns"] == 4
    assert len(block["props"]["exercises"]) == block["props"]["count"]
    # Two undo steps, in the order they landed: the late answer, then the column.
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    page.keyboard.press("Control+z")
    expect(tasks(page).nth(1)).to_have_text("3 Spalten")


def test_i1g_a_limit_click_before_a_refused_answer_drops_the_refused_count(editor):
    """I1g: "mehr" is refused, "Neu würfeln" is clicked before that answer lands: it is applied on 12 tasks, not 13."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    sent = []

    def hold(route):
        # Only the first request waits; the ones after it, the retry of the second click too, go on.
        sent.append(route)
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    sent[0].continue_()
    expect(page.locator('[data-foot="full"]')).to_be_hidden()
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    (block,) = saved(page, client)
    assert block["props"]["count"] == 12
    assert len(block["props"]["exercises"]) == 12
    # Neu würfeln took: on master it carried the refused 13 and was refused with it.
    assert block["props"]["exercises"] != props["exercises"]


def test_i1h_a_failed_clicks_line_goes_when_a_later_click_lands(editor):
    """I1h: "mehr" fails, "weniger" lands after it: the line of the failed click goes, the block ends with 9 tasks."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    sent = []

    def hold(route):
        # Only the first request waits; the ones after it, "weniger" too, go on.
        sent.append(route)
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_label("Eine Aufgabe weniger").click()
    sent[0].abort()
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)
    expect(tasks(page).first).to_have_text("9 Aufgaben")
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(page.get_by_role("button", name="Erneut versuchen")).to_be_hidden()
    expect(
        page.locator(".notice.fault").filter(has_text="Die Aufgaben konnten nicht erzeugt werden")
    ).to_have_count(0)


def test_i1j_a_failed_clicks_change_rides_on_the_next_click(editor):
    """I1j: "mehr" fails, "Neu würfeln" lands after it: failed is not refused, so the block gets 10 tasks."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    sent = []

    def hold(route):
        # Only the first request waits; the ones after it, "Neu würfeln" too, go on.
        sent.append(route)
        if len(sent) > 1:
            route.continue_()

    pick(page, "m")
    page.route("**/api/maths", hold)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    sent[0].abort()
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    expect(tasks(page).first).to_have_text("10 Aufgaben")
    expect(page.get_by_role("button", name="Erneut versuchen")).to_be_hidden()


def test_i1k_a_moot_retry_that_fails_again_says_nothing(editor):
    """I1k: "mehr" fails, its retry is on its way when "weniger" lands, then the retry fails too: no line."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=9, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=40, h=height(props)), client=client)
    pick(page, "m")
    page.route("**/api/maths", lambda route: route.abort())
    page.get_by_label("Eine Aufgabe mehr").click()
    again = page.get_by_role("button", name="Erneut versuchen")
    expect(again).to_be_visible()
    sent = []

    def hold(route):
        # Only the retry waits; the click after it, "weniger" too, goes on.
        sent.append(route)
        if len(sent) > 1:
            route.continue_()

    page.unroute("**/api/maths")
    page.route("**/api/maths", hold)
    again.click()
    asked(click("Eine Aufgabe weniger"))(page)
    expect(tasks(page).first).to_have_text("9 Aufgaben")
    sent[0].abort()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(again).to_be_hidden()
    expect(at(page, "m").locator(".maths > div")).to_have_count(9)


def test_i1l_a_column_clicked_while_the_re_ask_is_on_its_way_stays(editor):
    """I1l (review): "mehr" refused, "Neu würfeln" asked again without it, "Spalte mehr" while that is on its way: 4 stays."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    held = []
    sent = []

    def route(r):
        sent.append(r)
        if len(sent) == 2:
            r.continue_()
        else:
            held.append(r)

    pick(page, "m")
    page.route("**/api/maths", route)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    for _ in range(50):
        if len(sent) == 2:
            break
        page.evaluate(FRAMES)
    held.pop().continue_()
    for _ in range(50):
        if held:
            break
        page.evaluate(FRAMES)
    assert held, "the click was not asked again"
    page.get_by_label("Eine Spalte mehr").click()
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    held.pop().continue_()
    page.evaluate(FRAMES)
    page.evaluate(FRAMES)
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    (block,) = saved(page, client)
    assert block["props"]["columns"] == 4
    assert block["props"]["count"] == 12


def test_i1m_a_401_on_the_re_ask_is_owed(editor):
    """I1m (review): the re-ask without the refused 13 meets a run out session: the click is owed for after the login."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    held = []
    sent = []

    def route(r):
        sent.append(r)
        if len(sent) == 1:
            held.append(r)
        elif len(sent) == 2:
            r.continue_()
        else:
            r.fulfill(status=401, body="{}")

    pick(page, "m")
    page.route("**/api/maths", route)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    for _ in range(50):
        if len(sent) == 2:
            break
        page.evaluate(FRAMES)
    held.pop().continue_()
    page.wait_for_function(
        "() => Object.keys(localStorage).some((k) => k.startsWith('owed:') && localStorage.getItem(k) !== '[]')"
    )


def test_i1n_a_refused_count_leaves_the_panel_when_the_last_click_fails(editor):
    """I1n (review): "mehr" refused, "Neu würfeln" fails: the panel shows the block's own 12, not the refused 13."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    held = []
    sent = []

    def route(r):
        sent.append(r)
        if len(sent) == 1:
            held.append(r)
        else:
            r.abort()

    pick(page, "m")
    page.route("**/api/maths", route)
    page.get_by_label("Eine Aufgabe mehr").click()
    page.get_by_role("button", name="Neu würfeln").click()
    for _ in range(50):
        if len(sent) == 2:
            break
        page.evaluate(FRAMES)
    held.pop().continue_()
    expect(page.get_by_role("button", name="Erneut versuchen")).to_be_visible()
    expect(tasks(page).first).to_have_text("12 Aufgaben")
