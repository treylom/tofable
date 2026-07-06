# Forum: Any plans for streaming support?

**community.tidepoolsystems.com → Driftwood SDK → General**

---

**devuser447** · posted 2023-08-14

We're looking at Driftwood for a chat-style product and the polling loop
works, but the UX would be a lot better if we could show partial output as
it's generated instead of a spinner until the whole job finishes. A couple
of other APIs we've evaluated support streaming partial output over SSE or
a chunked HTTP response.

Is streaming on the roadmap for Driftwood, or is the job/poll model going
to be the only option for the foreseeable future?

---

**tidepool_sam** (Tidepool Systems team) · replied 2023-08-16

Thanks for the detailed writeup! Streaming is not on the roadmap right now.
The job model is core to how we've built reliability into the platform —
every job is persisted server-side the moment it's accepted, so a dropped
connection never costs you a lost result. A streaming transport would trade
that durability guarantee away for lower first-byte latency, and we don't
think that's the right tradeoff for the workloads most Driftwood customers
run today.

If partial output is a hard requirement right now, one workaround some
customers use is splitting a large task into smaller jobs and polling each
one — you get incremental results, just chunkier than true token-by-token
streaming. Not as smooth as SSE, but it ships today.

We'll keep this thread open — if we see more demand we'll revisit.

---

**devuser447** · replied 2023-08-16

Makes sense, thanks for the honest answer. Chunked jobs should work for our
first version at least.

---

**otheruser_kim** · replied 2023-08-22

+1 on wanting this eventually, we hit the same UX wall. For now the
chunked-jobs workaround above is what we ended up doing too.

---

*4 replies · last activity 2023-08-22*
