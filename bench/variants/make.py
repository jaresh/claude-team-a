#!/usr/bin/env python3
"""Make a one-change variant of team_kit.py, for a single-change experiment.

    bench/variants/make.py NAME OUT

bench/variants/NAME.py defines apply(src) -> src: the kit's source with that one change. The
variant's KIT_VERSION becomes the base version plus "+NAME", so results name what was tested.
bench/run.sh calls this when VARIANT=NAME is set."""
import importlib.util
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
name, out = sys.argv[1:3]
spec = importlib.util.spec_from_file_location(name, os.path.join(here, name + ".py"))
variant = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant)
src = open(os.path.join(here, "..", "..", "team_kit.py")).read()
new = variant.apply(src)
new = re.sub(r'^KIT_VERSION = "([^"]+)"', lambda m: f'KIT_VERSION = "{m.group(1)}+{name}"', new,
             count=1, flags=re.M)
with open(out, "w") as f:
    f.write(new)
