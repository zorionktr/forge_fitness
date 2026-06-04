# 00 — Product Requirements Document (PRD)

## 1. Vision

**Forge is an AI-native fitness companion wrapped in a social network.**
Every user gets a Personal Fitness Agent that acts as coach, nutritionist, accountability
partner, and health companion. Around that agent sits a Reddit + Instagram + Strava-style
social graph for fitness culture: communities, transformation journeys, workout clips, and
discussion.

**One-line:** *"Your AI coach that also happens to be a social network."*

### Why now
- LLMs are finally good enough to replace static onboarding forms and rule-based "plans."
- Fitness apps are fragmented: logging (MFP), social (IG/Reddit), tracking (Strava), coaching
  (human PT). No product unifies them with memory and personalization.
- Vision models can read a plate of food or a nutrition label well enough to log it in one tap.

### Core principle: **AI is the primary interface**
- No long forms. The agent asks questions naturally and progressively builds the profile.
- Logging, planning, Q&A, motivation, and discovery all flow through (or are augmented by) the agent.
- The UI is the *fast path*; the agent is the *smart path*. Both write to the same data model.

---

## 2. Target users & jobs-to-be-done

| Segment | Primary JTBD | Killer feature |
|---|---|---|
| Beginners | "Tell me what to do, don't overwhelm me." | Conversational onboarding + adaptive plan |
| Weight loss | "Stay in a deficit without misery." | Photo food logging + agent nudges |
| Weight gain | "Eat enough, train progressively." | Surplus tracking + progressive overload |
| Bodybuilders | "Optimize hypertrophy & physique." | Progress photos + volume analytics |
| Powerlifters | "Peak my S/B/D." | PR tracking, RPE/percentage programming |
| Calisthenics | "Progress skills & reps." | Skill progressions, no-equipment plans |
| Runners / Cyclists | "Train for distance/pace, recover." | Cardio load, Strava-style activity feed |
| Sports players | "Sport-specific conditioning." | Sport coach persona + periodization |
| Lifestyle | "Be healthier, feel accountable." | Habits, streaks, light social |

**Primary persona (MVP focus):** *"Goal-driven generalist"* — wants to lose fat or build muscle,
trains 3–5×/week, will log food if it's fast, motivated by community + a coach that remembers them.

---

## 3. Product pillars

1. **The Agent** — personalized, persistent, tool-using coach (`docs/03`).
2. **Memory** — the agent never forgets your history, injuries, preferences (`docs/04`).
3. **Food Intelligence** — log a meal from a photo/label in seconds (`docs/05`).
4. **Workouts & Progress** — adaptive programs, PRs, measurements, photos.
5. **Social** — communities, feed, follows, transformations (`docs/06`).
6. **Discovery** — AI-ranked feed + people/community recommendations (`docs/07`).

---

## 4. Feature requirements (by area)

### 4.1 Conversational onboarding
- The agent extracts profile facts from free conversation and writes structured `profile` fields.
- Required-by-value-not-by-form: goal, training frequency, gym access, injuries, body stats.
- Progress is shown as a **profile completeness meter** ("I know 6/10 things about you").
- The agent must be able to re-ask later when context is missing ("What's your current bodyweight?").
- **Acceptance:** a new user can reach a usable plan + first logged meal in < 5 minutes of chat.

### 4.2 Personal Agent
- Personas: Friendly, Aggressive, Scientific, Sports, Nutrition, Recovery coach. Switchable anytime.
- Reads: profile, workouts, nutrition, progress, social, goals. Writes: plans, goals, logs, memories.
- Tool calling for all data access (no hallucinated numbers — see `docs/03` tool list).
- Streaming responses; tool calls visible as "thinking/acting" UI affordances.
- **Acceptance:** "What did I eat yesterday and am I on track?" returns grounded, cited-from-DB answers.

### 4.3 Food intelligence
- Inputs: food photo, nutrition label, ingredient list (image), barcode, or text.
- Outputs: food name, ingredients, calories, macros (P/C/F), fiber/sugar/sodium, serving size, health score.
- Match against a canonical `food` database; create new verified-pending entries when unmatched.
- One-tap "log again," "eat this regularly?" agent guidance.
- **Acceptance:** packaged food via barcode/label is logged with correct macros ≥ 90% of the time;
  plate photo estimate within ±20% kcal for common meals.

### 4.4 Workouts
- Log: exercise, sets, reps, weight, RPE, rest, duration. Exercise library with media.
- AI-generated programs; dynamic adjustment based on adherence, RPE, and progress.
- **Acceptance:** agent can generate a 4-week progressive plan tailored to equipment + injuries.

### 4.5 Progress tracking
- Bodyweight, measurements, body fat, PRs, strength progression, consistency scores, progress photos.
- AI insights ("your bench stalled 3 weeks — deload or add volume").
- **Acceptance:** weekly auto-generated insight summary per user.

### 4.6 Social network
- Profiles, posts (image/video/text), comments, likes, shares, follows, communities (subreddit-like).
- Transformation journeys (before/after timelines), workout clips, discussions.
- **Acceptance:** user can join communities, post, and see an AI-ranked personalized feed.

### 4.7 Recommendations
- Personalized feed ranking; recommend communities, creators, posts, workout partners, challenges.
- **Acceptance:** feed CTR and dwell beat a reverse-chron baseline in A/B test.

---

## 5. Non-functional requirements

| Category | Target |
|---|---|
| Latency (API p95) | < 250 ms for CRUD; first agent token < 1.5 s; full food-photo analysis < 8 s |
| Availability | 99.9% (MVP) → 99.95% (scale) |
| Privacy | GDPR + CCPA; export & delete; PII encryption at rest |
| Security | JWT + OAuth (Google/Apple), RBAC, rate limiting, prompt-injection defense |
| Scale | Architected for 10M users / 100M food logs (`docs/15`) |
| Cost | LLM cost guardrails: per-user token budgets, caching, model tiering |
| Accessibility | WCAG 2.1 AA on web; mobile a11y labels |

---

## 6. Out of scope (MVP)

- Wearable device deep integrations (Apple Health/Garmin) — *fast-follow*, see roadmap.
- Human coach marketplace payments — *Phase 2 monetization*.
- Live video / real-time group workouts.
- Multi-language (English first; i18n-ready architecture).

---

## 7. Success metrics (North Star + supporting)

- **North Star:** *Weekly Active Loggers who also engage socially* (captures both core loops).
- Activation: % new users who complete conversational onboarding + log 1 meal + 1 workout in 7 days.
- Retention: D1 / D7 / D30; W4 retention ≥ 30% target.
- Agent: messages/user/week; tool-call grounded-answer rate; thumbs-up rate.
- Nutrition adherence; workout completion rate; community engagement (posts/comments/joins).
- Recommendation quality: feed CTR, dwell time, follow-through on suggestions.

---

## 8. Key product risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucinates health advice | Tool-grounded answers, medical disclaimers, guardrail layer, refusal on diagnosis |
| Food recognition inaccurate | Confidence scores, easy correction UI, learn from corrections, barcode-first |
| LLM cost runs away | Token budgets, prompt caching, model tiering, summarized memory |
| Cold-start social/feed | Seed communities + creators, content-based recs before collaborative signal |
| Privacy/trust (health PII) | Encryption, granular sharing controls, transparent data use, GDPR tooling |
| Onboarding friction (chat fatigue) | Hybrid: chat + optional quick-tap chips; never block core actions on profile completeness |
