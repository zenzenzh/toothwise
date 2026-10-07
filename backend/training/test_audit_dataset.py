"""
Self-check for audit_dataset's yaml reading. Run it directly:

    python test_audit_dataset.py

Exists because the yaml reader was rewritten twice to cope with Roboflow
export styles, and both earlier versions failed the same way: on a real
export they returned zero class names, which made the report print an empty
table and then conclude that every class was fine. A silent all-clear is
worse than a crash, so the shapes that broke it are pinned here.
"""
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "audit_dataset.py"
_ns = {"__name__": "audit_dataset_under_test", "__file__": str(SCRIPT)}
exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), _ns)

parse_yaml = _ns["parse_yaml"]
_manual_yaml = _ns["_manual_yaml"]
_normalise_names = _ns["_normalise_names"]
looks_like_dataset_yaml = _ns["looks_like_dataset_yaml"]

NAMES = {0: "healthy_tooth", 1: "cavity", 2: "gum_inflammation",
         3: "plaque", 4: "tartar"}
LIST = ("  - healthy_tooth\n  - cavity\n  - gum_inflammation\n"
        "  - plaque\n  - tartar\n")

# shape -> yaml body. Every one of these has appeared in a real export.
SHAPES = {
    "list":        "path: .\ntrain: t/images\nnames:\n" + LIST,
    "dict":        "path: .\ntrain: t/images\nnames:\n  0: healthy_tooth\n"
                   "  1: cavity\n  2: gum_inflammation\n  3: plaque\n  4: tartar\n",
    "inline":      "path: .\ntrain: t/images\nnc: 5\nnames: [healthy_tooth, "
                   "cavity, gum_inflammation, plaque, tartar]\n",
    "flowmap":     "path: .\ntrain: t/images\nnames: {0: healthy_tooth, "
                   "1: cavity, 2: gum_inflammation, 3: plaque, 4: tartar}\n",
    "quotedkey":   'path: .\ntrain: t/images\n"names":\n' + LIST,
    "quotednum":   "path: .\ntrain: t/images\nnames:\n  '0': healthy_tooth\n"
                   "  '1': cavity\n  '2': gum_inflammation\n  '3': plaque\n"
                   "  '4': tartar\n",
    "bom":         "\ufeffpath: .\ntrain: t/images\nnames:\n" + LIST,
    "tabs":        "path: .\ntrain: t/images\nnames:\n"
                   + LIST.replace("  - ", "\t- "),
    "crlf":        "path: .\r\ntrain: t/images\r\nnames:\r\n"
                   + LIST.replace("\n", "\r\n"),
    "comments":    "path: .  # root\ntrain: t/images\nnc: 5  # how many\n"
                   "names:\n" + LIST,
}

# The hand-rolled fallback is deliberately not a YAML parser. Pin what it
# cannot do so nobody assumes the dependency-free path is equivalent.
MANUAL_CANNOT = {"flowmap"}


def main() -> int:
    import tempfile
    failures = []

    with tempfile.TemporaryDirectory() as d:
        for shape, body in SHAPES.items():
            p = Path(d) / f"{shape}.yaml"
            p.write_text(body, encoding="utf-8")

            got = {int(k): v for k, v in parse_yaml(p)["names"].items()}
            if got != NAMES:
                failures.append(f"parse_yaml[{shape}] = {got}")
            if not looks_like_dataset_yaml(p):
                failures.append(f"looks_like_dataset_yaml[{shape}] = False")

            manual = _normalise_names(_manual_yaml(body)["names"])
            if shape in MANUAL_CANNOT:
                if manual == NAMES:
                    failures.append(
                        f"manual reader unexpectedly handled {shape}; "
                        f"either the fallback improved or the pin is stale")
            elif manual != NAMES:
                failures.append(f"_manual_yaml[{shape}] = {manual}")

        # A yaml with no names block must not be mistaken for a dataset, and
        # must report zero classes rather than inventing some.
        empty = Path(d) / "empty.yaml"
        empty.write_text("path: .\ntrain: t/images\nnc: 5\n", encoding="utf-8")
        if parse_yaml(empty)["names"]:
            failures.append("parse_yaml[no names block] invented classes")
        if looks_like_dataset_yaml(empty):
            failures.append("looks_like_dataset_yaml accepted a nameless yaml")

    for f in failures:
        print(f"FAIL {f}")
    print(f"{len(SHAPES)} yaml shapes x {{parse_yaml, manual fallback, discovery}}"
          f" -> {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
