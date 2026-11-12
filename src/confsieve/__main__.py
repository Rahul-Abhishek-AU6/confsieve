"""Direct package entrypoint for python -m confsieve."""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
