# 08 — Mobile App Architecture

## 1. Recommendation: React Native (Expo)

**Choose React Native + Expo** over Flutter for Forge:

| Criterion | RN + Expo | Flutter | Verdict |
|---|---|---|---|
| Shared logic with web (React) | ✅ types, SDK, validation reuse | ❌ Dart silo | RN — we have a React web app |
| Hiring / ecosystem | ✅ huge JS/TS pool | ⚠️ smaller | RN |
| OTA updates | ✅ EAS Update | ⚠️ limited | RN |
| Streaming LLM / SSE / WS | ✅ mature JS libs | ✅ ok | tie |
| AI/LLM tooling, JSON-heavy | ✅ TS end-to-end | ⚠️ | RN |
| Raw UI perf | ⚠️ good (RN new arch) | ✅ excellent | Flutter (not decisive here) |

Decisive factor: **a TypeScript monorepo** lets mobile + web share the API client, types
(generated from OpenAPI), Zod validators, and analytics — huge velocity for a small startup.

**Stack:** Expo (SDK 51+), Expo Router (file-based nav), TypeScript, TanStack Query (server state),
Zustand (local UI state), React Hook Form + Zod, Reanimated/Gesture Handler, MMKV (fast storage),
Expo SecureStore (tokens), Expo Notifications (push), Expo Camera/ImagePicker (food/progress
photos), Sentry, EAS Build/Update.

## 2. Screens (per PRD)

Auth · Onboarding (conversational) · AI Chat · Feed · Communities · Workout · Nutrition · Progress ·
Profile · Settings · Notifications · Messages.

Navigation: bottom tabs = **Chat · Feed · Log (FAB) · Progress · Profile**; Communities, Messages,
Notifications, Settings reachable from headers/stacks. The **Log FAB** opens a quick-action sheet
(scan food, photo meal, log workout, ask agent) — the core "fast path."

## 3. Folder structure

```
forge-mobile/
├── app/                          # Expo Router (file-based routes)
│   ├── (auth)/
│   │   ├── sign-in.tsx
│   │   ├── sign-up.tsx
│   │   └── oauth-callback.tsx
│   ├── (onboarding)/
│   │   └── chat.tsx              # conversational onboarding
│   ├── (tabs)/
│   │   ├── _layout.tsx           # bottom tab bar
│   │   ├── chat/index.tsx        # AI Chat
│   │   ├── feed/index.tsx
│   │   ├── progress/index.tsx
│   │   └── profile/index.tsx
│   ├── communities/[slug].tsx
│   ├── workout/[id].tsx
│   ├── nutrition/index.tsx
│   ├── messages/[threadId].tsx
│   ├── notifications/index.tsx
│   ├── settings/index.tsx
│   └── _layout.tsx               # providers root
├── src/
│   ├── api/                      # generated OpenAPI client + hooks
│   │   ├── client.ts
│   │   ├── generated/            # `openapi-typescript` output
│   │   └── hooks/                # useChat, useFeed, useFoodLog...
│   ├── features/                 # feature-sliced modules
│   │   ├── auth/                 # store, screens-logic, services
│   │   ├── onboarding/
│   │   ├── chat/                 # streaming agent UI, tool-call rendering
│   │   ├── feed/
│   │   ├── workout/
│   │   ├── nutrition/            # camera capture, barcode, log flow
│   │   ├── progress/
│   │   ├── community/
│   │   └── profile/
│   ├── components/               # shared UI (design system)
│   │   ├── ui/                   # Button, Card, Sheet, Avatar...
│   │   ├── chat/                 # MessageBubble, StreamingText, ToolChip
│   │   └── media/                # ImageUploader, VideoPlayer
│   ├── lib/
│   │   ├── auth/                 # token storage (SecureStore), refresh
│   │   ├── query.ts              # TanStack Query client
│   │   ├── storage.ts            # MMKV
│   │   ├── streaming.ts          # SSE/WS consumption
│   │   ├── analytics.ts
│   │   └── notifications.ts
│   ├── store/                    # Zustand stores (UI/local)
│   ├── theme/                    # tokens, dark mode
│   ├── types/                    # shared domain types
│   └── config/                   # env, feature flags
├── assets/
├── app.config.ts                 # Expo config (env-driven)
├── eas.json                      # build/update profiles
├── tsconfig.json
└── package.json
```

> In a monorepo (`/apps/mobile`, `/apps/web`, `/packages/api-client`, `/packages/types`), the
> `api`, `types`, and validators live in shared packages consumed by both apps.

## 4. State & data strategy

- **Server state**: TanStack Query (caching, optimistic updates, offline persistence via MMKV).
- **Local/UI state**: Zustand (lightweight, no boilerplate).
- **Forms**: React Hook Form + Zod (Zod schemas shared with backend contract).
- **Optimistic logging**: meals/workouts/likes apply instantly, reconcile on server confirm —
  critical for the "fast path" feel.

## 5. Conversational onboarding & chat UX

- Chat screen consumes the agent **SSE stream**; renders tokens live.
- **Tool calls surfaced** as subtle "doing X…" chips (e.g. "checking your workouts") so the agent
  feels active and trustworthy.
- Hybrid input: free text + tappable quick-reply chips the agent can emit (e.g. goal options),
  reducing typing without becoming a form.
- Profile completeness ring shown during onboarding; never blocks using the app.

## 6. Camera / food pipeline (mobile side)

1. Capture (Expo Camera) or pick image; client compresses.
2. Request presigned URL → upload to S3 directly.
3. `POST /food/analyze` → subscribe to result over WS (or poll).
4. Show analysis with confidence; user confirms/corrects → log.
5. Barcode scanning path uses Expo Camera barcode scanner for the fast/accurate route.

## 7. Offline & resilience

- Read caches persisted (feed, recent logs, profile) for offline viewing.
- Write queue: logs created offline are queued (MMKV) and flushed with idempotency keys on
  reconnect.
- Graceful streaming reconnect for chat.

## 8. Push notifications

Expo Notifications → device token registered with backend → APNs/FCM. Categories map to
`notifications.type`; deep links route into the relevant screen. Respect quiet hours & prefs.

## 9. Performance & release

- New RN architecture (Fabric/TurboModules) enabled; FlashList for feeds; image caching;
  Reanimated for 60fps interactions.
- **EAS Build** for binaries, **EAS Update** for OTA JS updates (ship fixes without store review).
- Sentry for crash/perf; feature flags gate risky features per cohort.
