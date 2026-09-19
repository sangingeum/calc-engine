"""Pure domain modules: no I/O, no sys.stdout/stderr/sys.exit.

Every module raises CalcError subclasses; rendering and exiting are cli.py's
job alone (DESIGN.md boundary rule).
"""
