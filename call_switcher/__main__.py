import sys

if sys.platform == "darwin":
    from .main import main
else:
    from .qt.app import main

main()
