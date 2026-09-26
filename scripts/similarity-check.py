#!/usr/bin/env python3
"""similarity-check.py <ours> <theirs> [--max N]

Reports lines of <ours> that also appear verbatim in <theirs>, ignoring
whitespace, blank lines, comments, lone brackets and common GNOME Shell API
boilerplate. Used to check that a clean-room rewrite shares no
non-trivial code with the project it replaced. Keep <theirs> outside the
repository; only the result belongs in a ticket or PR.

Exits 1 if more than N (default 0) non-trivial lines are shared.
"""
import re
import sys

# Lines any GNOME Shell extension written against the same APIs will have.
BOILERPLATE = [
    r"^import\b",
    r"^(export )?default class\b",
    r"^(enable|disable)\(\) \{$",
    r"^(super\._init|super)\(",
    r"^y_align: Clutter\.ActorAlign\.\w+,?$",
    r"^x_align: Clutter\.ActorAlign\.\w+,?$",
    r"^return Clutter\.EVENT_(STOP|PROPAGATE);$",
    r"^(return|break|continue);$",
    r"^\}?\s*(else|catch \(e\))\s*\{?$",
    r"^try \{$",
    r"^\}\);?$",
    r"^\]\);?$",
    r"^\],?$",
    r"^[{}\[\]();,]+$",
    r"^return (null|true|false|result);$",
    r"^GObject\.registerClass\(",
    # Single API calls with no room for expression.
    r"^this\.visible = (true|false);$",
    r"^return GLib\.SOURCE_(CONTINUE|REMOVE);$",
    r"^action: \(\) => \{$",
    r"^(this|dialog)\.(open|close)\(\);$",
    r"^\w+\.(un)?maximize\(Meta\.MaximizeFlags\.BOTH\);$",
    r"^\w+\.destroy\(\);$",
]
BOILERPLATE_RE = [re.compile(p) for p in BOILERPLATE]


def normalized_lines(path):
    lines = []
    in_block_comment = False
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if in_block_comment:
                if "*/" in line:
                    in_block_comment = False
                continue
            if line.startswith("/*"):
                in_block_comment = "*/" not in line
                continue
            if not line or line.startswith("//") or line.startswith("*"):
                continue
            line = re.sub(r"\s+", " ", line)
            if any(p.search(line) for p in BOILERPLATE_RE):
                continue
            lines.append(line)
    return lines


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    limit = 0
    if "--max" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--max") + 1])
        args = [a for a in args if a != str(limit)]
    if len(args) != 2:
        sys.exit(__doc__)
    ours, theirs = normalized_lines(args[0]), set(normalized_lines(args[1]))
    shared = [l for l in dict.fromkeys(ours) if l in theirs]
    total = len(set(ours))
    print(f"{len(shared)} of {total} distinct non-trivial lines shared "
          f"({100 * len(shared) / max(total, 1):.1f}%)")
    for line in shared:
        print(f"  {line}")
    sys.exit(1 if len(shared) > limit else 0)


if __name__ == "__main__":
    main()
