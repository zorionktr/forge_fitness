# 14 — MVP Roadmap

Goal of MVP: prove the **core insight** — an AI coach with memory + frictionless food/workout
logging + a light social loop drives retention. Ruthlessly cut everything else.

## 1. MVP scope (in)

- Conversational onboarding + Personal Agent (Sonnet) with memory + core tools.
- Food logging: **barcode + label OCR + meal photo (vision LLM)** + text; canonical food DB.
- Workout logging + AI-generated plan; exercise library (seeded).
- Progress: weight/measurements/photos + weekly AI insight.
- Social v1: profiles, posts (image/text), communities (seeded), follows, comments, likes,
  **content-based feed** (ranked, not just chron).
- Auth: email + Google + Apple. Push notifications. Premium paywall scaffold (not heavily gated).

## 2. MVP scope (out → fast-follow)

Video posts/HLS, workout-partner matching, challenges, coach/creator marketplaces, collaborative
recsys/learned ranker, Qdrant (use pgvector), Kafka (use Redis streams/Celery first), multi-region,
wearables. *Architecture leaves seams for all of these.*

> **MVP simplification:** run as the modular monolith on a managed Postgres + Redis; use Celery with
> a Redis/Redpanda broker instead of full MSK; pgvector instead of Qdrant. Swap in the heavier infra
> as load demands (`docs/15`).

## 3. 12-week plan

| Phase | Weeks | Deliverables |
|---|---|---|
| **0 — Foundations** | 1–2 | Repo/monorepo, CI, IaC baseline, auth (JWT+OAuth), DB schema + migrations, S3 uploads, observability skeleton |
| **1 — Agent core** | 3–5 | Provider abstraction (Anthropic), agent loop + streaming SSE, tool registry, profile/workout/nutrition read+write tools, memory store + RAG (pgvector), conversational onboarding |
| **2 — Food & workouts** | 5–7 | Barcode + label OCR + meal-photo vision pipeline, food DB + matching, food logging UX, workout logging + AI plan, exercise library seed |
| **3 — Progress & insights** | 7–8 | Measurements, progress photos, PRs, weekly insight job, agent proactive nudges |
| **4 — Social v1** | 8–10 | Profiles, posts, communities (seeded), follows/comments/likes, content-based ranked feed, notifications |
| **5 — Polish & beta** | 10–12 | Guardrails/safety, rate limits, GDPR export/delete, performance pass, paywall scaffold, closed beta + instrumentation |

## 4. Milestones / exit criteria

- **M1 (wk5):** a user onboards by chat and gets a grounded answer about their own (seeded) data.
- **M2 (wk7):** log a meal by photo & barcode and a workout in < 60s each; agent references them.
- **M3 (wk8):** weekly insight + nudge delivered; progress photos timeline works.
- **M4 (wk10):** join a community, post, and see a ranked personalized feed.
- **M5 (wk12):** closed beta live, SLOs met, activation funnel instrumented.

## 5. Team shape (lean)

- 2 backend (FastAPI/agent/ML-integration), 1 ML (food vision + recsys), 2 mobile (RN), 1 web,
  1 design, 1 PM/founder. Plus part-time DevOps/SRE. Agent + food intelligence are the
  highest-leverage hires.

## 6. Build vs buy (MVP)

| Need | MVP choice |
|---|---|
| LLM | Anthropic API (buy) |
| Food vision | Vision LLM (buy) → custom CV later |
| OCR | AWS Textract (buy) |
| Nutrition DB seed | USDA FDC + OpenFoodFacts (open data) |
| Auth | Self-host JWT + OAuth verify (own the tokens) |
| Analytics | PostHog/Amplitude early → warehouse later |
| Push | Expo Notifications → APNs/FCM |

## 7. Key risks for MVP & how we de-risk early

- **Food-photo accuracy** — barcode-first + easy correction; validate ±20% kcal on a test set wk6.
- **Agent groundedness** — eval harness from wk3; groundedness gate in CI.
- **LLM cost** — token dashboard + budgets from wk3; caching on by default.
- **Cold-start social** — seed 10–15 communities + creator content before beta.
- **Onboarding completion** — measure funnel; hybrid chat+chips to cut friction.
