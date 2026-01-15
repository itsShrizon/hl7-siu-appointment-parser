"""Unit tests for field utility functions."""
import pytest
from hl7_siu_parser.field_utils import (
    get_field_value,
    get_component_value,
    get_first_repetition,
    looks_like_datetime,
    extract_datetime_from_timing,
)


class TestGetFieldValue:
    """Tests for get_field_value function."""

    def test_valid_index(self):
        """Get field at valid index."""
        fields = ["MSH", "^~\\&", "APP", "FAC"]
        assert get_field_value(fields, 0) == "MSH"
        assert get_field_value(fields, 2) == "APP"
        assert get_field_value(fields, 3) == "FAC"

    def test_out_of_bounds_high(self):
        """Out of bounds index returns empty string."""
        fields = ["MSH", "^~\\&", "APP"]
        assert get_field_value(fields, 99) == ""
        assert get_field_value(fields, 5) == ""

    def test_out_of_bounds_negative(self):
        """Negative index returns empty string."""
        fields = ["MSH", "^~\\&", "APP"]
        assert get_field_value(fields, -1) == ""
        assert get_field_value(fields, -99) == ""

    def test_empty_list(self):
        """Empty list returns empty string for any index."""
        assert get_field_value([], 0) == ""
        assert get_field_value([], 5) == ""

    def test_none_value_in_list(self):
        """None value in list returns empty string."""
        fields = ["MSH", None, "APP"]
        assert get_field_value(fields, 1) == ""

    def test_empty_string_in_list(self):
        """Empty string in list returns empty string."""
        fields = ["MSH", "", "APP"]
        assert get_field_value(fields, 1) == ""


class TestGetComponentValue:
    """Tests for get_component_value function."""

    def test_valid_components(self):
        """Extract components from field."""
        field = "Doe^John^M"
        assert get_component_value(field, 0) == "Doe"
        assert get_component_value(field, 1) == "John"
        assert get_component_value(field, 2) == "M"

    def test_out_of_bounds(self):
        """Out of bounds component returns empty string."""
        field = "Doe^John"
        assert get_component_value(field, 5) == ""
        assert get_component_value(field, 99) == ""

    def test_empty_field(self):
        """Empty field returns empty string."""
        assert get_component_value("", 0) == ""
        assert get_component_value("", 1) == ""

    def test_no_separator(self):
        """Field without separator returns whole string for index 0."""
        field = "SimpleValue"
        assert get_component_value(field, 0) == "SimpleValue"
        assert get_component_value(field, 1) == ""

    def test_empty_components(self):
        """Handle empty components (consecutive separators)."""
        field = "First^^Third"
        assert get_component_value(field, 0) == "First"
        assert get_component_value(field, 1) == ""
        assert get_component_value(field, 2) == "Third"

    def test_custom_separator(self):
        """Use custom component separator."""
        field = "First#Second#Third"
        assert get_component_value(field, 0, "#") == "First"
        assert get_component_value(field, 1, "#") == "Second"
        assert get_component_value(field, 2, "#") == "Third"

    def test_all_empty_components(self):
        """Handle all empty components."""
        field = "^^^"
        assert get_component_value(field, 0) == ""
        assert get_component_value(field, 1) == ""
        assert get_component_value(field, 2) == ""
        assert get_component_value(field, 3) == ""


class TestGetFirstRepetition:
    """Tests for get_first_repetition function."""

    def test_single_value(self):
        """Single value returns itself."""
        assert get_first_repetition("ID001") == "ID001"

    def test_multiple_repetitions(self):
        """Multiple repetitions returns first."""
        assert get_first_repetition("ID001~ID002~ID003") == "ID001"

    def test_empty_first_repetition(self):
        """Empty first repetition returns empty string."""
        assert get_first_repetition("~ID002~ID003") == ""

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert get_first_repetition("") == ""

    def test_custom_separator(self):
        """Use custom repetition separator."""
        assert get_first_repetition("A|B|C", "|") == "A"

    def test_only_separators(self):
        """Only separators returns empty string."""
        assert get_first_repetition("~~~") == ""


class TestLooksLikeDatetime:
    """Tests for looks_like_datetime function."""

    def test_date_only(self):
        """8-digit date recognized."""
        assert looks_like_datetime("20250502") is True

    def test_date_with_time(self):
        """Date with time recognized."""
        assert looks_like_datetime("20250502130000") is True

    def test_date_with_timezone(self):
        """Date with timezone recognized."""
        assert looks_like_datetime("20250502130000+0500") is True
        assert looks_like_datetime("20250502130000-0800") is True

    def test_too_short(self):
        """Strings shorter than 8 chars rejected."""
        assert looks_like_datetime("2025050") is False
        assert looks_like_datetime("2025") is False
        assert looks_like_datetime("") is False

    def test_non_numeric(self):
        """Non-numeric strings rejected."""
        assert looks_like_datetime("abcdefgh") is False
        assert looks_like_datetime("2025-05-02") is False  # ISO format

    def test_partial_numeric(self):
        """First 8 chars must be numeric."""
        assert looks_like_datetime("20250a02") is False
        assert looks_like_datetime("2025050X") is False


class TestExtractDatetimeFromTiming:
    """Tests for extract_datetime_from_timing function."""

    def test_simple_datetime(self):
        """Simple datetime string extracted."""
        assert extract_datetime_from_timing("20250502130000", "^") == "20250502130000"

    def test_component_based(self):
        """Datetime in components extracted."""
        timing = "^^^20250502130000^20250502140000"
        assert extract_datetime_from_timing(timing, "^") == "20250502130000"

    def test_first_datetime_found(self):
        """First datetime-like component returned."""
        timing = "Label^Description^20250502130000^20250502140000"
        assert extract_datetime_from_timing(timing, "^") == "20250502130000"

    def test_empty_field(self):
        """Empty field returns None."""
        assert extract_datetime_from_timing("", "^") is None

    def test_no_datetime(self):
        """No datetime in field returns None."""
        timing = "Label^Description^Info"
        assert extract_datetime_from_timing(timing, "^") is None

    def test_only_separators(self):
        """Only separators returns None."""
        assert extract_datetime_from_timing("^^^^", "^") is None

    def test_custom_separator(self):
        """Works with custom separator."""
        timing = "###20250502130000#20250502140000"
        assert extract_datetime_from_timing(timing, "#") == "20250502130000"
