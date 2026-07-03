"""
Tests for BooleanChoices.
Path: utils/tests/test_choices.py
"""

from utils.models import BooleanChoices


class YesNoChoices(BooleanChoices):
    YES = True, "Yes"
    NO = False, "No"


class TestBooleanChoices:
    """Test the BooleanChoices base class."""

    def test_yes_value_is_true(self):
        assert YesNoChoices.YES.value is True

    def test_no_value_is_false(self):
        assert YesNoChoices.NO.value is False

    def test_yes_label_is_yes(self):
        assert YesNoChoices.YES.label == "Yes"

    def test_no_label_is_no(self):
        assert YesNoChoices.NO.label == "No"

    def test_choices_tuple_matches_defined_members(self):
        assert YesNoChoices.choices == [(True, "Yes"), (False, "No")]
