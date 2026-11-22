"""Run practice examples and emit their move lists as JSON."""

import argparse
import json
from pathlib import Path

from .examples import EXAMPLES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["all", *EXAMPLES])
    parser.add_argument("--input", type=Path, help="JSON layout overrides for one sorting task")
    args = parser.parse_args()
    if args.input and args.task in ("all", "common1"):
        parser.error("--input needs a single sorting task")
    if args.input:
        try:
            layouts = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(layouts, dict):
                raise ValueError("The layout file must contain a JSON object")
            result = EXAMPLES[args.task](layouts)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
            parser.exit(1, f"{error}\n")
        print(json.dumps({args.task: result}, ensure_ascii=False, indent=2))
        return
    selected = EXAMPLES if args.task == "all" else {args.task: EXAMPLES[args.task]}
    results = {name: plan() for name, plan in selected.items()}
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
