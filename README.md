# sleazy

A tiny utility to build CLI tools from Python `TypedDict` schemas.  
Define your parameters with type hints (and `Annotated` for positionals), then call `parse()` to get a typed dict and
`stringify()` to turn it back into args.

## Installation

```shell script
uv pip install sleazy
```

## Example CLI

```python
from typing import Annotated, Literal, TypedDict
from sleazy import parse, stringify


class AppConfig(TypedDict):
    # 1) Required positional (exactly one string)
    input_file: Annotated[str, 1]

    # 2) Optional positional (zero or more strings)
    tags: Annotated[str, "*"]

    # 3) Optional keyword args
    output: str  # string
    verbose: bool  # flag
    retries: int  # integer
    mode: Literal["auto", "manual"]  # choice via Literal or enum


if __name__ == "__main__":
    # parse() returns a dict matching AppConfig
    args = parse(AppConfig) # python example.py data.txt tag1 tag2 --output out.txt --verbose --retries 5 --mode auto
    print(args)
    # {
    #   'input_file': 'data.txt',
    #   'tags': ['tag1', 'tag2'],
    #   'output': 'out.txt',
    #   'verbose': True,
    #   'retries': 5,
    #   'mode': 'auto'
    # }

    # stringify back to CLI args, using AppConfig to keep positionals first
    print(stringify(args, AppConfig))
    # [
    #   'data.txt',
    #   'tag1', 'tag2',
    #   '--output', 'out.txt',
    #   '--verbose',
    #   '--retries', '5',
    #   '--mode', 'auto'
    # ]

    # Without the TypedDict, stringify treats everything as flags
    print(stringify(args))
    # [
    #   '--input-file', 'data.txt',
    #   '--tags', 'tag1', '--tags', 'tag2',
    #   '--output', 'out.txt',
    #   '--verbose',
    #   '--retries', '5',
    #   '--mode', 'auto'
    # ]
```

**Notes**

- Positionals are marked via `Annotated[type, count]` (`1`, `?`, `*`, `+`, or exact integer).
- All other fields become `--field-name` flags by default.
- It's useful to pass your `TypedDict` type to `stringify()` so it knows which fields are positional (and their order). Without it,
  everything is emitted as a keyword flag.
