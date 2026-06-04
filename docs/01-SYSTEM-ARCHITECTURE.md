# 01 — System Architecture

## 1. Architectural style

- **Modular monolith → services**: start as a well-bounded modular monolith (FastAPI app with
  internal domains), extract high-load domains (feed, recsys, food-ML, agent) into services as
  traffic demands. This keeps MVP velocity high while leaving clean seams (`docs/15`).
- **Event-driven core**: writes emit domain events to Kafka; consumers handle fan-out (feed),
  embeddings, analytics, notifications, and memory updates — keeping the request path fast.
- **AI-first**: the Agent service is a first-class subsystem, not a bolt-on. It has its own
  memory store, tool runtime, and provider abstraction.

## 2. C4 — Context

```mermaid
flowchart TB
    user([User])
    coach([Human Coach / Creator])
    subgraph Forge[Forge Platform]
      mobile[Mobile App\nReact Native]
      web[Web App\nReact]
      api[API Gateway / BFF\nFastAPI]
      agent[Agent Service]
      ml[Food + Rec ML]
    end
    anthropic[(Anthropic Claude API)]
    push[(APNs / FCM)]
    oauth[(Google / Apple OAuth)]

    user --> mobile
    user --> web
    coach --> web
    mobile --> api
    web --> api
    api --> agent
    api --> ml
    agent --> anthropic
    api --> oauth
    api --> push
```

## 3. C4 — Containers

```mermaid
flowchart LR
    subgraph Client
      RN[React Native App]
      WEB[React Web]
    end

    subgraph Edge
      CF[CloudFront CDN]
      ALB[ALB / Ingress]
      WAF[WAF + Rate Limit]
    end

    subgraph App[Kubernetes - EKS]
      GW[API / BFF\nFastAPI]
      AGENT[Agent Service\nFastAPI + tool runtime]
      FOOD[Food-ML Service]
      REC[Recsys / Feed Service]
      SOCIAL[Social Service]
      WORKER[Celery Workers]
    end

    subgraph Data
      PG[(PostgreSQL 16\n+ pgvector)]
      REDIS[(Redis 7)]
      QDRANT[(Qdrant)]
      S3[(S3)]
      KAFKA[(Kafka)]
    end

    EXT[(Anthropic API)]

    RN & WEB --> CF --> WAF --> ALB --> GW
    GW --> AGENT & FOOD & REC & SOCIAL
    AGENT --> EXT
    AGENT --> QDRANT
    AGENT & SOCIAL & REC & FOOD --> PG
    GW & AGENT & REC --> REDIS
    GW & FOOD --> S3
    GW & SOCIAL & FOOD --> KAFKA --> WORKER
    WORKER --> PG & QDRANT & S3 & REDIS
```

## 4. Subsystems

| Subsystem | Responsibility | Key stores |
|---|---|---|
| **API/BFF** | AuthN/Z, request validation, orchestration, REST + WS endpoints | PG, Redis |
| **Agent service** | Agent loop, tool calling, provider abstraction, memory retrieval/write | Qdrant/pgvector, PG, Redis |
| **Food-ML** | OCR, vision inference, nutrition parsing, food matching | PG, S3, Redis |
| **Recsys/Feed** | Feed ranking, candidate generation, people/community recs | PG, Redis, Qdrant |
| **Social** | Posts, comments, likes, follows, communities, moderation | PG, S3 |
| **Workers** | Async pipelines (image, embeddings, fan-out, notifications, analytics) | all |

## 5. Core data flows

### 5.1 Conversational turn (agent)
```mermaid
sequenceDiagram
    participant App
    participant GW as API/BFF
    participant AG as Agent Service
    participant MEM as Memory (Qdrant+PG)
    participant LLM as Claude (provider abstraction)
    participant DB as Postgres

    App->>GW: POST /agent/messages (stream)
    GW->>AG: forward + user ctx
    AG->>MEM: retrieve relevant memories (RAG)
    AG->>DB: load profile summary (cached)
    AG->>LLM: messages + tools + system + memories
    LLM-->>AG: tool_use(get_recent_workouts)
    AG->>DB: execute tool
    AG->>LLM: tool_result
    LLM-->>AG: streamed answer
    AG-->>App: SSE tokens
    AG->>MEM: extract + persist new memories (async)
```

### 5.2 Food photo logging
```mermaid
sequenceDiagram
    participant App
    participant GW
    participant S3
    participant Q as Celery
    participant FOOD as Food-ML
    participant DB

    App->>GW: request upload URL
    GW-->>App: presigned S3 URL
    App->>S3: PUT image
    App->>GW: POST /food/analyze {s3_key}
    GW->>Q: enqueue analyze_food(s3_key)
    Q->>FOOD: OCR + vision + parse + match
    FOOD->>DB: upsert food, write candidate log
    FOOD-->>GW: result (via WS/poll)
    GW-->>App: structured nutrition + confidence
    App->>GW: confirm/correct -> UserFoodLog
```

### 5.3 Post fan-out (feed)
```mermaid
sequenceDiagram
    participant App
    participant SOCIAL
    participant KAFKA
    participant REC as Feed Worker
    participant REDIS

    App->>SOCIAL: create post
    SOCIAL->>KAFKA: emit post.created
    KAFKA->>REC: consume
    REC->>REC: score candidates per follower / community
    REC->>REDIS: push to follower feed caches (fan-out-on-write for <N followers)
    Note over REC: large accounts -> fan-out-on-read (pull) at request time
```

## 6. Event taxonomy (Kafka topics)

| Topic | Producer | Consumers |
|---|---|---|
| `user.profile.updated` | API/Agent | memory, analytics, recsys |
| `agent.message.completed` | Agent | memory extraction, analytics |
| `food.logged` | API/Food-ML | analytics, agent-memory, streaks |
| `workout.logged` | API | analytics, progress-insights, streaks |
| `post.created` / `post.engaged` | Social | feed fan-out, recsys, analytics |
| `follow.created` | Social | recsys (graph), feed |
| `embedding.requested` | many | embedding worker → Qdrant/pgvector |
| `notification.requested` | many | notification worker → APNs/FCM |

Events use a versioned envelope: `{ event, version, id, occurred_at, actor_id, payload }`,
serialized as JSON (MVP) → Avro/Protobuf + Schema Registry (scale).

## 7. Cross-cutting concerns

- **Idempotency**: client-supplied `Idempotency-Key` on mutating endpoints; dedup in Redis.
- **Tracing**: OpenTelemetry across BFF → Agent → tools → DB; trace id propagated to LLM logs.
- **Config**: 12-factor; secrets in AWS Secrets Manager; feature flags in DB + Redis (see `02`).
- **Multi-tenant isolation**: row-level `user_id` scoping enforced in repository layer + RLS option.
- **Provider abstraction**: all LLM/embedding/vision calls go through an interface (`docs/03 §4`).

## 8. Environments

`local` (docker-compose) → `dev` → `staging` → `prod`. Each prod region is multi-AZ.
Blue/green or canary deploys via Argo Rollouts (`docs/12`).
