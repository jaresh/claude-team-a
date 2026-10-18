"""Brief item 1: force Haiku by setting, not by a prompt rule.

Every subagent and teammate runs on Haiku whatever the lead passes (CLAUDE_CODE_SUBAGENT_MODEL
with _FORCE, Claude Code 2.1.257+), and the 100K auto-compact window moves from the session's
modelSettings into the team-dev agent's own frontmatter (2.1.296+), so it applies to teammates
only."""
from common import SETTINGS, rep


def apply(src):
    src = rep(src, SETTINGS, '''SETTINGS_ADD = {"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
                        "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
                        "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"}}''')
    return rep(src, "model: haiku\neffort: medium\n---\n",
               "model: haiku\neffort: medium\nautoCompactWindow: 100000\n---\n")
