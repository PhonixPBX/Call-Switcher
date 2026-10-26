import sys

if sys.platform == "darwin":
    from .main import main
else:
    from .linux.app import main

main()
