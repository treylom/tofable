# Q&A Transcript — "Practical Rate Limiting Patterns for Public APIs"

DevCon 2026, Track B

MODERATOR: We have about eight minutes for questions. Let's start on the
left.

**Q1 (Attendee, Row 3):** You mentioned the token-bucket approach — how do
you handle burst traffic from a single client without starving everyone
else?

**SPEAKER:** Good question. We cap the bucket size per client key, so a
burst from one client can spend down to zero fast, but it can't borrow
from other clients' buckets — each key has its own independent bucket.
That's what keeps one noisy client from starving the rest.

**Q2 (Attendee, Row 1):** What happens if two instances of your rate
limiter are running behind a load balancer — do they share state?

**SPEAKER:** They do — we back the bucket counters with a shared Redis
instance, so any instance behind the load balancer sees the same counts.
Without that you'd effectively get N times the limit, one bucket per
instance.

**Q3 (Attendee, Row 5):** How does this compare to just using your cloud
provider's built-in API gateway throttling?

**SPEAKER:** The built-in throttling is coarser — usually just requests
per second per route. Ours lets us set different limits per API key and
per endpoint, which we needed once we started offering paid tiers with
different quotas.

**Q4 (Attendee, Row 2):** Is there a way to test the rate limiter locally
without hitting the real Redis-backed service — like some kind of
in-memory mode for unit tests?

**MODERATOR:** We're right at time — let's take that one offline, happy
to follow up after the session. Let's do one more quick one.

**Q5 (Attendee, Row 4):** Any plans to open-source the library?

**SPEAKER:** It's on our radar — nothing committed yet, but if there's
enough interest we'd like to clean it up and put it out publicly next
year.

MODERATOR: That's time — thanks everyone, the speaker will be around
after for follow-ups.
