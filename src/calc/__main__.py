"""Allow `python -m calc`."""

import sys

from calc.cli import main

if __name__ == "__main__":
    sys.exit(main())
