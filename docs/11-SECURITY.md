# 11 — Security & Privacy Design

Forge stores sensitive health PII (weight, body fat, injuries, photos) and runs an LLM that
touches user data — security and LLM-safety are first-class.

## 1. Authentication

- **JWT**: short-lived access tokens (~15 min) + rotating refresh tokens (~30 days) with reuse
  detection (stolen-refresh → revoke family). Tokens carry `sub`, `role`, `jti`; revocation via
  Redis `jti` blocklist.
- **Password**: Argon2id hashing; breach-password check; optional TOTP MFA.
- **OAuth / Social login**: Google (verify `id_token` against Google certs) and Apple (verify
  identity token, handle private-relay email). Account linking by verified email.
- Tokens stored in mobile **SecureStore** / web **httpOnly secure cookies** (web uses cookie+CSRF
  for refresh; access token in memory).

## 2. Authorization (RBAC + ownership)

- Roles: `user, creator, coach, moderator, admin` (`users.role`).
- **Ownership checks** in the service layer on every user-scoped resource; the agent's tools run
  through the *same* layer (the agent can never exceed the user's permissions).
- Defense-in-depth: optional Postgres **Row-Level Security** keyed on `user_id` for the most
  sensitive tables (profiles, logs, memories).
- Admin/moderation actions are gated, scoped, and **audit-logged** (`audit_logs`).

## 3. Data protection

- **In transit**: TLS 1.2+ everywhere; HSTS; cert rotation via ACM.
- **At rest**: RDS/EBS/S3 encryption with **KMS**; per-environment keys.
- **PII handling**: data catalog tags PII columns (email, OAuth sub, photos, health metrics);
  application-level field encryption for the most sensitive at-rest values where warranted;
  access to PII is logged.
- **Secrets**: AWS Secrets Manager / SSM; never in code or images; rotated.
- **Photos**: private S3 buckets, served via short-lived signed CloudFront URLs; visibility
  enforced before signing.

## 4. GDPR / CCPA

- **Right to access/export**: async job assembles all user data + media into a downloadable archive.
- **Right to erasure**: soft-delete immediately, hard-delete + S3 purge ≤ 30 days; `user.deleted`
  event cascades to memories, embeddings, recsys, caches.
- **Consent & purpose**: explicit consent for health data processing; granular sharing controls;
  data-use transparency screen.
- **Data residency**: region-pinned storage; DPA with subprocessors (incl. LLM provider).
- **Minimization**: only retain what's needed; configurable retention on logs/analytics.

## 5. LLM & prompt-injection security

This is the novel attack surface — treated explicitly:

| Threat | Mitigation |
|---|---|
| **Prompt injection** (via user content, food labels, posts, image OCR) | Treat all retrieved/user/3rd-party text as **untrusted data**, never instructions; structural separation (data in clearly delimited blocks); an instruction-injection classifier screens inputs |
| **Tool abuse / privilege escalation** | Tools run under the user's own authz; write tools confirmed + audited; arg schema validation; no tool can read another user's data by construction |
| **Data exfiltration via model** | System prompt forbids revealing other users' data; per-user memory namespacing makes cross-user leakage impossible at the data layer |
| **Jailbreak → harmful advice** (eating disorders, dangerous cuts, dosing) | Safety guardrail layer pre+post; refuse diagnosis/medical dosing; ED-risk language → supportive redirect + resources; medical disclaimers |
| **PII in prompts/logs** | PII redaction before logging; sampling; access-controlled LLM logs |
| **Cost/DoS via prompts** | Per-user token budgets, max tool calls/turn, rate limits, output caps |
| **Indirect injection from OCR/vision** | OCR'd label/ingredient text is data-only; never executed as instructions |

Guardrail pipeline: **input screen** (injection + safety classifier) → **constrained system
prompt** → **tool authz** → **output screen** (policy classifier, groundedness check, disclaimer
injection). High-risk → refuse/escalate.

## 6. Application security

- **Rate limiting**: Redis sliding-window per user + per IP + per route; stricter on auth,
  agent, upload, posting. WAF (AWS WAF) for L7 (SQLi/XSS/bot) at the edge.
- **Input validation**: Pydantic everywhere; strict content-type; size limits on uploads.
- **Injection**: parameterized queries only (SQLAlchemy); no string-built SQL.
- **File uploads**: presigned, content-type + size validated, AV/malware + NSFW scan in the
  pipeline before content goes live; EXIF stripped from photos.
- **CORS**: allowlist origins; CSRF protection for cookie-based web flows.
- **Headers**: CSP, X-Content-Type-Options, Referrer-Policy, etc.
- **Dependencies**: SCA (Dependabot/Snyk), SBOM, pinned versions, image scanning (Trivy).
- **Secrets scanning** + SAST in CI; DAST against staging.

## 7. Abuse, trust & moderation

- Account-takeover protection (anomalous login alerts, device tracking).
- Content moderation pipeline (`docs/06 §6`); trust scores; shadow-limits for spam/bots.
- Bot/fraud detection on engagement and signup (velocity, device fingerprint).

## 8. Audit & incident response

- `audit_logs` (partitioned, append-only) for auth events, PII access, admin/mod actions, exports,
  deletions, agent write-tools.
- Centralized, tamper-evident logging; alerting on anomalies (SIEM).
- Documented incident response runbook; breach notification process per GDPR (72h).

## 9. Compliance posture (roadmap)

GDPR/CCPA from day one; SOC 2 Type II as the platform matures; HIPAA is **out of scope** unless we
become a covered entity (we present as wellness, not medical — reinforced by the agent's
no-diagnosis guardrails).
