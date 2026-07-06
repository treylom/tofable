# Talk Summary — "Practical Rate Limiting Patterns for Public APIs"

Overview of how the team built a per-client, per-endpoint rate limiter for
their public API. Covered:

- Why per-route, global throttling wasn't enough once paid tiers launched.
- Token-bucket algorithm basics and why it was chosen over fixed windows.
- Sharing bucket state across instances via Redis so limits hold behind a
  load balancer.
- Config format for setting different limits per API key / plan tier.
- A brief mention that the team's own dev environment uses a local Redis
  container via docker-compose for day-to-day development, so engineers
  aren't hitting shared staging infrastructure while iterating.
- Roadmap teaser: considering a managed dashboard for customers to see
  their own usage against their limit.
