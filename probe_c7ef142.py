"""Pre-fix failure-mode probe (dev scratch, not part of the suite).

Confirms that raw argparse on this interpreter (3.12.12) drops the
interleaved positional `uniform` — the issue 7 root cause — when the
_normalize_positionals rebuild is bypassed.
"""

import sys

sys.path.insert(0, "src")
from calc.cli import _build_parser  # noqa: E402

p = _build_parser()
argv = "compare-moments beta --alpha 2 --beta 2 uniform --low 0 --high 1 --moment mean".split()
args, unknown = p.parse_known_args(argv)
print("value=", args.value, "family2=", args.family2, "unknown=", unknown)
