# Forge — AI-Native Fitness Social Platform

> MyFitnessPal + Reddit + Instagram + Strava + ChatGPT, rebuilt around a single principle:
> **the AI is the primary interface.**

Forge gives every user a **Personal Fitness Agent** that coaches, tracks nutrition, designs
workouts, remembers everything, and lives inside a Reddit/Instagram-style social network for
fitness. There are no large onboarding forms — the agent builds your profile through conversation.

---

## Repository layout

```
Fitness/
├── docs/                      # The full design (read these in order)
│   ├── 00-PRD.md                       Product Requirements Document
│   ├── 01-SYSTEM-ARCHITECTURE.md       High-level system + C4 + event flow
│   ├── 02-DATABASE-DESIGN.md           Full Postgres schema, indexes, partitioning, caching
│   ├── 03-AGENT-ARCHITECTURE.md        Agent loop, provider abstraction, tool calling
│   ├── 04-AI-MEMORY-RAG.md             Memory tiers + RAG retrieval pipeline
│   ├── 05-FOOD-INTELLIGENCE.md         Image → OCR → vision → nutrition → log pipeline
│   ├── 06-SOCIAL-NETWORK.md            Profiles, posts, communities, graph
│   ├── 07-RECOMMENDATION-SYSTEM.md     Feed ranking + people/community/content recsys
│   ├── 08-MOBILE-APP.md                React Native (Expo) architecture + folder structure
│   ├── 09-BACKEND-ARCHITECTURE.md      FastAPI services, event-driven, workers
│   ├── 10-API-DESIGN.md                REST + streaming + WebSocket API spec
│   ├── 11-SECURITY.md                  Auth, PII, GDPR, LLM/prompt-injection defense
│   ├── 12-DEPLOYMENT.md                Docker, K8s, AWS, CI/CD, observability
│   ├── 13-ANALYTICS-MONETIZATION.md    Metrics, experimentation, business model
│   ├── 14-MVP-ROADMAP.md               12-week MVP plan + milestones
│   └── 15-SCALING-PLAN.md              100 → 10,000,000 users
├── backend/                   # FastAPI scaffold (production layout)
├── frontend/                  # React (web) scaffold — mobile is React Native, see docs/08
├── infra/                     # Terraform, Kubernetes, Docker, monitoring
└── .github/workflows/         # CI/CD
```

## Recommended reading order

1. **`docs/00-PRD.md`** — what we're building and why.
2. **`docs/01-SYSTEM-ARCHITECTURE.md`** — the 10,000-ft view.
3. Then any deep dive.

## Tech stack (decisions, not options)

| Layer | Choice | Why |
|---|---|---|
| Mobile | **React Native + Expo** | One codebase, OTA updates, fastest path to iOS+Android. See `docs/08`. |
| Web | React + Vite + TanStack Query | Shares types/SDK with mobile via a generated client. |
| Backend | **FastAPI** (Python 3.12) | Async, first-class typing, great LLM/ML ecosystem. |
| Primary DB | **PostgreSQL 16** (+ `pgvector`) | Relational core + vector search in one engine to start. |
| Cache / queues | **Redis 7** | Sessions, rate limits, feed cache, Celery broker. |
| Vector DB | **pgvector → Qdrant** | Start in Postgres; graduate hot vector workloads to Qdrant at scale. |
| Object storage | **S3** (+ CloudFront) | Images, progress photos, workout clips. |
| Event bus | **Kafka** (Redpanda for dev) | Fan-out for feed, recsys, analytics, memory updates. |
| Async tasks | **Celery** | Image pipeline, embeddings, notifications, fan-out. |
| LLM | **Anthropic Claude (Sonnet)** via a provider-abstraction layer | Swappable to OpenAI/Gemini/Grok/local. See `docs/03`. |
| Infra | **Docker + Kubernetes (EKS)**, **Terraform** | Reproducible, multi-AZ, autoscaling. |

## Status

This repository is a **design + production-grade scaffold**, not a finished product. The `docs/`
set is complete and implementation-ready; `backend/` and `frontend/` contain the real folder
structure with representative, runnable-shaped code (core wiring, models, agent loop, key
endpoints) intended to be filled in along the MVP roadmap (`docs/14`).
```

Generated as a Staff-Engineer-level design for an AI-native fitness startup.
```
