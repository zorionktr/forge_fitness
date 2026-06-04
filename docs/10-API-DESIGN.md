# 10 — API Design

REST (JSON) for CRUD, **SSE** for agent streaming, **WebSocket** for chat/notifications/live food
results. Versioned under `/api/v1`. OpenAPI is the contract; clients are generated from it.

## 1. Conventions

- Base: `https://api.forge.app/api/v1`
- Auth: `Authorization: Bearer <access_jwt>`; refresh via rotating refresh token.
- Pagination: **cursor-based** — `?limit=&cursor=`; responses return `{ data, next_cursor }`.
- Idempotency: `Idempotency-Key` header on POSTs that create resources.
- Errors: RFC 9457 `application/problem+json`:
  ```json
  { "type":"about:blank","title":"Not Found","status":404,
    "detail":"food 1a2b not found","instance":"/api/v1/foods/1a2b" }
  ```
- Rate limits: `X-RateLimit-Limit/Remaining/Reset` headers; `429` on exceed.
- Timestamps ISO-8601 UTC; all IDs UUID.

## 2. Auth

| Method | Path | Body / notes |
|---|---|---|
| POST | `/auth/register` | `{email,password,username}` → tokens |
| POST | `/auth/login` | `{email,password}` → `{access,refresh}` |
| POST | `/auth/refresh` | `{refresh}` → rotated tokens |
| POST | `/auth/logout` | revoke refresh (jti blocklist) |
| POST | `/auth/oauth/google` | `{id_token}` verify → tokens |
| POST | `/auth/oauth/apple` | `{identity_token}` verify → tokens |
| GET  | `/auth/me` | current user + profile completeness |

## 3. Profile & goals

| Method | Path | Notes |
|---|---|---|
| GET | `/profile` | full profile + completeness |
| PATCH | `/profile` | partial update (also written by agent `update_profile`) |
| GET/POST | `/goals` | list / create |
| PATCH/DELETE | `/goals/{id}` | update / archive |

## 4. Agent (the core surface)

| Method | Path | Notes |
|---|---|---|
| GET | `/agent/conversations` | list |
| POST | `/agent/conversations` | start (optional persona) |
| GET | `/agent/conversations/{id}/messages` | history (paginated) |
| **POST** | `/agent/messages` | send message → **SSE stream** |
| WS | `/ws/agent` | bidirectional alternative |
| PATCH | `/agent/persona` | switch coach persona |
| GET | `/agent/memories` | list memories (transparency) |
| DELETE | `/agent/memories/{id}` | forget a memory |

**SSE event types** from `/agent/messages`:
```
event: message_start      data: {conversation_id, message_id}
event: content_delta      data: {text}
event: tool_use           data: {name, args}        # UI shows "checking workouts…"
event: tool_result        data: {name, summary}
event: content_delta      data: {text}
event: message_done       data: {usage, citations}
event: error              data: {type, detail}
```

Request:
```json
POST /api/v1/agent/messages
{ "conversation_id":"...", "content":"Did I hit my protein target today?",
  "attachments":[{"type":"image","s3_key":"..."}] }
```

## 5. Nutrition & food intelligence

| Method | Path | Notes |
|---|---|---|
| GET | `/foods?query=` | search canonical foods (trigram+semantic) |
| GET | `/foods/barcode/{code}` | barcode lookup (cached) |
| POST | `/foods` | create custom/recipe food |
| POST | `/food/analyze` | `{s3_key, input_type}` → async; returns `job_id` |
| GET | `/food/analyze/{job_id}` | poll result (or via WS) |
| GET/POST | `/nutrition/logs` | list (by date) / create log |
| GET | `/nutrition/summary?date=` | daily totals + targets + adherence |

Analyze result:
```json
{ "items":[{"food_id":"...","name":"Grilled chicken","grams":150,
   "calories":248,"protein_g":46,"carbs_g":0,"fat_g":5.4,"confidence":0.82}],
  "total":{"calories":..., "protein_g":...}, "warnings":["contains: none"] }
```

## 6. Workouts & progress

| Method | Path | Notes |
|---|---|---|
| GET | `/exercises?query=` | exercise library |
| GET/POST | `/workouts/sessions` | list / log session (+ sets) |
| GET | `/workouts/sessions/{id}` | detail |
| POST | `/workouts/plans` | create (or agent-generated) plan |
| GET | `/workouts/plans/active` | current plan |
| GET/POST | `/progress/measurements` | list / add |
| GET/POST | `/progress/photos` | list / upload (presigned) |
| GET | `/progress/insights` | latest AI insight summary |
| GET | `/progress/prs` | personal records |

## 7. Social

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/posts` | feed-agnostic list / create |
| GET/DELETE | `/posts/{id}` | detail / delete |
| GET/POST | `/posts/{id}/comments` | threaded comments |
| POST/DELETE | `/posts/{id}/like` | like / unlike |
| POST | `/posts/{id}/share` | share |
| GET | `/communities?query=` | discover |
| POST/DELETE | `/communities/{id}/membership` | join / leave |
| POST/DELETE | `/users/{id}/follow` | follow / unfollow |
| GET | `/users/{id}/profile` | public profile + transformation journey |

## 8. Feed & recommendations

| Method | Path | Notes |
|---|---|---|
| GET | `/feed?cursor=` | ranked personalized feed |
| GET | `/feed/community/{slug}?cursor=` | community feed |
| GET | `/recommendations/communities` | join suggestions |
| GET | `/recommendations/people` | follow / partner suggestions |
| GET | `/recommendations/challenges` | challenge suggestions |
| POST | `/feed/events` | client impression/dwell events (training signal) |

## 9. Uploads, notifications, messages

| Method | Path | Notes |
|---|---|---|
| POST | `/uploads/presign` | `{content_type,purpose}` → `{url,fields,s3_key}` |
| GET | `/notifications?cursor=` | list |
| POST | `/notifications/read` | mark read |
| POST | `/devices` | register push token |
| GET/POST | `/messages/threads` | DM threads |
| WS | `/ws/notifications` | live notifications |

## 10. Versioning & deprecation

- URI version `/v1`; additive changes don't bump version. Breaking changes → `/v2` with overlap +
  `Deprecation`/`Sunset` headers. Generated clients pinned per app release; OpenAPI snapshot-tested
  in CI.
