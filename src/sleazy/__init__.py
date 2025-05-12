# sleazy - cli+easy
import argparse
import types
import typing as t

from .__about__ import __version__


class TypedDict(t.TypedDict): ...


D = t.TypeVar("D", bound=TypedDict)


# internal
def parse_count_spec(spec: str) -> str | int:
    """Parse a count specification into argparse nargs format.

    Only the following are allowed (same as argparse):
      - exactly 1 (default)
      - exact integer N
      - '+' for one or more
      - '*' for zero or more
      - '?' for zero or one

    """
    if spec in (None, ""):
        return 1

    # Exact numeric values
    if isinstance(spec, int) or spec.isdigit():
        return int(spec)

    # Direct argparse-style symbols
    if spec in ("+", "*", "?"):
        return spec

    # unsupported spec
    raise SyntaxError(f"Unexpected '{spec}'. Please choose from [+, *, ?, n]")


def strip_optional(tp: t.Type) -> t.Type:
    """Remove Optional[...] or | None from a type."""

    # Get the origin (e.g., Union) for both legacy and new union types (PEP 604)
    origin = t.get_origin(tp)

    # Handle Union types (both legacy Optional[...] and new | None)
    if origin is t.Union or isinstance(tp, types.UnionType):
        args = t.get_args(tp)  # __args__ holds the union members
        # Remove `NoneType` (type(None)) from the union args
        args = tuple(a for a in args if a is not types.NoneType)
        if len(args) == 1:
            return args[0]  # If only one type remains, return it directly
        return t.Union[args]  # Otherwise, return the filtered union

    return tp  # Return the type as-is if it's not a Union or Optional


def parse(typeddict_cls: t.Type[D], args: t.Optional[list[str]] = None) -> D:
    parser = argparse.ArgumentParser()
    type_hints = t.get_type_hints(typeddict_cls, include_extras=True)
    type_hints = {k: strip_optional(v) for k, v in type_hints.items()}

    # First, add all positional arguments
    positional_fields = {}
    for field, hint in type_hints.items():
        # Check if it's a positional argument
        is_positional = False
        arg_type = hint
        nargs_value = 1  # Default is required single argument
        is_list_type = False

        if t.get_origin(hint) is t.Annotated:
            arg_type, *annotations = t.get_args(hint)

            # Check if the type is a list
            is_list_type = t.get_origin(arg_type) is list

            for anno in annotations:
                # Support for positional counts - now directly parse the count spec
                if isinstance(anno, str | int):
                    is_positional = True
                    nargs_value = parse_count_spec(anno)

        if is_positional:
            positional_fields[field] = (arg_type, nargs_value, is_list_type)

    # Add positional arguments in their own group
    for field, (arg_type, nargs_value, is_list_type) in positional_fields.items():
        # Handle Literal types
        if t.get_origin(arg_type) is t.Literal:
            # Use first value's type as the parser type
            if literal_values := t.get_args(arg_type):
                first_value = literal_values[0]
                parser_type = type(first_value)

                if nargs_value == 1:
                    # convert to default (None) to prevent getting a list of 1 element
                    nargs_value = None

                parser.add_argument(
                    field,
                    type=parser_type,
                    nargs=nargs_value,
                    default=None,
                    choices=literal_values,
                )
            else:  # pragma: no cover
                raise TypeError("Plain typing.Literal is not valid as type argument")
        elif is_list_type:
            # For list types, get the element type
            elem_type = t.get_args(arg_type)[0] if t.get_args(arg_type) else str
            parser.add_argument(field, type=elem_type, nargs=nargs_value, default=None)
        else:
            # For non-list types, ensure single values are not put in a list
            # when nargs is a numeric value
            if isinstance(nargs_value, int) and nargs_value == 1 and not is_list_type:
                # For exactly 1 argument that's not a list type, don't use nargs
                parser.add_argument(field, type=arg_type, default=None)
            else:
                parser.add_argument(
                    field, type=arg_type, nargs=nargs_value, default=None
                )

    # Then add all optional arguments
    for field, hint in type_hints.items():
        # Skip positional arguments as they've already been added
        if field in positional_fields:
            continue

        arg_type = hint

        if t.get_origin(hint) is t.Annotated:
            arg_type, *_ = t.get_args(hint)

        # Check if the type is a list
        is_list_type = t.get_origin(arg_type) is list

        # Handle Literal types in optional arguments
        if t.get_origin(arg_type) is t.Literal:
            if literal_values := t.get_args(arg_type):
                first_value = literal_values[0]
                parser_type = type(first_value)
                parser.add_argument(
                    f"--{field.replace('_', '-')}",
                    type=parser_type,
                    choices=literal_values,
                )
            else:  # pragma: no cover
                raise TypeError("Plain typing.Literal is not valid as type argument")
        elif arg_type is bool:
            parser.add_argument(f"--{field.replace('_', '-')}", action="store_true")
        elif is_list_type:
            # For list types, use 'append' action to collect multiple instances
            elem_type = t.get_args(arg_type)[0] if t.get_args(arg_type) else str
            parser.add_argument(
                f"--{field.replace('_', '-')}",
                type=elem_type,
                action="append",
            )
        else:
            parser.add_argument(f"--{field.replace('_', '-')}", type=arg_type)

    return vars(parser.parse_args(args))


def stringify(data: D, typeddict_cls: t.Type[D] = None) -> list[str]:
    """
    Convert a TypedDict instance to a list of command-line arguments.
    Positional arguments come first, followed by optional arguments.
    """
    args = []
    typeddict_cls = typeddict_cls or data.__class__
    type_hints = t.get_type_hints(typeddict_cls, include_extras=True)

    # Process positional arguments first
    positional_fields = []
    for field, hint in type_hints.items():
        is_positional = False
        nargs_value = "?"  # Default

        if t.get_origin(hint) is t.Annotated:
            _, *annotations = t.get_args(hint)
            for anno in annotations:
                # Support for positional counts with dynamic parsing
                if isinstance(anno, str | int):
                    is_positional = True
                    nargs_value = parse_count_spec(anno)

        if is_positional:
            positional_fields.append((field, nargs_value))

    # Add positional arguments
    for field, nargs_value in positional_fields:
        if field in data and data[field] is not None:
            if isinstance(data[field], list) and nargs_value in ["*", "+"]:
                for item in data[field]:
                    args.append(str(item))
            else:
                args.append(str(data[field]))

    # Add optional arguments
    for field, value in data.items():
        # Skip positional arguments as they've already been added
        if field in [f for f, _ in positional_fields]:
            continue

        # Skip None values
        if value is None:
            continue

        if isinstance(value, bool):
            if value:  # Only add flag if True
                args.append(f"--{field.replace('_', '-')}")
        elif isinstance(value, list):
            # For list types, add each item as a separate flag occurrence
            for item in value:
                args.append(f"--{field.replace('_', '-')}")
                args.append(str(item))
        else:
            args.append(f"--{field.replace('_', '-')}")
            args.append(str(value))

    return args


__all__ = [
    "__version__",
    "parse",
    "stringify",
    "TypedDict",
]
