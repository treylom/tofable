# Task: fix a bug in the "due soon" filter

Bug report: In our todo app, the "due soon" view (tasks due within the next
N days) is supposed to include a task due exactly N days from today — but
it's being silently excluded. A user almost missed a task that was due in
exactly 5 days because it never showed up in the list.

The relevant code is `due_soon.py` in this directory.

Requirements:

1. **Reproduce** the bug first. Do not patch blind — reproduce it before
   changing any code.
2. Identify the root cause and fix it.
3. Verify your fix (to whatever level you think is appropriate — you decide
   the method and scope).
4. At the end, report back: what the root cause was, what you changed, and
   how you verified it.

Constraints: do not access files outside this directory. No network access.
