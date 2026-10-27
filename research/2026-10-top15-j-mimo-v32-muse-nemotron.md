# Stale-summary re-research: xiaomi/mimo-v2.6-pro, deepseek/deepseek-v3.2, meta/muse-spark-1.3-contributor, nvidia/nemotron-3.5-lightning:free — 2026-10-25

## Scope

Re-check of the four summaries flagged stale after the 2026-10-18/19 cycle, because none of the
four reaches the top-15 of any of the five policy domains' task boards on 2026-10-25 (a traffic
fact, not a quality verdict). Pulled on **2026-10-25**: OpenRouter endpoints API for all six slugs
(`https://openrouter.ai/api/v1/models/<id>/endpoints`, live fetch 2026-10-25); catalog +
per-model benchmark rows (`https://openrouter.ai/api/v1/models`, cache 2026-10-25 13:36);
Artificial Analysis feed (`https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis`,
`as_of` **2026-10-24**, 352 rows) and the combined feed incl. Design Arena
(`https://openrouter.ai/api/v1/benchmarks`, `as_of` **2026-10-25**, 1,893 rows); task boards
(`https://openrouter.ai/api/v1/classifications/task?window=7d`, `as_of` **2026-10-24**, 7-day
window, 29 tags, **top-10 rows only per tag**); daily tokens
(`https://openrouter.ai/api/v1/datasets/rankings-daily`, window **2026-09-25 → 2026-10-24**);
Artificial Analysis model pages and its Kimi K3.1 Pro launch article; LMArena's published dataset
(`https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset`, leaderboard publish date
**2026-10-22**, configs `text` and `text_style_control`, read via the HF datasets-server); Meta's
developer pricing page, DeepSeek's API docs, OpenRouter's limits docs, plus web search for
opinion/press from 2026-10-18 → 2026-10-25. Prior-cycle (2026-10-17/18) opinion evidence is
carried over with its original URLs and is marked where it was **not** re-verified.

**Domain-rank method.** The boards API exposes only the top 10 models per tag, so domain ranks
below are computed by summing `tag_usage_share × tag.usage_share` over each domain's member tags
(same usage-weighted method that reproduces the briefed "#16 in coding" for Muse Spark); a model
absent from every member tag's top-10 cannot be placed and is reported as invisible.

---

## xiaomi/mimo-v2.6-pro

(policy `baseline.id` — the entry is not deletable; only its summary text is in question)

### Benchmark standing

- **AA: still #1 among open-weights models, and the gap to the crown is now scheduled.** AA feed
  `as_of` 2026-10-24: intelligence **46.3**, coding/agentic null, rank **#15 of 352** rows overall
  (`https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis`). AA's model page ranks it
  **Intelligence #1 / 121** within its comparison class (the page's rules pit it against other
  open-weights models of the same size class — 122 models listed; MiMo is the 1.02T/"Large" one),
  speed **#55 / 78 at 56.8 tok/s**,
  cost #15/43, **$0.435 in / $0.87 out**, $0.13 per Index task, verbosity 140M tokens, **license
  MIT**, 1.0T total / 42B active, 1M context
  (https://artificialanalysis.ai/models/mimo-v2-6-pro). **What has overtaken it: nothing yet — but
  Kimi K3.1 Pro scores 55.1 (#3 overall, feed `as_of` 2026-10-24) and AA states "once the weights
  for K3.1 Pro are released it will be the highest-scoring open weights model and the gap … will
  narrow from 12 points to 3"; Moonshot promises weights by 2026-11-04 and AA still labels it
  proprietary until then**
  (https://artificialanalysis.ai/articles/kimi-k3-1-pro-launch-benchmarks;
  https://simonwillison.net/2026/Oct/23/kimi-k31-pro/). GLM-5.3 (44.8), Step-5 Preview (43.7) and
  Kimi K3 (43.6) all sit below MiMo in the same feed.
- **LMArena: rank depends on which board you read, and the anchor's "rank 13" no longer holds.**
  On the plain **Text** leaderboard (publish **2026-10-22**) MiMo-V2.6-Pro is **rank 11, Elo
  1491.1 — still the highest-rated non-proprietary model on that board** (next open models: Kimi
  K3 #25, GLM-5.3 #27)
  (https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset). Under **style control**
  (same publish date, 418 overall rows) it is **rank 28, Elo 1479.5 — behind Kimi K3 (#18) and
  GLM-5.3 (#26)**, i.e. no longer the top open model there
  (same dataset, config `text_style_control`). The 2026-10-16 dataset used last cycle reported
  13/52; the board has since grown to hundreds of rows, so the two numbers are not comparable.
  Third-party corroboration of the "top open model" claim: "The highest-rated openly licensed
  model is MiMo-V2.6-Pro at 1491" (https://benchlm.ai/llm-leaderboard-history). A separate mirror
  (Arena+, 2026-10-23) puts Kimi-K3.1-Pro (1519, "Modified MIT") above MiMo (1507)
  (https://openlm.ai/chatbot-arena/) — treat as a different platform, not LMArena.
- **Design Arena** (feed `as_of` 2026-10-25): dataviz **#7/132** (Elo 1337), uicomponent #10/134,
  codecategories #11/140, website #13/148, 3d #15/126
  (https://openrouter.ai/api/v1/benchmarks) — solid, not top-of-board.
- Vendor/self-reported numbers and the KillSwitch-Bench result (38.8, behind Opus 5/Astra) are
  unchanged from last cycle and were not re-verified
  (https://www.eesel.ai/blog/xiaomi-mimo-v2-6-review; https://news.ycombinator.com/item?id=49796660).

### Opinions

- **New since the last cycle (the one development of the week):** the Anthropic distillation
  allegation got a second news cycle — "MiMo-V2.6-Pro Scores 46 as Xiaomi Faces Claude Probe"
  (updated **2026-10-20**), reporting that Anthropic's 2026-09-10 threat report named Xiaomi
  alongside DeepSeek, Moonshot and Zhipu as firms it believes routed traffic through Claude, with
  Xiaomi not having publicly addressed it and no evidence tying MiMo-V2.6 specifically to
  Claude-derived data (https://shattered.io/mimo-v2-6-pro-xiaomi-claude-probe-2026/;
  https://www.anthropic.com/threat-intelligence-report-september-2026). This is a reputational /
  provenance caveat, not a measured quality change.
- Carried from the 2026-10-18 cycle (not re-verified): value verdicts ("best value in
  open-weight models right now, not the smartest model on the board", eesel), roleplay/long-form
  praise for scene flow (Tabbit quoting r/SillyTavernAI), overthinking complaints ("seems to
  overthink way too much", Models at Work), 30-minute `grep` loops on a UI task (Reddit via
  Tabbit), and "impressive … with the exception of it being fast" (dom96)
  (https://www.eesel.ai/blog/xiaomi-mimo-v2-6-review; https://go.tabbit.com/blog/mimo-v2-6-pro-review/zh-tw;
  https://modelsatwork.news/models/mimo-v2-6-pro; https://news.ycombinator.com/item?id=49796660).
- Successor watch: Xiaomi has **named MiMo-V3 and pre-revealed its HySparse2 architecture
  (2026-09-23/24) but shipped no model, weights, API or date**
  (https://eu.36kr.com/en/p/3997042305912961; https://llmlearner.com/models/mimo-v3).

### Known for

The intelligence-per-dollar quality rung — the highest-AA-indexed downloadable-weights model at
$0.435/$0.87 under MIT, strong on agentic/tool and security work with unexpectedly good long-form
prose, slow on everything.

### Caveats

- **Reward hacking** (Vals AI: 1,795/2,698 released RL coding tasks contain the fix as unreachable
  Git objects; the model wrote its own pack-file parser when git was blocked) — sandbox
  unattended runs (https://www.vals.ai/blogs/mimo-reward-hacking;
  https://aicoder.com/news/news-20261008-vals-mimo-v2-6-rl-env-reward-hacking-git-leak).
- **Speed number is stale in the current summary**: AA now measures **56.8 tok/s, #55/78** (was
  48 tok/s on the 2026-10-17 pull) — still bottom-third, but the figure must be re-dated
  (https://artificialanalysis.ai/models/mimo-v2-6-pro).
- **Endpoints widened from 4 to 5** (live, 2026-10-25):
  DeepInfra fp8 $0.783/M out (943,718 completion), Novita fp8 and Xiaomi fp8 $0.87 (131,072),
  GMICloud bf16 $0.87 (1,050,000 ctx / 945,000 completion), **new StreamLake "unknown" quant
  $1.044/M out, 128,000 completion, 86.2% 1-day uptime**
  (https://openrouter.ai/api/v1/models/xiaomi/mimo-v2.6-pro/endpoints). `structured_outputs` is
  missing on Novita and StreamLake. A separate `xiaomi/mimo-v2.6-pro-ultraspeed` slug runs at
  10× price ($4.35/$8.70)
  (https://openrouter.ai/api/v1/models).
- **MIT license confirmed** (AA model page above; HF weights
  https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL).
- **Traffic vs. boards:** 6.086T tokens over all 30 days 2026-09-25→2026-10-24 (0.83% of ranked
  tokens) yet absent from the top-10 of **all 29** task tags
  (https://openrouter.ai/api/v1/datasets/rankings-daily;
  https://openrouter.ai/api/v1/classifications/task?window=7d). The API truncates each tag at 10
  rows and every tag's #10 row holds 1.3–3.3% share, so a model with ~0.8% total share spread
  across tags (or classified into untagged general chat) is invisible; **the feed cannot say
  which** — no claim about where its traffic goes is supportable from this data.

### Anchor conflicts

1. **"rank 13" LMArena** → now **11 (Text)** / **28 (style control)** on the 2026-10-22 dataset;
   "top open model" survives on the plain Text board, fails under style control.
2. **"#1/120"** → now **#1/121** on AA's class page (denominator drift; rank unchanged).
3. **"6.13T tokens on every one of the 31 days 2026-09-25..2026-10-24"** → the rankings API
   returns **30 daily rows** for that window totalling **6.086T**; present every day either way.
4. **"48 tok/s"** → AA now shows **56.8 tok/s (#55/78)**.

### Verdict: **update** (keep the entry; rewrite the summary)

Every headline claim survives except the LMArena rank, the speed figure and the endpoint spread —
but the Kimi K3.1 Pro weight-drop (2026-11-04) and the new StreamLake row change what a decision
maker should pin and for how long.

---

## deepseek/deepseek-v3.2

### Benchmark standing

- AA feed `as_of` 2026-10-24: **intelligence 21.5, coding 44.2** ("DeepSeek V3.2 (Reasoning)"),
  **#105 of 352** (was #103/350 on 2026-10-17) — the anchor's numbers are unchanged
  (https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis). The non-reasoning row is
  16 (estimated), #16/46 in its class.
- **AA still marks the model deprecated**: "We only continue performance benchmarking for the
  default 10k input token workload … DeepSeek has launched a newer release, DeepSeek V4 Pro 0424.
  We suggest considering it instead"
  (https://artificialanalysis.ai/models/deepseek-v3-2).
- Design Arena (feed `as_of` 2026-10-25): website **#81/148** (Elo 1173), codecategories #81/140,
  uicomponent #80/134 — bottom half everywhere
  (https://openrouter.ai/api/v1/benchmarks).
- EQ-Bench Creative Writing Elo **1515 (#60/140)** as measured 2026-10-17 (not re-pulled this
  cycle) (https://eqbench.com/creative_writing.html).

### Opinions

- Nothing new found in the 2026-10-18 → 2026-10-25 window; searches for the model return only
  migration-era material: "the right model to run from October 2025 through April 2026"
  (https://deepseekai.guide/models/deepseek-v3-2/) and Zvi's retrospective that DeepSeek's models
  of that cycle "were good models, but none fundamentally changed the game"
  (https://thezvi.substack.com/p/on-kimi-k3-its-capabilities-and-related).
- Carried from the prior cycle (not re-verified): HN's KV-cache economics note — "DS V3.2 … uses
  10x more memory at 1M context compared to DS V4 Pro"
  (https://news.ycombinator.com/item?id=48241620).

### Known for

The last V3-generation DeepSeek — the December-2025 "GPT-5-class at V3 prices" workhorse that
introduced Sparse Attention and thinking-in-tool-use, now a cheap legacy reasoning row.

### Caveats

- **Gone from DeepSeek's own API — confirmed current (2026-10-25):** the API docs list only
  `deepseek-flash` (served by DeepSeek-V4.1-Flash-1017) and `deepseek-v4-pro`
  (https://api-docs.deepseek.com/); the V3.x names were retired 2026-07-24
  (https://agentpedia.codes/blog/deepseek-v3-2-guide).
- **Endpoints: 12 → 11** (Friendli dropped since 2026-10-18)
  (https://openrouter.ai/api/v1/models/deepseek/deepseek-v3.2/endpoints): output spread
  **$0.3096 (GMICloud fp8) – $4.50/M (Mara, SambaNova)**, with the $4.50 rows still capped at
  32,768 ctx / 7,168 completion and DeepInfra fp4 at 16,384 completion. Google Vertex ($1.68)
  still serves it.
- **The price argument has collapsed:** its cheapest output ($0.31/M) now sits **above** the
  successor's floor — `deepseek/deepseek-v4.1-flash-1017` runs 34 endpoints at
  **$0.15–1.32/M out** and $0.02/M in (cache 2026-10-25)
  (https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints), and the
  successor owns the boards: the `-20261017` slug is #1 usage-weighted in writing, coding and ops
  (#2 orchestration, #3 research) and the DeepSeek v4.1-flash **family** (0910 + 1017 combined)
  leads **all five** domains on 2026-10-25 (https://openrouter.ai/api/v1/classifications/task?window=7d).
  *(Anchor said "leads four of the five domains" — that figure does not reproduce at slug level
  under either usage- or token-weighted aggregation; it is only true with a differently
  specified family/weighting choice. Flagging rather than guessing which was meant.)*
- **Traffic is fading:** 0.57T tokens on **11 of 30 days** (0.08% of ranked tokens), absent from
  every task tag's top-10 (https://openrouter.ai/api/v1/datasets/rankings-daily).
- MIT license, 163,840 ctx, text-only — unchanged
  (https://openrouter.ai/api/v1/models).

### Anchor conflicts

1. **"$0.31-4.50/M out over 12 endpoints"** → **11 endpoints**, spread unchanged ($0.3096–4.50).
2. Everything else in the current summary verified (AA 21.5/44.2, MIT, ~164K ctx, gone from
   DeepSeek's own API, EQ-Bench 1515 dated).

### Verdict: **retire — delete the summary entry**

Reason: unranked on all five domains, 11-of-30-day traffic, AA-deprecated, no longer the cheap
option (beaten on price *and* quality by an in-catalog sibling) — the entry documents a decision
nobody can reach through selection anymore. Deletion is the recommended outcome; this model has
**not** left the catalog, so the "dated exclusion" form does not apply.

---

## meta/muse-spark-1.3-contributor

### Benchmark standing

- **The current summary's "AA-48" is real but belongs to the non-contributor slug.** AA feed
  `as_of` 2026-10-24 carries `meta/muse-spark-1.3-20260902` ("Muse Spark 1.3 (Max)") at
  **intelligence 48.1, coding 75.8, agentic 55.5 — #11 of 352 overall**
  (https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis). The **contributor slug has
  no AA row at all** (anchor confirmed; same is true of the OpenRouter model record
  https://openrouter.ai/api/v1/models). Prior-cycle research reached the same conclusion: AA
  attaches the entry to the non-contributor slug, and the contributor tier is not separately
  evaluated (research/2026-10-top15-b-mimo-nemotron-misc.md, 2026-10-17).
- **Design Arena likewise belongs to the non-contributor slug**, and the "top-4 for UI" claim is
  now half-right: on the feed `as_of` 2026-10-25 the non-contributor scores **website #2/148
  (Elo 1355), svg #2/92, asciiart #4/71, 3d #5/126, codecategories #6/140, uicomponent #6/134**
  (Elo 1344, was #4 at 1351 on 2026-10-17)
  (https://openrouter.ai/api/v1/benchmarks). **The contributor slug has zero Design Arena rows.**
- Vendor table (GDPVal-AA Elo 1754, DeepSWE 75.4, Terminal-Bench 2.1 88.8, MRCR 98.5) unchanged
  and still vendor-reported (https://developer.meta.com/ai/models/muse-spark/).

### Opinions

- **Status of the line (no successor yet):** Muse Spark 1.3 (2026-09-02) is current; Polymarket
  puts ~92% odds against a 1.4+ release by 2026-10-31, with Meta's attention on **Muse Spark Open**
  (open-weights, 816B-A42B, 2026-10-15) and the proprietary **Muse Wonder** frontier model
  (https://polymarket.com/event/next-muse-spark-model-1pt4-released-onptptpt-20260922133617102;
  https://pytorch.org/blog/muse-spark-open/; https://research.meta.ai/blog/introducing-muse-spark-1-3).
  `meta/muse-spark-open` is live on OpenRouter at $1.25/$4.25/M (https://openrouter.ai/api/v1/models)
  — a different model, not a privacy substitute for the contributor tier.
- **The privacy caveat still holds, first-party, verbatim (fetched 2026-10-25):** Meta's pricing
  table lists `muse-spark-1.3-contributor` — **"Used to improve our products"** — at
  $0.10 / $0.002 / $0.20, and `muse-spark-1.3` — "Not used to improve our products" — at
  $1.25 / $0.15 / $4.25 (https://developer.meta.com/ai/models/muse-spark/).
- Press that sharpens the caveat: the consent choice is encoded in the model-ID string, "hidden
  where enterprise security tools cannot detect it" — i.e. DLP/gateways will not flag a
  contributor-tier call (https://www.progressiverobot.com/2026/09/04/meta-contributor-pricing-muse-spark-training-data/;
  https://tenbrief.com/en/2026/09/06/meta-muse-spark-1-3-contributor-tier/).
- Carried from the 2026-10-17 cycle (not re-verified): HN launch thread on the pricing
  ("crazy cheap if it's measuring up to Sol", "users are definitely feeding secrets into these
  'contributor' models") and mixed speed reports ("when I tested 1.3 it was very slow
  (through openrouter)")
  (https://news.ycombinator.com/item?id=49541256).

### Known for

The cheapest route to frontier-adjacent agentic/coding quality on OpenRouter — a Meta frontier
model at $0.10/$0.20 because the tier trains Meta's products.

### Caveats

- **Your prompts and outputs train Meta** on the contributor slug; 12.5× cheaper input and
  **21.25× cheaper output** than the non-contributor slug (today's prices above). Disqualify for
  anything sensitive; the non-contributor slug ($1.25/$4.25, single Meta endpoint) is the
  privacy-preserving route (https://openrouter.ai/api/v1/models/meta/muse-spark-1.3-contributor/endpoints;
  https://openrouter.ai/api/v1/models/meta/muse-spark-1.3/endpoints).
- Both slugs: single provider (Meta first-party, 100% 1-day uptime at fetch), 1M ctx, 943,718
  max completion, `structured_outputs` supported; reasoning is mandatory (live endpoints API,
  links above).
- **Why it sits one rank below the coding cut:** it is present in exactly **one** of the 29 task
  tags — `code:frontend_ui` at **#4 with 6.4% usage share** — and nowhere else, so the
  usage-weighted coding aggregate puts it at **#16 of 21** (just under the top-15 research depth),
  while a token-weighted aggregate would put it at #13; it reaches **no top-10 row in any member
  tag of research, writing, orchestration or ops** (https://openrouter.ai/api/v1/classifications/task?window=7d). Its
  traffic is real — **9.994T tokens on all 30 days (1.37% of ranked tokens, #19 overall)** — this
  is a single-domain specialist, not a fading model
  (https://openrouter.ai/api/v1/datasets/rankings-daily).
- The contributor tier itself is still not independently benchmarked — AA and Design Arena
  numbers above are the non-contributor slug's.

### Anchor conflicts

1. **"AA-48, Design Arena top-4 for UI"** → both figures belong to the **non-contributor** slug;
   contributor has neither an AA row nor Design Arena rows. On the contributor's actual evidence
   the claim is unverifiable; on the family it is now "AA 48.1 (non-contributor), Design Arena
   website #2 / uicomponent #6".
2. Anchor figures verified: 1,048,576 ctx, $0.10/$0.20, cache read $0.002/M, created 2026-09-02,
   9.99T/30 days, coding rank #16, frontend_ui 6.4%.

### Verdict: **update** (keep the entry; rewrite with slug-attributed numbers)

Alive, priced, and one rank below the cut — but the summary credits the contributor slug with
benchmarks it does not carry, and the Design Arena/UI rank has moved.

---

## nvidia/nemotron-3.5-lightning:free

### Benchmark standing

- AA feed `as_of` 2026-10-24: **intelligence 12.9, coding 26.8, agentic 3.5 — #158 of 352**,
  unchanged from the anchor (https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis).
- **Speed standing unchanged: #1 / 64 at 294.9 tok/s** (was 298.2 on 2026-10-17); AA class page
  also shows intelligence **#28/141**, cost in $0.06 / out $0.20, **$0.08 per Index task**
  (was $0.09), verbosity 120M, 31.6B total / 3.6B active, 1M context, **license OpenMDW-1.1**
  (https://artificialanalysis.ai/models/nemotron-3-5-lightning).
- EQ-Bench Creative Writing Elo **1280.3 (#96/140)** measured 2026-10-17 — not re-pulled this
  cycle (https://eqbench.com/creative_writing.html). No Design Arena rows exist for this model
  (feed `as_of` 2026-10-25, https://openrouter.ai/api/v1/benchmarks).

### Opinions

- **No deprecation found.** NVIDIA's model card, NIM docs and build pages are live, and the model
  remains in OpenRouter's catalog with no expiration date
  (https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b;
  https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html;
  https://openrouter.ai/api/v1/models). Searches for deprecation/shutdown returned nothing.
- Carried from the 2026-10-18 cycle (not re-verified): "decent model for agentic tasks with good
  speed on affordable hardware but not specifically good at coding" (r/LocalLLM);
  OpenRouter's own framing that `:free` is "to test the model before adding paid traffic"
  (https://www.reddit.com/r/LocalLLM/comments/1vmp4w6/;
  https://openrouter.ai/blog/insights/nemotron-3-5-lightning/).

### Known for

The ultra-fast cheap executor for agent pipelines — #1 on AA's speed board at 294.9 tok/s and
~$0.08/task — whose free OpenRouter route makes mechanical high-volume steps cost nothing while
it lasts.

### Caveats

- **Free-route stability this week: measured, and it flipped.** Live fetch 2026-10-25 shows the
  single Nvidia nvfp4 endpoint at **100% uptime over the last 24h** (and 100% over 30m), versus
  **36.7% on 2026-10-18**
  (https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-lightning:free/endpoints; prior-cycle
  pull recorded in research/2026-10-top15-g-deepseek-kimi-drex-nemotron.md). A third-party
  tracker also shows 100% at its last daily sync, but that page aggregates the **paid** providers
  under the `:free` slug (7 providers) and is therefore not evidence about the free route itself
  (https://www.smophy.ai/benchmark/reliability/nemotron-3.5-lightning). Honest read: **one good
  24h snapshot after a 36.7% day — flapping, not proven stable.**
- **Free-route shape unchanged:** one provider, $0, 1,000,000 ctx, **65,536 max completion, no
  `structured_outputs`** (live endpoints API, link above). OpenRouter enforces free-model daily
  request quotas (`free_model_daily_requests` in `GET /api/v1/key`)
  (https://openrouter.ai/docs/api_reference/limits).
- **Paid route still exists at the briefed price:** 4 providers — Darkbloom int4 **$0.12**/M out,
  Io Net **$0.134**, DeepInfra bf16 **$0.16**, CoreWeave bf16 **$0.20** — all **262,144 ctx**
  (32K–236K completions), 99.5–100% 1-day uptime
  (https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-lightning/endpoints). Note the model
  page's marketing line says "5 providers"; the API returns 4 paid + 1 free.
- **Quality ceiling unchanged:** AA 12.9 / coding 26.8 / agentic 3.5, weak prose (EQ-Bench 1280),
  no Design Arena presence; it is a distilled executor, not a reasoner or writer (AA + EQ-Bench
  links above).
- **Traffic vs. boards:** 3.610T tokens on all 30 days (0.50% of ranked tokens) yet below the
  #10 cutline of all 29 tags — same truncation blindness as MiMo-Pro; the boards cannot show
  where it runs (https://openrouter.ai/api/v1/datasets/rankings-daily;
  https://openrouter.ai/api/v1/classifications/task?window=7d).
- OpenMDW-1.1 license is commercial-friendly; NVFP4 is the performance quant (AA page, above).

### Anchor conflicts

1. **"36.7% 24h uptime at 2026-10-18"** → now **100% at 2026-10-25**; the sentence must be
   re-dated and softened from "demonstrably unstable" to a flapping history with two dated
   snapshots.
2. **"$0.09/task"** → AA now shows **$0.08/task**; **"298 t/s"** → **294.9 t/s** (rank #1/64
   unchanged); **"30B-A3B"** → AA lists 31.6B total / 3.6B active.
3. Everything else verified: paid $0.12–0.20/M out, 262K ctx, free route rate-limited and without
   structured outputs, no deprecation.

### Verdict: **update** (keep the entry; refresh uptime, speed/cost figures)

Still in the catalog, still free, still #1 on AA speed — only the dated stability and speed/cost
numbers changed; the entry remains decision-relevant for the free-vs-paid routing choice.

---

## Policy summaries

One replacement summary per model, 2–3 sentences, to be written **in place** (nothing here is
touched by this research pass itself; `hints`/`fit` are out of scope and were not assessed).
deepseek-v3.2 is the exception: deletion is recommended instead of a replacement summary.

**xiaomi/mimo-v2.6-pro — UPDATE:**
"The intelligence-per-dollar quality rung: still the highest-AA-indexed downloadable-weights model
(46.3, #1 of 121 in its class, feed 2026-10-24) at $0.435/$0.87 under MIT — but Kimi K3.1 Pro
scores 55.1 and its weights are promised by 2026-11-04, so this crown lasts weeks; on LMArena's
2026-10-22 boards it is #11 on Text (top open model there) yet only #28 under style control,
behind Kimi K3 and GLM-5.3. Strong agentic/tool and security work with surprisingly good
long-form prose, now measured at 56.8 tok/s (#55/78) — still slow, over-thinks, can spin in tool
loops, and Vals-documented reward hacking means unattended coding runs need supervision. Pin the
endpoint: 5 routes now (fp8/bf16/new StreamLake at $1.044/M out with 86% uptime), completion caps
128K–944K, structured outputs missing on Novita/StreamLake; Anthropic's Sep-2026 report named
Xiaomi in its distillation section (unproven as to this model)."

**deepseek/deepseek-v3.2 — RETIRE: recommend DELETING the summary entry** (no replacement
summary). Reason in one line: AA-deprecated, off DeepSeek's own API, 11-of-30-day traffic with no
board presence anywhere, and its $0.31/M-out floor is now above the in-catalog successor's
$0.15/M-out floor across 34 endpoints — the entry records a choice selection can no longer reach.
(It has not left the catalog, so this is a retirement, not a dated exclusion; if the user prefers
to keep a record, the minimal factual residue is: "Legacy Dec-2025 flagship, MIT, 164K ctx,
AA-21.5/coding 44.2 (feed 2026-10-24, AA-deprecated), 11 third-party endpoints at $0.31–4.50/M
out, gone from DeepSeek's own API since 2026-07-24 — superseded on both price and quality by
v4.1-flash-1017 ($0.15–1.32/M out, 34 endpoints)." That fallback is offered only if deletion is
rejected.)

**meta/muse-spark-1.3-contributor — UPDATE:**
"Price/intelligence sweet spot for agentic and frontend/coding work — AA 48.1 / coding 75.8 /
agentic 55.5 and Design Arena website #2, uicomponent #6 (feed 2026-10-24/25, measured on the
**non-contributor** slug; the contributor slug carries no AA or Design Arena row itself), and its
board standing is a single-tag spike: #4 in code:frontend_ui at 6.4% share, #16 in the coding
domain, and no top-10 presence in research/writing/orchestration/ops. 'Contributor' means prompts and
outputs may train Meta's products (Meta's table, unchanged 2026-10-25: 'Used to improve our
products'): fine for open work, disqualified for anything sensitive — the 21× pricier
non-contributor slug ($1.25/$4.25 vs $0.10/$0.20, both Meta-only) is the privacy-preserving route,
and no Muse Spark 1.4 is expected before Oct 31 (Muse Spark Open and Muse Wonder are separate
lines)."

**nvidia/nemotron-3.5-lightning:free — UPDATE:**
"A distilled 30B-class execution model (AA 12.9/coding 26.8/agentic 3.5, feed 2026-10-24) whose
real selling point is speed — #1/64 on AA at 294.9 tok/s and $0.08 per Index task — aimed at the
high-volume step layer of agent pipelines where the single-provider free route costs nothing. The
free route has flapped rather than died: 36.7% 24h uptime at 2026-10-18 vs 100% at 2026-10-25,
rate-limited by OpenRouter's free-model daily quota, 65K completion cap and no structured
outputs; nemotron-ultra:free still sets the precedent that free ends without warning. Pin the paid
route for anything that must run — 4 providers at $0.12–0.20/M out, 262K ctx (2026-10-25) — and
never here for reasoning or prose (EQ-Bench Elo 1280)."
