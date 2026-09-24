from mypy.main import main
import sys

# Mypy usually doesn't have an easy "get the types" internal API that is stable,
# let's just observe what Jedi gave us.
