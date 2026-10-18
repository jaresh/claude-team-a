"""Brief item 6: a Haiku 5.5 advisor for the Haiku teammates.

advisorModel in the kit's settings. A Sonnet 5.5 lead accepts only Fable, Opus 5+ or Sonnet 5.5
as advisor, so the lead gets none; Haiku 5.5 teammates accept Haiku 5.5 (Claude Code 2.1.293+).
Advisor calls are billed apart (usage.iterations), which `team_kit.py cost` counts."""
from common import SETTINGS, rep


def apply(src):
    return rep(src, SETTINGS, SETTINGS[:-1] + ',\n                "advisorModel": "claude-haiku-5-5"}')
