from hypothesis import given, settings
from hypothesis import strategies as st

from blattwerk.maths import Settings, generate, school


def tasks_of(out):
    return [(e["op"], e["a"], e["b"]) for e in out["exercises"]]


def families_of(out):
    """The tasks of each family, in order: the drawn task first."""
    by_number: dict[int, list[dict]] = {}
    for e in out["exercises"]:
        by_number.setdefault(e["family"], []).append(e)
    return [by_number[n] for n in sorted(by_number)]


def test_a4_no_task_stands_twice_in_a_block_of_neighbours():
    settings_list = [
        lambda seed: Settings(
            ops=["/"], max=10, family="neighbour", moves="b", count=12, seed=seed
        ),
        lambda seed: Settings(
            ops=["*", "/"],
            max=10,
            one=False,
            distinct=True,
            format="gap",
            gaps=["b"],
            family="neighbour",
            moves="b",
            count=12,
            seed=seed,
        ),
    ]
    for make in settings_list:
        for seed in range(100):
            out = generate(make(seed))
            tasks = tasks_of(out)
            assert len(set(tasks)) == len(tasks)
            if len(families_of(out)) < 12:
                assert out["loosen"] is not None


@settings(max_examples=100, deadline=None)
@given(
    # Every set holds the division, where the repeats of #469 were found.
    ops=st.lists(st.sampled_from("+-*/"), min_size=1, max_size=4, unique=True).map(
        lambda ops: ops if "/" in ops else [*ops, "/"]
    ),
    max=st.sampled_from([10, 20, 100]),
    family=st.sampled_from(["swap", "reverse", "neighbour"]),
    moves=st.sampled_from(["a", "b"]),
    count=st.integers(1, 12),
    seed=st.integers(0, 10**6),
)
def test_a4_no_task_stands_twice_in_any_family_block(ops, max, family, moves, count, seed):
    out = generate(Settings(ops=ops, max=max, family=family, moves=moves, count=count, seed=seed))
    tasks = tasks_of(out)
    assert len(set(tasks)) == len(tasks)


def test_a5_a_division_neighbour_moves_only_its_second_number():
    for seed in range(100):
        top = 100 if seed % 2 == 0 else 10
        out = generate(
            Settings(ops=["/"], max=top, family="neighbour", moves="b", count=12, seed=seed)
        )
        fams = families_of(out)
        for fam in fams:
            a, b = fam[0]["a"], fam[0]["b"]
            assert [(e["a"], e["b"]) for e in fam] == [(a, b), (a, b - 1), (a, b + 1)]
            assert all(e["rest"] == 0 and e["a"] % e["b"] == 0 for e in fam)
    assert fams


def test_a5_with_a_rest_only_the_second_number_moves_too():
    for seed in range(100):
        out = generate(
            Settings(
                ops=["/"], max=100, family="neighbour", moves="b", count=12, rest=True, seed=seed
            )
        )
        fams = families_of(out)
        for fam in fams:
            a, b = fam[0]["a"], fam[0]["b"]
            assert [(e["a"], e["b"]) for e in fam] == [(a, b), (a, b - 1), (a, b + 1)]
            assert all(e["rest"] > 0 for e in fam)
    assert fams


def test_a7_plain_families_are_at_most_one_in_ten():
    for seed in range(100):
        moves = "a" if seed % 2 else "b"
        cases = [
            (Settings(ops=["/"], max=10, family="neighbour", moves="b", count=12, seed=seed), 12),
            (
                Settings(
                    ops=["*", "/"], max=20, family="neighbour", moves=moves, count=12, seed=seed
                ),
                12,
            ),
            (Settings(ops=["*"], max=100, family="swap", count=20, seed=seed), 20),
        ]
        for s, count in cases:
            out = generate(s)
            plain = [
                fam
                for fam in families_of(out)
                if not school(fam[0]["op"], fam[0]["a"], fam[0]["b"])
            ]
            assert len(plain) <= count // 10
            if s.max == 10:
                assert sum(e["a"] == 0 for e in out["exercises"]) <= 3


def test_a8_at_most_one_task_in_ten_comes_to_0_or_1():
    for seed in range(100):
        out = generate(
            Settings(
                ops=["+", "-", "*", "/"],
                max=100,
                numbers=3,
                pvs=True,
                brackets=True,
                count=24,
                seed=seed,
            )
        )
        assert len(out["exercises"]) == 24
        assert sum(e["result"] in (0, 1) for e in out["exercises"]) <= 2
