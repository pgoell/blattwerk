"""What teacher run 7 found in the families of Rechnen, as the editor shows it (#469, #470, #471).

The rules themselves are proven on the generator in test_maths_run7_gen.py; here the steps of
the issues run through the panel once.
"""

from playwright.sync_api import expect
from ui import at, box, maths, pick, user


def test_a4_a5_a7_division_neighbours_from_the_panel(editor):
    """A4, A5, A7: only : on, bis 10, Nachbaraufgaben, 2. Zahl: no task twice, only the second
    number moves, at most one family of 0, and the panel says that the limits give no more."""
    client = user()
    props = maths(client, ops=["/"], max=10, count=12, family="neighbour")
    page = editor(box("m", "maths", props, y=20, h=200), client=client)
    pick(page, "m")
    page.get_by_label("2. Zahl wandert").click()
    panel = page.locator(".panel")
    expect(
        panel.get_by_text("Mit diesen Grenzen gibt es nur 2 verschiedene Familien.")
    ).to_be_visible()
    families = at(page, "m").locator(".maths .family")
    expect(families).to_have_count(2)
    shown = [families.nth(i).locator("div").all_inner_texts() for i in range(2)]
    tasks = [" ".join(text.split()) for family in shown for text in family]
    assert len(set(tasks)) == len(tasks) == 6, tasks
    firsts = [{task.split(" : ")[0] for task in family} for family in shown]
    assert all(len(first) == 1 for first in firsts), shown
    assert sum(first == {"0"} for first in firsts) <= 1, shown
    assert {"6"} in firsts, shown
