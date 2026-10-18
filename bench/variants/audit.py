"""Brief item 5: a fresh-context Haiku teammate checks the merged work.

After the last wave passes the check, one teammate, `audit` (never "review": Claude Code refuses
report-like Markdown from subagents, and it writes .txt anyway), reads the request, the Contract,
the Conventions and the code with no history, and lists findings without changing files. The
lead fixes small ones and gives the rest to one successor, `audit-fix`."""
from common import rep


def apply(src):
    return rep(src, '''- Then the next wave; after the last one, step 4 or 5.''', '''- Then the next wave. After the last one passes the check, one more teammate, `audit`,
  checks the work with fresh eyes. Its prompt: read `.claude/team/spec.md` (or the plan's
  Goal), the Contract, the Conventions and the code the team wrote; write up to 10 findings to
  `.claude/team/handoff/audit.txt`, each with file and function: a requirement not met or not
  tested, a rule or helper implemented twice, a convention broken; change no file. Its done
  check: that file exists. Then fix what matters: small things yourself, the rest with one
  successor, `audit-fix`, whose prompt names the findings and whose done check is the full
  check. Then step 4 or 5.''')
