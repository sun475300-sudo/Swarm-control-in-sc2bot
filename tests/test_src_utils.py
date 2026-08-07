"""Tests for the helpers under src.utils."""

import math

import pytest
from src.utils import (
    cache_utils,
    data_utils,
    format_utils,
    math_utils,
    string_utils,
    time_utils,
    validation_utils,
)


class TestMathUtils:
    def test_clamp_within_range(self):
        assert math_utils.clamp(5, 0, 10) == 5

    def test_clamp_below_low(self):
        assert math_utils.clamp(-1, 0, 10) == 0

    def test_clamp_above_high(self):
        assert math_utils.clamp(11, 0, 10) == 10

    def test_clamp_invalid_range(self):
        with pytest.raises(ValueError):
            math_utils.clamp(0, 5, 1)

    def test_lerp_endpoints(self):
        assert math_utils.lerp(0.0, 10.0, 0.0) == 0.0
        assert math_utils.lerp(0.0, 10.0, 1.0) == 10.0

    def test_lerp_midpoint(self):
        assert math_utils.lerp(0.0, 10.0, 0.5) == 5.0

    def test_distance(self):
        assert math_utils.distance((0, 0), (3, 4)) == 5.0

    def test_manhattan(self):
        assert math_utils.manhattan((0, 0), (3, 4)) == 7

    def test_normalize_zero_vector(self):
        assert math_utils.normalize((0.0, 0.0)) == (0.0, 0.0)

    def test_normalize_unit_length(self):
        nx, ny = math_utils.normalize((3.0, 4.0))
        assert math.isclose(math.hypot(nx, ny), 1.0, rel_tol=1e-9)

    def test_angle_between(self):
        assert math_utils.angle_between((0, 0), (1, 0)) == 0.0
        assert math.isclose(
            math_utils.angle_between((0, 0), (0, 1)), math.pi / 2, rel_tol=1e-9
        )

    def test_sign(self):
        assert math_utils.sign(5) == 1
        assert math_utils.sign(-5) == -1
        assert math_utils.sign(0) == 0

    def test_mean(self):
        assert math_utils.mean([1, 2, 3, 4]) == 2.5

    def test_mean_empty_raises(self):
        with pytest.raises(ValueError):
            math_utils.mean([])

    def test_variance_zero_for_singleton(self):
        assert math_utils.variance([5]) == 0.0

    def test_stddev(self):
        assert math.isclose(
            math_utils.stddev([2, 4, 4, 4, 5, 5, 7, 9]), 2.0, rel_tol=1e-9
        )


class TestTimeUtils:
    def test_gameloop_to_seconds(self):
        assert math.isclose(time_utils.gameloop_to_seconds(224), 10.0, rel_tol=1e-9)

    def test_seconds_to_gameloop(self):
        assert time_utils.seconds_to_gameloop(10.0) == 224

    def test_format_duration_short(self):
        assert time_utils.format_duration(75) == "01:15"

    def test_format_duration_with_hours(self):
        assert time_utils.format_duration(3661) == "1:01:01"

    def test_parse_duration_mm_ss(self):
        assert time_utils.parse_duration("01:15") == 75

    def test_parse_duration_hh_mm_ss(self):
        assert time_utils.parse_duration("1:01:01") == 3661

    def test_parse_duration_invalid(self):
        with pytest.raises(ValueError):
            time_utils.parse_duration("garbage")

    def test_split_hms(self):
        assert time_utils.split_hms(3661) == (1, 1, 1)

    def test_negative_seconds_raises(self):
        with pytest.raises(ValueError):
            time_utils.format_duration(-1)


class TestStringUtils:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("CamelCase", "camel_case"),
            ("camelCase", "camel_case"),
            ("HTTPRequest", "http_request"),
            ("already_snake", "already_snake"),
        ],
    )
    def test_snake_case(self, raw, expected):
        assert string_utils.to_snake_case(raw) == expected

    def test_camel_case(self):
        assert string_utils.to_camel_case("hello_world") == "helloWorld"
        assert (
            string_utils.to_camel_case("hello-world", capitalize_first=True)
            == "HelloWorld"
        )
        assert string_utils.to_camel_case("") == ""

    def test_truncate_no_change(self):
        assert string_utils.truncate("abc", 5) == "abc"

    def test_truncate_with_ellipsis(self):
        assert string_utils.truncate("abcdef", 5, ellipsis="...") == "ab..."

    def test_truncate_invalid_length(self):
        with pytest.raises(ValueError):
            string_utils.truncate("abc", -1)

    def test_sanitize_filename(self):
        assert string_utils.sanitize_filename("a/b\\c?d") == "a_b_c_d"

    def test_sanitize_filename_falls_back(self):
        assert string_utils.sanitize_filename("..") == "_"

    def test_slugify(self):
        assert string_utils.slugify("Hello, World!") == "hello-world"


class TestValidationUtils:
    def test_is_in_range_inclusive(self):
        assert validation_utils.is_in_range(5, 0, 10)
        assert validation_utils.is_in_range(0, 0, 10)
        assert not validation_utils.is_in_range(11, 0, 10)

    def test_is_in_range_exclusive(self):
        assert not validation_utils.is_in_range(0, 0, 10, inclusive=False)
        assert validation_utils.is_in_range(5, 0, 10, inclusive=False)

    def test_is_in_range_invalid_bounds(self):
        with pytest.raises(ValueError):
            validation_utils.is_in_range(0, 5, 1)

    def test_is_finite_number(self):
        assert validation_utils.is_finite_number(3)
        assert validation_utils.is_finite_number(3.5)
        assert not validation_utils.is_finite_number(float("nan"))
        assert not validation_utils.is_finite_number(float("inf"))
        assert not validation_utils.is_finite_number("3")

    def test_is_non_empty(self):
        assert validation_utils.is_non_empty([1])
        assert not validation_utils.is_non_empty([])
        assert not validation_utils.is_non_empty(None)

    def test_ensure_type_ok(self):
        assert validation_utils.ensure_type(3, int) == 3

    def test_ensure_type_raises(self):
        with pytest.raises(TypeError):
            validation_utils.ensure_type("3", int)

    def test_ensure_in_range(self):
        assert validation_utils.ensure_in_range(5, 0, 10) == 5
        with pytest.raises(ValueError):
            validation_utils.ensure_in_range(11, 0, 10)

    def test_all_unique(self):
        assert validation_utils.all_unique([1, 2, 3])
        assert not validation_utils.all_unique([1, 1])

    def test_has_keys(self):
        assert validation_utils.has_keys({"a": 1, "b": 2}, ["a"])
        assert not validation_utils.has_keys({"a": 1}, ["b"])


class TestFormatUtils:
    def test_format_number(self):
        assert format_utils.format_number(1234567.891) == "1,234,567.89"

    def test_format_percent(self):
        assert format_utils.format_percent(0.512) == "51.2%"

    def test_format_resources(self):
        assert format_utils.format_resources(50, 0, (10, 14)) == "M=50 G=0 S=10/14"

    def test_format_resources_negative_supply(self):
        with pytest.raises(ValueError):
            format_utils.format_resources(50, 0, (-1, 14))

    def test_format_supply(self):
        assert format_utils.format_supply(10, 14) == "10/14"

    @pytest.mark.parametrize(
        "n,expected",
        [(0, "0 B"), (1024, "1.00 KB"), (1024 * 1024, "1.00 MB")],
    )
    def test_format_bytes(self, n, expected):
        assert format_utils.format_bytes(n) == expected

    def test_format_bytes_negative(self):
        with pytest.raises(ValueError):
            format_utils.format_bytes(-1)


class TestDataUtils:
    def test_chunked(self):
        assert list(data_utils.chunked(range(7), 3)) == [[0, 1, 2], [3, 4, 5], [6]]

    def test_chunked_invalid_size(self):
        with pytest.raises(ValueError):
            list(data_utils.chunked([1], 0))

    def test_flatten(self):
        assert data_utils.flatten([[1, 2], [3], []]) == [1, 2, 3]

    def test_unique_preserves_order(self):
        assert data_utils.unique([3, 1, 2, 3, 1]) == [3, 1, 2]

    def test_group_by(self):
        groups = data_utils.group_by(["aa", "ab", "bc"], key=lambda s: s[0])
        assert groups == {"a": ["aa", "ab"], "b": ["bc"]}

    def test_take(self):
        assert data_utils.take(range(5), 3) == [0, 1, 2]
        assert data_utils.take([1], 5) == [1]

    def test_take_negative(self):
        with pytest.raises(ValueError):
            data_utils.take([], -1)

    def test_deep_get(self):
        m = {"a": {"b": {"c": 1}}}
        assert data_utils.deep_get(m, ["a", "b", "c"]) == 1
        assert data_utils.deep_get(m, ["a", "x"], default=42) == 42


class TestLRUCache:
    def test_put_and_get(self):
        c = cache_utils.LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        assert c.get("a") == 1
        assert c.get("b") == 2

    def test_eviction_order(self):
        c = cache_utils.LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        assert c.get("a") is None
        assert "a" not in c

    def test_get_promotes_key(self):
        c = cache_utils.LRUCache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.get("a")
        c.put("c", 3)
        assert c.get("b") is None
        assert c.get("a") == 1

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            cache_utils.LRUCache(0)

    def test_clear(self):
        c = cache_utils.LRUCache(2)
        c.put("a", 1)
        c.clear()
        assert len(c) == 0
