# 12 — Deployment & Infrastructure

Cloud: **AWS**. Orchestration: **Kubernetes (EKS)**. IaC: **Terraform**. Everything reproducible,
multi-AZ, autoscaled.

## 1. Topology

```mermaid
flowchart TB
    subgraph Edge
      R53[Route 53] --> CF[CloudFront]
      CF --> WAF[AWS WAF]
      WAF --> ALB[ALB / Ingress-NGINX]
    end
    subgraph EKS[EKS - multi-AZ]
      subgraph ns_api[ns: api]
        API[api-bff pods - HPA]
        AGENT[agent pods - HPA]
        SOCIAL[social pods]
      end
      subgraph ns_ml[ns: ml]
        FOOD[food-ml pods - GPU pool]
        REC[recsys pods]
      end
      subgraph ns_worker[ns: workers]
        CW[celery workers - KEDA]
        BEAT[celery beat]
      end
    end
    subgraph Data[Managed data]
      RDS[(RDS Postgres - Multi-AZ + replicas)]
      EREDIS[(ElastiCache Redis)]
      MSK[(MSK / Kafka)]
      QDR[(Qdrant - EKS statefulset or cloud)]
      S3[(S3)]
    end
    ALB --> API & AGENT & SOCIAL
    API --> RDS & EREDIS & S3 & MSK
    AGENT --> RDS & QDR & EREDIS
    FOOD --> RDS & S3
    MSK --> CW
    CF --> S3
```

## 2. Containers & images

- Multi-stage Dockerfiles; distroless/slim runtime; non-root user; pinned base + Trivy scan.
- Images: `api-bff`, `agent`, `food-ml` (GPU base), `recsys`, `worker` (shared codebase, different
  entrypoints/commands — modular monolith → split images as services extract).
- Pushed to **ECR**; immutable tags = git SHA.

## 3. Kubernetes

- **Deployments** for stateless services; **HPA** on CPU + custom concurrency/latency metrics.
- **KEDA** scales Celery workers on Kafka lag / queue depth (scale-to-near-zero off-peak).
- GPU node group (food-ml vision at scale) with taints/tolerations; CPU node groups otherwise;
  spot instances for workers, on-demand for API.
- `PodDisruptionBudgets`, `requests/limits`, liveness/readiness/startup probes, topology spread.
- Config via ConfigMaps; secrets via **External Secrets Operator** ← AWS Secrets Manager.
- Ingress: NGINX (or ALB controller) + cert-manager (ACM).
- Layout: `infra/k8s/base` (kustomize) + `overlays/{staging,prod}`.

## 4. Data layer ops

- **RDS Postgres** Multi-AZ, read replicas for read-heavy paths; **PgBouncer** (transaction mode)
  in-cluster for pooling. Automated snapshots + PITR. Partition maintenance job (`docs/02 §5`).
- **ElastiCache Redis** (cluster mode) for cache/queues/rate-limits.
- **MSK** (Kafka) multi-broker; Schema Registry at scale.
- **Qdrant** as statefulset (or managed) once vector load graduates from pgvector.
- **S3** with lifecycle policies (transition to IA/Glacier for old media, archive cold partitions).

## 5. CI/CD

```mermaid
flowchart LR
    PR[PR] --> CI[CI: lint, type, unit+integration, agent-evals, security scan, build image]
    CI --> REG[Push to ECR]
    REG --> CD[CD: deploy staging - Argo CD]
    CD --> E2E[E2E + smoke + load gate]
    E2E --> CAN[Canary to prod - Argo Rollouts]
    CAN --> PROD[Progressive rollout w/ auto-rollback]
```

- **GitHub Actions** for CI (`.github/workflows`): lint (ruff), type (mypy/pyright), tests
  (pytest + testcontainers), agent eval gate, OpenAPI snapshot, SAST/SCA, Docker build+scan.
- **Argo CD** (GitOps) for deploys; **Argo Rollouts** for canary/blue-green with metric analysis
  (error rate, latency, agent error rate) → auto-rollback.
- DB migrations via Alembic run as a pre-deploy K8s **Job** (expand/contract pattern for zero-downtime).
- Mobile: **EAS Build/Update**; web: build → S3 + CloudFront invalidation.

## 6. Observability

- **Metrics**: Prometheus + Grafana (RED/USE dashboards per service; LLM cost/token dashboards;
  feed CTR; food-pipeline latency). Alertmanager → PagerDuty.
- **Tracing**: OpenTelemetry → Tempo/Jaeger; traces span BFF→agent→tools→DB→LLM.
- **Logs**: structured JSON (structlog) → Loki / CloudWatch / OpenSearch; PII-redacted.
- **Errors**: Sentry (backend + mobile + web).
- **SLOs**: API p95 < 250ms, first agent token < 1.5s, 99.9% availability; error budgets drive
  release pace.
- **Synthetics**: uptime + critical-flow probes (login, chat, food log).

## 7. Cost controls

- Spot for workers/ML batch; autoscale-to-low off-peak; S3 lifecycle; right-sized RDS with
  replicas; **LLM cost governance** (caching, tiering, budgets — `docs/03 §8`) tracked on a Grafana
  cost dashboard with alerts.

## 8. Environments & DR

- `local` (docker-compose: pg, redis, redpanda, qdrant, minio) → `dev` → `staging` → `prod`.
- Prod multi-AZ; cross-region async replica + S3 CRR for DR. RPO ≤ 5 min, RTO ≤ 1 h targets.
- Backups tested via periodic restore drills; runbooks in repo.
