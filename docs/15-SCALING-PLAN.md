# 15 — Scaling Plan: 100 → 10,000,000 users

The architecture is intentionally a **modular monolith with clean seams** so we don't pay
distributed-systems tax early, but can extract and scale each subsystem independently. Below: what
changes at each stage.

## Stage 0 — 100 users (closed beta)

- **Infra**: single small EKS cluster (or even ECS/Fargate), one RDS Postgres (db.t/m small,
  Multi-AZ off ok for beta), one Redis, Celery on Redis broker, **pgvector**, S3+CloudFront.
- **App**: monolith image (api+agent+workers via different commands).
- **Focus**: product correctness, agent groundedness, food accuracy, instrumentation. Not scale.
- **Cost lever**: prompt caching + model tiering already on.

## Stage 1 — 10,000 users

- RDS: enable Multi-AZ + 1 read replica; **PgBouncer** for pooling; tune indexes; partitions live.
- Redis cache hot paths (profile summary, feed pages, barcode foods).
- Introduce **Kafka (MSK/Redpanda)** for fan-out + analytics (replace inline/Redis-stream paths).
- HPA on api/agent; KEDA on workers. Sentry + Grafana dashboards mature.
- Feed: fan-out-on-write to Redis for normal accounts.
- **Bottlenecks to watch**: LLM concurrency/cost, food-vision latency, DB write hot rows (counters).

## Stage 2 — 100,000 users

- **Service extraction** begins: split **Agent**, **Food-ML**, **Recsys/Feed** into their own
  deployments (still shared DB initially, separate schemas/ownership). Independent scaling + GPU
  node pool for vision.
- **Vectors → Qdrant**: migrate memory/post/food embeddings off pgvector to Qdrant (per-user
  payload filtering, higher recall/QPS). pgvector stays for small/secondary use.
- Read replicas for read-heavy domains (feed, social); route reads via replica-aware sessions.
- CDN everything static + media; image/video transcode workers; HLS for video.
- **Caching tiers**: add per-service caches; cache stampede protection (locks, jittered TTL).
- Recsys: introduce learned ranker (LightGBM) on logged engagement; feature store (offline +
  Redis online).
- LLM cost governance critical: budgets enforced, summarized memory, Haiku for extraction.

## Stage 3 — 1,000,000 users

- **Database scaling**: this is the main event.
  - Vertical scale RDS + many read replicas first.
  - **Functional partitioning**: move social, nutrition, agent-memory to separate Postgres
    clusters (per-domain DBs) — they have different access patterns and growth.
  - **Horizontal sharding** for the largest tables (`user_food_logs`, `workout_sets`, `posts`,
    `messages`): shard by `user_id` (hash) via Citus or app-level routing. UUID PKs + strictly
    user-scoped access make this clean.
- **Feed at scale**: hybrid fan-out matured — pull for large accounts, push for the rest; precomputed
  candidate stores; ranking service horizontally scaled; aggressive feed caching.
- **Kafka** partitioned per high-volume topic; Schema Registry (Avro/Protobuf); tiered storage.
- **Food-ML**: replace vision-LLM with in-house fine-tuned classifier + portion estimator on
  autoscaled GPU (Triton/KServe); vision-LLM only for long tail. Big COGS win.
- **Multi-region** read paths; primary write region + async replicas; latency-based routing via
  Route 53; S3 CRR.
- Cost: reserved/savings plans for steady capacity, spot for batch/workers, GPU autoscaling.

## Stage 4 — 10,000,000 users

- **Full microservices** along the seams defined since MVP; service mesh (Istio/Linkerd) for
  mTLS, traffic shaping, observability.
- **Sharded, multi-cluster Postgres** (Citus or Vitess-style) + dedicated analytical warehouse;
  CDC (Debezium) → lake → warehouse; OLTP never runs analytics.
- **Graph workloads** (people-you-may-know, 2nd-degree) on a dedicated graph store / precomputed
  adjacency; follow edges in their own scalable store.
- **Recsys**: two-tower retrieval + deep ranking network, online learning, dedicated feature
  platform; multi-objective (engagement + healthy-outcome guardrails).
- **Agent at scale**: regionally deployed; self-hosted/open models via vLLM for cheap paths
  (extraction, classification) through the same provider abstraction; provider failover &
  multi-vendor routing for resilience and cost.
- **Multi-region active-active** for read; careful write routing; global CDN; per-region data
  residency for compliance.
- **Org**: platform teams (infra, data, ML-platform, agent-platform) + product squads.

## Capacity rules of thumb (drive autoscaling & sharding triggers)

| Signal | Action |
|---|---|
| DB CPU > 60% sustained / replica lag rising | add replica → functional split → shard |
| Single table > ~500M rows or hot partition | partition + shard by user_id |
| Kafka consumer lag growing | scale consumers (KEDA) / add partitions |
| LLM $/active-user above target | tiering, caching, summarization, self-host cheap paths |
| Vision p95 > 8s or GPU saturated | scale GPU pool / move to in-house CV |
| Feed rank p95 > target | precompute more, cache, scale ranker, shed exploration |

## Constant principles across stages

1. **User-scoped, UUID-keyed data** → sharding is always available.
2. **Events decouple writes from fan-out** → each consumer scales independently.
3. **Provider abstraction** → LLM cost/vendor is a config lever, not a rewrite.
4. **Cache + denormalized counters** → reads never aggregate hot tables.
5. **Cost is a first-class SLO** (esp. LLM/vision) tracked from day one.
