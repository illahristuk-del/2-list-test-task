"""Unit tests for the pure logic in app.service.

These cover the two helpers that have no database or HTTP involvement:
the input hash (which produces the payload id) and the interleaving that
assembles the output. They are the heart of the task's correctness, so they
are tested in isolation, without any fixtures.
"""

from app.schemas import PayloadCreate
from app.service import _hash_input, _interleave


class TestHashInput:
    """The payload id must be a deterministic, collision-free hash of the input."""

    def test_same_input_same_hash(self):
        """Identical input must map to the same id — this is what makes
        'reuse the identifier' work."""
        a = PayloadCreate(list_1=["first string"], list_2=["other string"])
        b = PayloadCreate(list_1=["first string"], list_2=["other string"])
        assert _hash_input(a) == _hash_input(b)

    def test_order_changes_hash(self):
        """Order affects the interleaving, so it must affect the id too:
        swapping element order is a different request."""
        a = PayloadCreate(list_1=["a", "b"], list_2=["c", "d"])
        b = PayloadCreate(list_1=["b", "a"], list_2=["c", "d"])
        assert _hash_input(a) != _hash_input(b)

    def test_swapped_lists_change_hash(self):
        """Swapping list_1 and list_2 yields a different interleaving, so the
        id must differ as well."""
        a = PayloadCreate(list_1=["a"], list_2=["b"])
        b = PayloadCreate(list_1=["b"], list_2=["a"])
        assert _hash_input(a) != _hash_input(b)

    def test_no_collision_on_separator(self):
        """The critical case: a naive join on ',' would make these two inputs
        hash the same. The JSON-based canonicalization must keep them distinct.
        """
        a = PayloadCreate(list_1=["a,b"], list_2=["c"])
        b = PayloadCreate(list_1=["a"], list_2=["b,c"])
        assert _hash_input(a) != _hash_input(b)

    def test_hash_is_hex_sha256(self):
        """Sanity check on the id shape: a 64-char hex sha256 digest."""
        h = _hash_input(PayloadCreate(list_1=["x"], list_2=["y"]))
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestInterleave:
    """The output is the two transformed lists woven together, one from each
    in turn, joined by ', '."""

    def test_basic_interleave(self):
        """One item from each list, alternating, in order."""
        result = _interleave(["A", "B", "C"], ["X", "Y", "Z"])
        assert result == "A, X, B, Y, C, Z"

    def test_matches_task_example(self):
        """The exact example from the task description must come out verbatim."""
        result = _interleave(
            ["FIRST STRING", "SECOND STRING", "THIRD STRING"],
            ["OTHER STRING", "ANOTHER STRING", "LAST STRING"],
        )
        assert result == (
            "FIRST STRING, OTHER STRING, SECOND STRING, "
            "ANOTHER STRING, THIRD STRING, LAST STRING"
        )

    def test_single_element(self):
        """Smallest non-trivial case."""
        assert _interleave(["A"], ["B"]) == "A, B"
