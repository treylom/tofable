# Driftwood API Reference — v4.0

*Published November 2, 2024 · Driftwood SDK / API v4.0 · Tidepool Systems*

Base URL: `https://api.tidepoolsystems.com`

## Authentication

### POST /v1/auth/token

Exchange an API key for a short-lived bearer token.

| Field | Type | Required | Description |
|---|---|---|---|
| `api_key` | string | yes | Your account API key. |

Returns `{ "token": string, "expires_in": integer }`.

## Jobs

### POST /v1/jobs

Submit a new asynchronous job.

| Field | Type | Required | Description |
|---|---|---|---|
| `payload` | object | yes | Task-specific input. See "Task types" in the getting-started guide. |
| `callback_url` | string | no | If set, Tidepool Systems POSTs the result here on completion instead of requiring a poll. |
| `priority` | string | no | One of `low`, `normal`, `high`. Defaults to `normal`. |

Returns a job object: `{ "id": string, "state": "queued", "created_at": string }`.

### GET /v1/jobs/{id}

Fetch the current state of a job.

Returns: `{ "id": string, "state": "queued" | "running" | "completed" | "failed", "result": object | null, "error": object | null }`.

### GET /v1/jobs

List jobs for the current account. Supports `status` and `created_after`
query filters.

### DELETE /v1/jobs/{id}/cancel

Cancel a queued or running job.

## Completions

### POST /v1/complete

Generate a single completion for a prompt. This call is synchronous — the
response is returned once generation finishes; there is no separate
polling step for this endpoint.

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | yes | The input prompt. |
| `max_tokens` | integer | no | Upper bound on generated length. Defaults to 512. |
| `temperature` | float | no | Sampling temperature, 0.0–2.0. Defaults to 0.7. |

Returns: `{ "id": string, "output": string, "usage": { "prompt_tokens": integer, "completion_tokens": integer } }`.

## Rate limits

| Endpoint | Limit |
|---|---|
| `POST /v1/jobs` | 120 / minute |
| `POST /v1/complete` | 60 / minute |
| `GET /v1/jobs/{id}` | 600 / minute |

## Changelog

- **v4.0** (this document): added `priority` field to job creation; added
  `/v1/complete` for synchronous single-shot generation, as a
  lighter-weight alternative to the job queue for short prompts.
- **v3.2**: initial public release of the job queue, polling model, and
  webhook callbacks.
