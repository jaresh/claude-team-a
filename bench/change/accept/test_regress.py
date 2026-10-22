"""The warehouse benchmark's hidden tests, as a regression suite: existing behaviour must not change."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "warehouse", "accept"))
from test_wms import *  # noqa: F401,F403,E402
