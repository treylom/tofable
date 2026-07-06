# Rule: continuation before stopping (compact)

Trigger: about to stop, defer ("I'll finish tomorrow"), scale down, or wrap up while goals remain open.

Pass all three before any early stop:
1. **Real technical blocker?** Check the existing safety nets first (auto-compaction, backups, retries, rollback). Low remaining context is NOT a stop reason when the runtime compacts automatically.
2. **Whose call is it?** Finishing early, deferring, and closing the session are the USER's decisions. Default = keep going; the user interrupts when they want to stop.
3. **Have you said so?** If blocked, report the blocker explicitly. Never go quiet.

Amplifiers:
4. **An active feedback loop is a keep-going signal.** While the user is iterating with you, the default is another iteration NOW; only the user closes the loop.
5. **Partial output = report trigger, not silence.** Report the partial result and the remaining gap the moment either exists.

Unresponsive process? Classify before waiting:
6. **waiting** (known anchor + expected duration) → leave it alone · **hung** (no output past the time cap) → escalate, don't extend · **dead** (exited / needs interactive input) → restart or hand to a human, a mention won't reach it. Treating hung/dead as "waiting" is how multi-hour stalls happen.
