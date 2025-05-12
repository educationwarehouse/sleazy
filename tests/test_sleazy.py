"""
Fixme: these tests were automatically generated and should still be manually confirmed!
"""

import enum
import typing as t

import pytest

from src.sleazy import (
    TypedDict,
    parse,
    parse_count_spec,
    stringify,
    strip_optional,
)


def test_parse_count_spec():
    # Exact numbers
    assert parse_count_spec("0") == 0
    assert parse_count_spec("1") == 1
    assert parse_count_spec("") == 1
    assert parse_count_spec("5") == 5

    # Direct argparse-style symbols
    assert parse_count_spec("+") == "+"
    assert parse_count_spec("*") == "*"
    assert parse_count_spec("?") == "?"

    # Comparison operators are not supported anymore → default to "?"
    for spec in ("> 0", "<=5", ">= 1", "==3", "<1", ">=0", "invalid", "foo"):
        with pytest.raises(SyntaxError):
            parse_count_spec(spec)


def test_strip_optional_all_cases():
    assert strip_optional(t.Optional[int]) is int
    assert strip_optional(str | None) is str
    assert strip_optional(t.Union[int, float, None]) == t.Union[int, float]
    assert strip_optional(int | float | None) == t.Union[int, float]
    assert strip_optional(int) is int
    assert strip_optional(t.Union[None, None]) is type(None)


def test_basic_type_parsing():
    class BasicTypes(t.TypedDict):
        string_val: t.Optional[str]
        int_val: int
        float_val: float
        bool_val: bool

    args = [
        "--string-val",
        "test",
        "--int-val",
        "42",
        "--float-val",
        "3.14",
        "--bool-val",
    ]
    result = parse(BasicTypes, args)

    assert result["string_val"] == "test"
    assert result["int_val"] == 42
    assert result["float_val"] == 3.14
    assert result["bool_val"] is True


def test_positional_args():
    class PositionalArgs(t.TypedDict):
        pos1: t.Annotated[str, "?"]
        pos2: t.Annotated[int, "?"]
        opt1: str | None

    args = ["value1", "42", "--opt1", "option"]
    result = parse(PositionalArgs, args)

    assert result["pos1"] == "value1"
    assert result["pos2"] == 42
    assert result["opt1"] == "option"


def test_literal_types():
    class LiteralTypes(t.TypedDict):
        mode: t.Literal["auto", "manual", "hybrid"]
        level: t.Literal[1, 2, 3]

    # Test valid literals
    args = ["--mode", "auto", "--level", "2"]
    result = parse(LiteralTypes, args)

    assert result["mode"] == "auto"
    assert result["level"] == 2

    # Test invalid literals - should raise error
    with pytest.raises(SystemExit):
        parse(LiteralTypes, ["--mode", "invalid", "--level", "2"])

    with pytest.raises(SystemExit):
        parse(LiteralTypes, ["--mode", "auto", "--level", "5"])


def test_positional_literal():
    class PosLiteral(t.TypedDict):
        mode: t.Annotated[t.Literal["auto", "manual"], "1"]

    args = ["auto"]
    result = parse(PosLiteral, args)
    assert result["mode"] == "auto"

    with pytest.raises(SystemExit):
        parse(PosLiteral, ["invalid"])


def test_positional_count_zero_or_more():
    class CountTest(t.TypedDict):
        files: t.Annotated[list[str], "*"]

    # Test with multiple values
    args = ["file1.txt", "file2.txt", "file3.txt"]
    result = parse(CountTest, args)
    assert result["files"] == ["file1.txt", "file2.txt", "file3.txt"]

    # Test with no values
    args = []
    result = parse(CountTest, args)
    assert result["files"] == []


def test_positional_count_one_or_more():
    class CountTest(TypedDict):
        files: t.Annotated[list[str], "+"]

    # Test with multiple values
    args = ["file1.txt", "file2.txt"]
    result = parse(CountTest, args)
    assert result["files"] == ["file1.txt", "file2.txt"]

    # Test with no values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, [])


def test_positional_count_greater_than():
    class CountTest(t.TypedDict):
        files: t.Annotated[list[str], "+"]

    # Test with values
    args = ["file1.txt", "file2.txt"]
    result = parse(CountTest, args)
    assert result["files"] == ["file1.txt", "file2.txt"]

    # Test with no values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, [])


def test_positional_count_at_most_one():
    class CountTest(t.TypedDict):
        file: t.Annotated[str, "?"]

    # Test with one value
    args = ["file1.txt"]
    result = parse(CountTest, args)
    assert result["file"] == "file1.txt"

    # Test with no values
    args = []
    result = parse(CountTest, args)
    assert result["file"] is None

    # Test with multiple values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, ["file1.txt", "file2.txt"])


def test_positional_count_less_than():
    class CountTest(t.TypedDict):
        file: t.Annotated[str, "?"]

    # Test with one value
    args = ["file1.txt"]
    result = parse(CountTest, args)
    assert result["file"] == "file1.txt"

    # Test with no values
    args = []
    result = parse(CountTest, args)
    assert result["file"] is None

    # Test with multiple values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, ["file1.txt", "file2.txt"])


def test_positional_count_exactly():
    class CountTest(t.TypedDict):
        files: t.Annotated[list[str], "3"]

    # Test with exact number of values
    args = ["file1.txt", "file2.txt", "file3.txt"]
    result = parse(CountTest, args)
    assert result["files"] == ["file1.txt", "file2.txt", "file3.txt"]

    # Test with too few values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, ["file1.txt", "file2.txt"])

    # Test with too many values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, ["file1.txt", "file2.txt", "file3.txt", "file4.txt"])


def test_positional_count_exactly_one():
    class CountTest(t.TypedDict):
        command: t.Annotated[str, 1]

    # Test with single value
    args = ["build"]
    result = parse(CountTest, args)
    assert result["command"] == "build"  # Should be a string, not a list
    assert not isinstance(result["command"], list)

    # Test with multiple values - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, ["build", "extra"])


def test_multiple_positional_args_with_fixed_counts():
    class FixedCounts(t.TypedDict):
        command: t.Annotated[str, "1"]
        subcommand: t.Annotated[str, 1]
        target: t.Annotated[str, "1"]
        option: t.Annotated[str, "?"]

    # Test with all arguments
    args = ["build", "web", "app.py", "debug"]
    result = parse(FixedCounts, args)
    assert result["command"] == "build"
    assert result["subcommand"] == "web"
    assert result["target"] == "app.py"
    assert result["option"] == "debug"

    # Test with minimum required
    args = ["build", "web", "app.py"]
    result = parse(FixedCounts, args)
    assert result["command"] == "build"
    assert result["subcommand"] == "web"
    assert result["target"] == "app.py"
    assert result["option"] is None


def test_positional_with_count_constraints():
    class PositionalWithConstraints(t.TypedDict):
        command: t.Annotated[str, "1"]
        files: t.Annotated[list[str], "2"]

    # Test with exact file count
    args = ["compress", "input.txt", "output.gz"]
    result = parse(PositionalWithConstraints, args)
    assert result["command"] == "compress"
    assert result["files"] == ["input.txt", "output.gz"]

    # Test with wrong file count - should fail
    with pytest.raises(SystemExit):
        print(parse(PositionalWithConstraints, ["compress", "input.txt"]))


def test_exact_numeric_count():
    class CountTest(t.TypedDict):
        files: t.Annotated[list[str], "2"]

    # Test with exact number
    args = ["file1.txt", "file2.txt"]
    result = parse(CountTest, args)
    assert result["files"] == ["file1.txt", "file2.txt"]

    # Test with wrong number - should fail
    with pytest.raises(SystemExit):
        parse(CountTest, ["file1.txt"])


def test_larger_exact_count():
    class CountTest(t.TypedDict):
        files: t.Annotated[list[str], "5"]

    # Test with exact number
    args = ["file1.txt", "file2.txt", "file3.txt", "file4.txt", "file5.txt"]
    result = parse(CountTest, args)
    assert result["files"] == [
        "file1.txt",
        "file2.txt",
        "file3.txt",
        "file4.txt",
        "file5.txt",
    ]


def test_typeddict_to_cli_args_basic():
    class TestDict(t.TypedDict):
        name: str
        count: t.Optional[int]
        verbose: bool

    # Create a dictionary that would be an instance of TestDict
    data: TestDict = {"name": "test", "count": 42, "verbose": True}

    args = stringify(data, TestDict)
    # The order might vary, so we'll check for inclusion
    assert "--name" in args
    assert "test" in args
    assert "--count" in args
    assert "42" in args
    assert "--verbose" in args


def test_typeddict_to_cli_args_with_positionals():
    class TestDict(t.TypedDict):
        pos1: t.Annotated[str, "1"]
        pos_multi: t.Annotated[list[str], "+"]
        flag: bool
        option: str | None

    # Create a dictionary that would be an instance of TestDict
    data: TestDict = {
        "pos1": "value1",
        "pos_multi": ["a", "b", "c"],
        "flag": True,
        "option": "opt_val",
    }

    args = stringify(data, TestDict)

    # The positionals should come first in order
    assert args[0] == "value1"
    assert args[1:4] == ["a", "b", "c"]

    # Check for inclusion of optional arguments
    assert "--flag" in args
    assert "--option" in args
    assert "opt_val" in args


def test_typeddict_to_cli_args_with_literal():
    class TestDict(t.TypedDict):
        mode: t.Literal["fast", "slow"]
        level: t.Annotated[t.Literal[1, 2, 3], "1"]

    data = {"mode": "fast", "level": 2}

    args = stringify(data, TestDict)

    assert args[0] == "2"  # Positional comes first
    assert "--mode" in args
    assert "fast" in args


def test_list_repeat():
    class MyConfigDict(t.TypedDict):
        repeat_me: t.Annotated[
            list[str], None
        ]  # idk why'd you want to do this but at least it shouldn't crash

    a = parse(MyConfigDict, ["--repeat-me", "once"])
    b = parse(MyConfigDict, ["--repeat-me", "once", "--repeat-me", "twice"])
    c = parse(MyConfigDict, [])

    assert a["repeat_me"] == ["once"]
    assert b["repeat_me"] == ["once", "twice"]

    assert stringify(a) == ["--repeat-me", "once"]
    assert stringify(a, MyConfigDict) == ["--repeat-me", "once"]
    assert stringify(b, MyConfigDict) == ["--repeat-me", "once", "--repeat-me", "twice"]
    assert stringify(c, MyConfigDict) == []


def test_enum():
    class SomeEnum(enum.Enum):
        first = "first"
        second = "second-option"

    class EnumDict(t.TypedDict):
        option: t.Annotated[SomeEnum, 1]

    enum_dict = parse(EnumDict, ["second-option"])

    assert isinstance(enum_dict["option"], SomeEnum)
    assert enum_dict["option"] == SomeEnum.second
