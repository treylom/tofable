# Rule: delegating work (compact)

Trigger: handing a task to a sub-agent, worker, or bot — or accepting its result.

Dispatch:
1. **Complete HOW in the first message**: exact method, tools, forbidden paths, output format, report destination. Self-test: could the worker execute correctly from this one message alone?
2. **Check the worker's capacity first** (context/rate/resource). Near-limit worker = have it checkpoint and wind down, or pick another.
3. **Ack ≠ execution.** Observe the worker actually enter the task (session/logs) before ending your turn.

Accepting results:
4. **Trust artifacts, not "done".** Run ALL of:
   - exist: `ls -la` every claimed path
   - fresh: mtimes fall INSIDE the claimed work window — backdated or months-old files under a fresh claim = reject
   - distinct: `shasum` the outputs — identical hashes under different names = one result copied N times
   - counted: batch outputs match the claimed count exactly (structured returns truncate silently).
5. **Verify against sources, not narration.** Spot-check citations against the primary sources; many citations from very few tool calls = confabulation smell.
6. **Disambiguate scope verbs before acting**: "register" ≠ "run now"; "fix the format" ≠ "replace the content"; "all N items" ≠ any subset.
7. **Decompose multi-part instructions into a checklist first**, execute against it, and diff the result against the ORIGINAL wording — not your memory of it.
8. **Scope changes propagate the same turn**: patch the spec document and re-dispatch the delta immediately.
