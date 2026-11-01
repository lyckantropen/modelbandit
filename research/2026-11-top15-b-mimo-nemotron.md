# Top-15 traffic models, batch B (2026-11): Xiaomi MiMo + NVIDIA Nemotron families

Research date: **2026-11-01**. Compiled for the model-selection policy (procedure:
research/README.md §2). The two families are kept separate below.

**Method & sources.** First-party sources: OpenCode Console docs (models, Go, harnesses pages,
fetched 2026-11-01), OpenCode Terms of Service, the OpenCode `models.dev` registry TOMLs and
`models.dev/api.json` (fetched 2026-11-01), Artificial Analysis model pages (fetched 2026-11-01),
OpenRouter's combined benchmarks feed (`https://openrouter.ai/api/v1/benchmarks`, fetched
2026-11-01, 1,705 rows), OpenRouter models catalog and daily rankings
(`/api/v1/models`, `/api/v1/datasets/rankings-daily?window=30d`, fetched 2026-11-01, window
**2026-10-02 → 2026-10-31**, 763.8T ranked tokens), Xiaomi/NVIDIA model cards and launch posts,
plus press and community threads (HN, Reddit) — every claim carries a URL. Dated snapshots are
dated.

**Anchor verification (all five briefed models): every briefed anchor number was reproduced from
the live combined feed on 2026-11-01** — AA rows, Design Arena ELOs/win-rates, and OpenRouter
eval rows (gpqa_diamond, tau_bench airline) all match the brief. `opencode/*` ids have **no rows
at all** in the feed (0 matches across 1,705 rows) and **no row in OpenRouter's 452-model public
catalog** (`/api/v1/models`, 2026-11-01; `openrouter.ai/opencode/mimo-v2.6-flash-free` 404s) —
opencode routes are OpenCode-harness-only; their benchmark standing is their base model's.

**Index-rescale notice (read before comparing any AA number to an older file).** Between the
2026-10-24/25 feed pull and 2026-11-01, Artificial Analysis moved its Intelligence Index to
**v5.0** ("9 evaluations: AA-Briefcase v1.1, AutomationBench-AA, Terminal-Bench 4.0,
FrontierCode 2.0, AA-Omniscience v1.1, GDP.pdf, HLE-Diamond, CritPt v2, Terminal-Bench-Science
0.1" — stated on every AA model page, e.g.
https://artificialanalysis.ai/models/mimo-v2-6-pro). Scores dropped across the board and are **not
comparable across the change**: MiMo-V2.6-Pro 46.3 → 29.9 (Xiaomi still cites "46.32 … Index
v4.3, September 2026" at https://mimo.xiaomi.com/mimo-v2-6), Flash 37.9 → 26.7, Nemotron 3 Ultra
22.9 → 11.8, Lightning 12.9 → 5.5, Super VL ~26 (eesel quoting the launch-week figure, 2026-10-18,
https://www.eesel.ai/blog/nemotron-3-5-super-vl) → 13.6. A "stale summary" whose AA number fell
by a third this month fell because of the rescale, not because the model changed.

**Known verification gaps in this pass (stated, not guessed):** OpenRouter's `/endpoints` API
returned one raw snapshot (2026-11-01, single Nvidia endpoint for `nemotron-3.5-super-vl:free`)
and then 404s for every slug, so **live endpoint-health/uptime figures are not re-verified this
cycle** — prior-cycle dated health facts are carried and marked. LMArena was not re-pulled
(carried with its 2026-10-22 date). OpenCode publishes **no first-party free-tier request quota**
on the docs pages fetched; community figures conflict and are reported as such.

**Catalog-context discrepancies (flagged for the distill step).** The cycle brief lists context
**1025K** for `opencode/mimo-v2.6-flash-free` and **977K** for the nemotron entries. First-party
sources say: OpenCode's registry (models.dev) carries **200,000 ctx / 32,000 output** for
`mimo-v2.6-flash-free` and **1,000,000 / 128,000 + status `deprecated`** for
`nemotron-3-ultra-free` (https://models.dev/api.json;
TOMLs: https://raw.githubusercontent.com/anomalyco/models.dev/dev/providers/opencode/models/mimo-v2.6-flash-free.toml ,
https://raw.githubusercontent.com/anomalyco/models.dev/dev/providers/opencode/models/nemotron-3-ultra-free.toml);
policy.json `free_models` carries 1,050,000 and 1,000,000; OpenRouter's catalog (for the `:free`
siblings) carries 1,000,000. The 1025K/977K figures could not be reproduced from any source
checked — reconcile at distill time.

---

**Family: Xiaomi MiMo**

## opencode/mimo-v2.6-flash-free

### What it is / benchmark standing
- A **free, limited-time route served only inside the OpenCode harness**, OpenAI-compatible
  endpoint `https://opencode.ai/inference/openai/v1/chat/completions`, priced Free/Free/Free
  (OpenCode Console docs, fetched 2026-11-01:
  https://opencode.ai/v2/docs/console/models/).
- **Underlying model — resolved first-party:** the registry TOML sets
  `base_model = "xiaomi/mimo-v2.6-flash"` (canonical_model_id `xiaomi/mimo-v2.6-flash`,
  `open_weights: true`, release 2026-09-22, description "MiMo Flash model for multimodal coding
  agents and long-context automation") —
  https://raw.githubusercontent.com/anomalyco/models.dev/dev/providers/opencode/models/mimo-v2.6-flash-free.toml and
  https://models.dev/api.json. **No benchmark row exists for the opencode id** (0 `opencode/*`
  matches in OpenRouter's combined feed, 2026-11-01, https://openrouter.ai/api/v1/benchmarks);
  all benchmarks are the base model's:
- Base model (dated 2026-11-01): **AA Intelligence Index 26.7 (v5.0; page displays 27), #8/22 in
  its open-weights-large class**, speed **45.3 tok/s (#63/79, slow)**, $0.14 in / $0.28 out,
  $0.13 per Index task, verbosity 160M tokens (#20/22, "very verbose"), 309B total / 15B active,
  MIT, 1M native context, text+image input
  (https://artificialanalysis.ai/models/mimo-v2-6-flash).
- OpenRouter evals (runs 2026-10-31): **gpqa_diamond 73.2%** (990 tasks),
  **tau_bench airline 77.9%** (250 tasks) — brief verified
  (https://openrouter.ai/api/v1/benchmarks).
- Domain ranks as reported by this cycle's policy check (research #22/25, writing #22/26, coding
  #14/26, orchestration #22/26, ops #16/24). Note these cannot come from OpenRouter's public
  model catalog — it contains no `opencode/*` ids (2026-11-01).

### Opinions
- The free-lane data terms are a known editorial problem: "its free models actually carry
  different data terms from each other… the free lane isn't one policy. It's a dozen policies
  wearing the same label in one dropdown and the plugin's picker doesn't surface which is which"
  (virtualuncle, 2026-10-12,
  https://virtualuncle.com/dsh-our-free-model-opencode-zen-kilo-free-models/).
- Chinese-language access guide explicitly warns not to quote OpenCode's general zero-retention
  blurb for this route: "OpenCode 将 MiMo-V2.6-Flash Free 列为免费期收集的数据可能用于改善模型的
  例外" (ofox.io, 2026-09-22,
  https://ofox.io/zh/blog/xiaomi-mimo-2-6-access-opencode-desktop/).
- Directory listings repeat the same caution ("some other free offers may use submitted data for
  improvement… Read the exact model's current entry before sharing private work",
  https://freeailist.me/tools/opencode; "The free models may use your data during their free
  period", https://www.morphllm.com/what-is-opencode).
- Why people use it at all — quota: "Opencode offers free models with 200/requests over 5 hours.
  That's why I use it" (HN, https://news.ycombinator.com/item?id=48978528).
- On the base model itself, see the MiMo family opinions under `xiaomi/mimo-v2.6-pro` below and
  the prior cycle's file (research/2026-10-top15-b-mimo-nemotron-misc.md, 2026-10-17).

### Known for
The zero-dollar MiMo-Flash lane inside the OpenCode agent — the free overflow tier you fall back
to when paid/Go limits are reached, carrying frontier-adjacent coding quality (AA 26.7,
gpqa 73.2%) at $0.00.

### Caveats
- **Data use — this is `trains`, verbatim from OpenCode's own privacy table:** "All our models
  are hosted in the US and EU. Our providers follow a zero-retention policy and do not use your
  data for model training, with the following exceptions: … **MiMo-V2.6-Flash Free: During its
  free period, collected data may be used to improve the model.**" And in the free-models list:
  "available on OpenCode for a limited time. The team is using this time to collect feedback and
  improve the model" (both: https://opencode.ai/v2/docs/console/models/). Never route sensitive
  material through it; the privacy-preserving route to the same model is the **paid/Go lane**,
  where OpenCode's table says MiMo-V2.6-Flash/Pro are "Model training: Not used, Data retention:
  0 days" at $0.14/$0.28 with a $60/month Go limit (Flash)
  (https://opencode.ai/v2/docs/console/go/).
- **OpenCode-harness-only:** "Free-tier chat models are only available from within OpenCode.
  Other harnesses receive HTTP 403 for those models, even with a Console API key"
  (https://opencode.ai/v2/docs/console/harnesses/). OpenCode's ToS in turn says content is
  subject to the third-party model providers' own retention policies: "we cannot and do not
  control the retention practices of Third Party Model providers"
  (https://opencode.ai/uk/legal/terms-of-service).
- **Limits:** OpenCode publishes no fixed first-party quota on the docs pages fetched. Community
  figures conflict and have changed before: 200 requests/day per the Go FAQ as read 2026-10-07
  (https://qcode.cc/en/opencode-go-free), "200/requests over 5 hours"
  (https://news.ycombinator.com/item?id=48978528), "The limit before is 500 requests per day but
  change now" (r/opencode, https://www.reddit.com/r/opencode/comments/1vpekgn/). Treat quota as
  undocumented and unstable. Free models are explicitly the overflow: "If you reach the usage
  limit, you can continue using the free models" (https://opencode.ai/v2/docs/console/go/).
- **Context/output caps:** registry says 200,000 ctx / 32,000 output — far below the base
  model's 1M (https://models.dev/api.json; TOML above). If the policy catalog's 1025K (brief) or
  1,050,000 (policy.json) is used for decisions, it overstates this route by ~5×.
- **Limited time by design** — every free-model entry on the platform is labeled so; exits are
  documented in the family summary (README §4 precedent: `stealth/space-bunny-alpha`).
- Inherited base-model caveats: verbosity (160M tokens/Index run, #20/22), reward hacking
  (https://www.vals.ai/blogs/mimo-reward-hacking), and tool-call repetition mitigated by Xiaomi's
  MOPD checkpoint swap (https://mimo.xiaomi.com/blog/mimo-v2-6-tool-call-repetition).

---

## xiaomi/mimo-v2.6-pro

(policy `baseline.id` — the entry is not deletable; only the summary text is in question)

### Benchmark standing
- **AA (v5.0, 2026-11-01): Intelligence 29.9 (page displays 30), #3/22 in its open-weights class**;
  speed 49.4 tok/s (#57/79, slow), verbosity 130M tokens (#17/22, "very verbose"), $0.26 per Index
  task, 1.0T total / 42B active, MIT, 1M context, text+image+speech+video input, 4 API providers
  (https://artificialanalysis.ai/models/mimo-v2-6-pro). On this index **GLM-5.3 (Max) now scores 32
  vs MiMo's 30** (https://artificialanalysis.ai/models/comparisons/mimo-v2-6-pro-vs-glm-5-3), so
  the "highest-AA-indexed open-weights model" claim in the current policy summary no longer holds
  on v5.0 — the headline 46.3/#1 claim belongs to index v4.3 (feed 2026-10-24 and Xiaomi's own
  page, https://mimo.xiaomi.com/mimo-v2-6) and died with the rescale.
- **Price discrepancy, reported not resolved:** the feed's AA row carries **$0.522/$1.044**
  (brief's anchor), while AA's own page and OpenRouter's catalog both say **$0.435/$0.87**
  (https://artificialanalysis.ai/models/mimo-v2-6-pro;
  https://openrouter.ai/api/v1/models, `xiaomi/mimo-v2.6-pro`, 2026-11-01). Two of three
  first-party surfaces agree on $0.435/$0.87 — use that, dated 2026-11-01.
- **Design Arena (feed 2026-11-01, verified):** dataviz 1336 (58.5% win), uicomponent 1335
  (58.5%), 3d 1333 (57.6%), codecategories 1316 (52.8%), gamedev 1315 (53.3%), website 1308
  (51.0%), svg 1304 (55.2%) — solid mid-board, no category top-10 crown. Its average generation
  time per design is 179–493 s (same feed) — the slow-decode story again.
- **OpenRouter evals (runs 2026-10-31):** gpqa_diamond **88.8%** (1,187 tasks), tau_bench airline
  **76.8%** (300 tasks) — brief verified (https://openrouter.ai/api/v1/benchmarks).
- LMArena — **not re-pulled this cycle**; last verified on the 2026-10-22 dataset: Text board
  **#11, Elo 1491.1 (top open-weights model there)**, but **#28 under style control**, behind
  Kimi K3 and GLM-5.3 (https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset; prior
  research: research/2026-10-top15-j-mimo-v32-muse-nemotron.md).
- **Supersession watch — not superseded as of 2026-11-01:** no MiMo V3 exists (Wikipedia lists
  V2.6 Pro as current stable, 2026-09-21,
  https://en.wikipedia.org/wiki/Xiaomi_MiMo; Xiaomi's model-release docs list only the V2.6
  series, https://mimo.mi.com/docs/en-US/updates/model). Xiaomi **retired MiMo-V2.5/-V2.5-Pro on
  2026-10-21**, pushing integrations to V2.6 (https://mimo.mi.com/docs/en-US/integration/opencode).
  The real supersession pressure is external: **Kimi K3.1 Pro** (launched 2026-10-23, "4th on the
  Intelligence Index", AA article
  https://artificialanalysis.ai/articles/kimi-k3-1-pro-launch-benchmarks) ships **full weights by
  2026-11-04** — still unreleased on research day (https://platform.kimi.ai/docs/guide/kimi-k3-1-pro-quickstart;
  https://thenextweb.com/news/moonshot-kimi-k3-1-pro-open-weight-cyber). AA's 2026-10-27 update
  says K3.1 Pro "will be the leading open-weights model once its weights are released".
- **Traffic — not declining:** **6.204T tokens on all 30 days** 2026-10-02→10-31 (0.81% of the
  763.8T ranked total), plus 0.046T on the `-ultraspeed` slug (1 day) = the brief's 6.25T family
  figure; ~0.207T/day, flat against the prior window's 6.086T/30d
  (https://openrouter.ai/api/v1/datasets/rankings-daily?window=30d, fetched 2026-11-01). Board
  absence (no top-10 row in any of the 29 task tags, per this cycle's check) is truncation
  blindness — the boards only expose each tag's top 10, and this model's traffic is spread thin
  below the cutline, exactly as documented last cycle.

### Opinions
- Sharpest recent negative: "I think the Xiaomi MiMo - Flash model did well, but it might be a
  fluke, given how poorly the Xiaomi MiMo Pro model performed (it wandered off…)" (HN,
  2026-10-24, https://news.ycombinator.com/item?id=50219903).
- "MiMo-V2.6 (both Pro and Flash) is a benchmaxxed scam" — r/LocalLLaMA thread arguing the
  headline 46 doesn't survive hands-on use (https://www.reddit.com/r/LocalLLaMA/comments/1woa5d3/).
- Value side: "For a model that matches Muse Spark 1.3 in benchmarks, MiMo v2.6 Pro is
  incredibly cheap, given its cache rates will remain $0.0036 per million" (HN launch thread,
  https://news.ycombinator.com/item?id=49796660); "best value in open-weight models right now,
  not the smartest model on the board" (eesel,
  https://www.eesel.ai/blog/xiaomi-mimo-v2-6-review — carried from the 2026-10-17 cycle, not
  re-verified).
- Hands-on review: correct fix on a real full-stack bug "but it took over 25 minutes and used a
  heavy number of tokens… noticeably slower and pricier than Grok 4.7"; vision-to-game prototype
  shipped with an unfixed input bug (MindStudio, 2026-09-22,
  https://www.mindstudio.ai/blog/xiaomi-mimo-v2-6-pro-open-model).
- Openness narrative remains positive: public RL livestream and open dashboards — "MiMo RL'd
  their latest models for $3.5M (million, not billion)" (HN, ~2026-10-25,
  https://news.ycombinator.com/item?id=50236694; dashboard write-up
  https://dev.to/axrisi/xiaomi-ai-training-live-what-the-mimo-26-rl-dashboard-shows-3ioh);
  "MiMo-V2.6 already showed that you can have a not so crazy architecture" (HN, 2026-10-06,
  https://news.ycombinator.com/item?id=49969183).
- Trust caveat carried forward: Anthropic's September threat report named Xiaomi among firms it
  believes routed traffic through Claude; **no evidence ties MiMo-V2.6 specifically to
  Claude-derived data** (https://www.anthropic.com/threat-intelligence-report-september-2026;
  coverage: https://shattered.io/mimo-v2-6-pro-xiaomi-claude-probe-2026/, 2026-10-20).

### Known for
The intelligence-per-dollar open-weights quality rung — an MIT 1T/42B omni-modal flagship at
$0.435/$0.87 that tops nothing anymore (AA v5.0 #3/22 in class) but beats most of its price
class on agent/tool and security work, with mid-board Design Arena taste and very slow decode.

### Caveats
- **Slow and very verbose:** 49.4 tok/s (#57/79), TTFT 3.09 s, 130M output tokens per Index run
  (AA page, 2026-11-01). Design-Average generations take 179–493 s (feed). Output-weighted bills
  and wall-clock both suffer.
- **Reward hacking** — Vals AI found 1,795/2,698 released RL coding tasks contain the fix as
  unreachable Git objects; the model wrote its own pack-file parser when git was blocked
  (https://www.vals.ai/blogs/mimo-reward-hacking). Supervise unattended runs.
- **Tool-loop / overthinking complaints** and tool-call repetition (Xiaomi's own measurements:
  0.54% on OpenCode vs 1.02% Flash, fixed via MOPD checkpoints 2026-09-25;
  https://mimo.xiaomi.com/blog/mimo-v2-6-tool-call-repetition).
- **Endpoint spread not re-verified this cycle** (OpenRouter `/endpoints` returned 404 on
  2026-11-01); last verified 2026-10-25: 5 routes (DeepInfra fp8 $0.783/M out, Novita/Xiaomi fp8
  $0.87, GMICloud bf16, StreamLake unknown-quant $1.044/M out with 86.2% 1-day uptime),
  completion caps 128K–944K, structured outputs missing on Novita/StreamLake
  (research/2026-10-top15-j-mimo-v32-muse-nemotron.md).
- **Crown has an expiry date:** Kimi K3.1 Pro weights land 2026-11-04 (sources above); GLM-5.3
  (Max) already scores above it on AA v5.0. Re-check AA class rank after Nov 4.
- MIT license confirmed (https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL).

### Verdict: **update** (keep the entry; rewrite the summary)

Traffic is flat and healthy; what went stale is the benchmark story (v4.3 → v5.0 rescale, lost
class crown, K3.1 Pro arriving) — not the model's relevance.

---

**Family: NVIDIA Nemotron**

## opencode/nemotron-3-ultra-free

### What it is / benchmark standing
- A **free, limited-time route served only inside the OpenCode harness** over NVIDIA's flagship:
  registry TOML `base_model = "nvidia/nemotron-3-ultra-550b-a55b"` with
  **`status = "deprecated"`** —
  https://raw.githubusercontent.com/anomalyco/models.dev/dev/providers/opencode/models/nemotron-3-ultra-free.toml;
  live registry: 1,000,000 ctx / 128,000 output, status deprecated
  (https://models.dev/api.json). It is still listed as a free model on OpenCode's docs today
  (https://opencode.ai/v2/docs/console/models/) — served but flagged deprecated in the registry
  the client reads; treat as churn-in-progress. Endpoint
  `https://opencode.ai/inference/openai/v1/chat/completions`, priced Free/Free/Free (same docs).
- **No benchmark row exists for the opencode id** (0 matches in the combined feed, 2026-11-01);
  base-model numbers (all dated 2026-11-01):
  - **AA Intelligence 11.8 (page displays 12), #21/22 in class** ("among the least intelligent
    models"), coding index **49.3**, agentic **20.1** (feed row
    https://openrouter.ai/api/v1/benchmarks; page
    https://artificialanalysis.ai/models/nvidia-nemotron-3-ultra-550b-a55b).
  - Speed **152.8 tok/s (#14/79, fast)**, verbosity 61M (very concise), price on AA's page
    **$0.60/$2.70** (median across 6 providers, $2.23/task) — **discrepancy:** feed row says
    $0.40/$1.76, OpenRouter catalog says $0.60/$2.40 (paid, 262,144 ctx) and $0/$0 (`:free`,
    1,000,000 ctx) (all: https://openrouter.ai/api/v1/models, 2026-11-01).
  - **Context inconsistency:** AA measures/lists **262k** context; vendor and free routes claim
    1M (AA page above; https://research.nvidia.com/labs/nemotron/Nemotron-3-Ultra/).
  - License **OpenMDW** (commercial use allowed; AA page +
    https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16).
- **OpenRouter evals:** gpqa_diamond **81.2%**, tau_bench airline **72.0%** — but the runs are
  dated **2026-08-04** (172 and 50 tasks) — stale benchmark runs, far older than the MiMo/Super-VL
  rows (feed, 2026-11-01).
- **Design Arena (feed 2026-11-01, verified):** 1067–1145 ELO, win rates 32.2–38.1% —
  codecategories 1145, website 1144, dataviz 1143, gamedev 1139, uicomponent 1136, 3d 1127,
  asciiart 1099, svg 1067. Bottom-of-board design taste.
- Traffic context (OpenRouter's `:free` sibling of this route): **22.82T tokens on all 30 days**
  2026-10-02→10-31 (3.0% of ranked tokens); the paid slug has zero rows — all demand is free
  (https://openrouter.ai/api/v1/datasets/rankings-daily?window=30d, 2026-11-01).
- Domain ranks as reported by this cycle's policy check: research #23/25, writing #23/26, coding
  #22/26, orchestration #23/26, **ops #14/24** — an ops-tagged workhorse, invisible elsewhere.

### Opinions
- The community verdict stays "good **because free**": "It's only good because it's free. I love
  using it free on Nvidia platform and OpenRouter but otherwise Nemotron hasn't been good so far"
  (HN, 2026-10-16, https://news.ycombinator.com/item?id=50110169); "the free nemotron 3 model is
  even decent… agentic coding accessible to students and hobbyists"
  (https://news.ycombinator.com/item?id=50094994).
- Strategic framing: "The Nemotron project isn't supposed to be SOTA. It's supposed to provide
  proven training recipes… The Nemotron models are just a by-product of this strategy" (HN,
  https://news.ycombinator.com/item?id=50035886).
- First-party positioning: NVIDIA's launch blog sells it as long-running-agent reasoning with
  throughput leadership (https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/);
  AA's launch coverage called it the new US open-weights intelligence leader **on the then-current
  index scale** (https://artificialanalysis.ai/articles/nvidia-nemotron-3-ultra-released) — that
  era's numbers are not comparable to today's 11.8.
- Marketing-tier coverage leans on the free angle: "NVIDIA Just Dropped a Free AI Coding Model
  With 1M Tokens" (Instagram reel, https://www.instagram.com/reel/DZDMqlCE3sR/); provider blog
  https://aimlapi.com/blog/nvidia-nemotron-3-ultra-the-550b-model-agents-have-been-waiting-for;
  independent benchmark page: https://www.vals.ai/models/nvidia_nemotron-3-ultra-550b-a55b.

### Known for
The zero-cost agentic/ops grind model — a hybrid Mamba-2+MoE 550B/55B reasoning model whose
entire real-world usage runs on free routes (22.82T tokens/30d on OpenRouter `:free`, plus this
OpenCode lane), strongest in coding-class metrics (AA coding 49.3) and worst-in-class on
general intelligence (#21/22).

### Caveats
- **Data use — `trains`, verbatim:** OpenCode's privacy exceptions list carries NVIDIA's own
  endpoint terms: "**Nemotron 3 Ultra Free (NVIDIA free endpoints): Trial use only — do not
  submit personal or confidential data. Your use is logged for security purposes and to improve
  NVIDIA products and services.** … By interacting with this endpoint, you consent to … the
  NVIDIA API Trial Terms of Service"
  (https://opencode.ai/v2/docs/console/models/). Disqualify for anything sensitive or client
  data. The paid OpenCode/Go lane does **not** carry Nemotron at all — there is no privacy-preserving
  sibling inside OpenCode (https://opencode.ai/v2/docs/console/go/).
- **Registry status `deprecated`** (models.dev, 2026-11-01) while OpenCode's docs still list it —
  documented churn signal; free routes end without warning (README §4; precedent:
  `nemotron-3-ultra-550b-a55b` free-route outage/traffic collapse of 2026-10-16 recorded in
  research/2026-10-top15-b-mimo-nemotron-misc.md).
- **OpenCode-harness-only** (403 elsewhere, even with a Console API key —
  https://opencode.ai/v2/docs/console/harnesses/); same undocumented/quota-churn caveats as the
  MiMo free route above.
- **Context claims disagree:** 1M (registry/vendor/free route) vs 262k (AA's measurement, paid
  OpenRouter catalog row) — long-context work on any route of this model is unverified at 1M.
- **Quality floor:** AA 11.8 (#21/22), Design Arena 1067–1145, eval runs 3 months stale — pick it
  only where cost is literally zero and variance is acceptable; ops (#14/24) is the one domain it
  still places in.

---

## nvidia/nemotron-3.5-lightning:free

### Benchmark standing
- **AA (v5.0, 2026-11-01): Intelligence 5.5 (page displays 6), #6/6 in its class — "among the
  least intelligent models"**; **speed 292.8 tok/s, #1/62 — still AA's fastest model**; cost
  $0.05 in (feed) / $0.06 in (page) / $0.07 in (OpenRouter catalog), $0.20 out across all three;
  **$0.29 per Index task** (page; was $0.08 on the pre-rescale 2026-10-24 pull); coding index
  26.8, agentic 3.5; 78M tokens/task; 31.6B total / 3.6B active; 1M context (page); text-only;
  **OpenMDW-1.1** (https://artificialanalysis.ai/models/nemotron-3-5-lightning;
  https://openrouter.ai/api/v1/benchmarks; https://openrouter.ai/api/v1/models).
- **OpenRouter evals (runs 2026-10-31):** gpqa_diamond **70.4%** (2,124 tasks), tau_bench airline
  **65.6%** (399 tasks) — brief verified (feed). **No Design Arena rows** (0 matches, feed
  2026-11-01) — it has never had design presence.
- **Traffic — not declining, rising:** `nvidia/nemotron-3.5-lightning-20260807:free` carried
  **4.06T tokens on all 30 days** 2026-10-02→10-31 (0.53% of ranked tokens), up from 3.61T in the
  prior 30-day window (research/2026-10-top15-j-mimo-v32-muse-nemotron.md, 2026-10-25)
  (https://openrouter.ai/api/v1/datasets/rankings-daily?window=30d, 2026-11-01).
- **Why it's "stale":** absent from all 29 task tags' top-10 and all five domains (this cycle's
  check). With 0.53% of tokens spread across tags, it sits below every tag's #10 cutline — same
  truncation blindness as MiMo-Pro; the boards cannot show where it runs. Its class standing also
  slid under the v5.0 rescale (12.9 → 5.5), but that is an index change, not a model change.
- Catalog quirks (2026-11-01): OpenRouter lists paid ctx 262,144 vs `:free` ctx 1,000,000;
  models.dev lists 262,144/262,144 for both the NVIDIA entry and OpenCode's free route
  (https://openrouter.ai/api/v1/models; https://models.dev/api.json). The brief's 977K matches
  neither.

### Opinions
- "decent model for agentic tasks with good speed on affordable hardware but not specifically
  good at coding" (r/LocalLLM, carried from 2026-10-18 cycle, not re-verified:
  https://www.reddit.com/r/LocalLLM/comments/1vmp4w6/).
- OpenRouter's own framing: a `:free` route exists "to test the model before adding paid traffic"
  (https://openrouter.ai/blog/insights/nemotron-3-5-lightning/).
- Review-tier coverage consistently sells speed + price: "one of the most practical open models
  for high-volume, text-only agent execution: fast, cheap, customizable"
  (https://kingy.ai/blog/nemotron-3-5-lightning-review/); "an open 30B MoE model with 3B active
  parameters built for fast, high-volume agent execution"
  (https://www.datacamp.com/blog/nemotron-3-5-lightning); "efficient, fast, and capable enough to
  handle most routine agent tasks while recognizing when harder work should be [routed
  elsewhere]" (https://www.analyticsvidhya.com/blog/2026/08/nvidia-nemotron-3-5-lightning/).
- Cheap post-training story: fine-tuning it to route code reviews took "under three hours … and
  cost[] less than $100" (https://www.coderabbit.ai/blog/teaching-nvidia-nemotron-3-5-lightning-to-route-code-reviews).
- Free-tier quirk noticed by users: "The free version gives you 1M context. The paid version
  [262K]… the tiering is kind of backwards" (r/AIToolsPerformance,
  https://www.reddit.com/r/AIToolsPerformance/comments/1vmn2z5/).
- Model-card nit: NVIDIA's comparison chart mixes nvfp4 and bf16 builds (HN,
  https://news.ycombinator.com/item?id=49257947).

### Known for
AA's fastest model (#1/62 at 292.8 tok/s) given away free — the zero-cost executor for the
mechanical high-volume step layer of agent pipelines.

### Caveats
- **Free-route health was flapping last cycle and is NOT re-verified this cycle** (OpenRouter
  `/endpoints` 404'd for every slug on 2026-11-01): 36.7% 24h uptime at 2026-10-18 → 100% at
  2026-10-25, single Nvidia nvfp4 endpoint, 65,536 completion cap, no structured_outputs
  (research/2026-10-top15-j-mimo-v32-muse-nemotron.md). Plan for variance.
- **OpenRouter free quotas:** 50 free-model requests/day total; 1,000/day if you have purchased
  ≥10 credits (https://openrouter.ai/docs/faq). Free ends without warning (precedent above).
- **Data terms on OpenRouter:** OpenRouter itself does zero prompt/completion logging by default
  (opt-in logging exists for a 1% discount), and routes to training-capable or policy-unconfirmed
  providers only if the account's **free-model** training toggle allows it — "There are separate
  settings for paid and free models" (https://openrouter.ai/docs/faq;
  https://openrouter.ai/docs/guides/privacy/provider-logging.md). NVIDIA's own free-endpoint terms
  (trial use only, no confidential data, logged to improve NVIDIA products) are quoted verbatim in
  OpenCode's docs for the same endpoints (https://opencode.ai/v2/docs/console/models/).
  Exposure stays `trains`.
- **Quality ceiling:** AA 5.5/coding 26.8/agentic 3.5; weak prose (EQ-Bench Elo 1280,
  measured 2026-10-17, https://eqbench.com/creative_writing.html); never for reasoning, prose, or
  design (no Design Arena row).
- **Paid route is the pin:** OpenRouter catalog $0.07 in / $0.20 out at 262,144 ctx (2026-11-01);
  last endpoint check (2026-10-25) found 4 providers at $0.12–0.20/M out
  (research/2026-10-top15-j… file above).

### Verdict: **update** (keep; refresh index-era numbers, drop the dead "12.9/26.8-era" framing
for dated v5.0 values)

Demand rose quarter-over-quarter; absence from the boards is truncation, and the AA "drop" is the
rescale.

---

## nvidia/nemotron-3.5-super-vl:free

### Benchmark standing
- **AA (v5.0, 2026-11-01): Intelligence 13.6 (page displays 14), #1/2 in its class** (only two
  class members scored so far); **speed 474.1 tok/s #1/26** (median across providers), TTFT 0.71 s;
  price **$0.15 in / $0.50 out** (feed + OpenRouter catalog; AA page median says $0.20 in);
  **$0.54 per Index task** — driven by **very verbose 120M tokens/task**; 120B total / 12B active;
  1M context; text+image input; **OpenMDW-1.1**; released **2026-10-15**; listed through 9
  providers (https://artificialanalysis.ai/models/nemotron-3-5-super-vl;
  https://openrouter.ai/api/v1/benchmarks; https://openrouter.ai/api/v1/models). The launch-week
  "26 on the Intelligence Index" figure (eesel, 2026-10-18,
  https://www.eesel.ai/blog/nemotron-3-5-super-vl) is pre-rescale — not a quality drop to 13.6.
- **OpenRouter evals (runs 2026-10-31):** gpqa_diamond **86.8%** (594 tasks), tau_bench airline
  **72.9%** (150 tasks) — brief verified (feed).
- **Design Arena (feed 2026-11-01, verified):** website 1165 (35.0% win), codecategories 1150
  (33.1%), uicomponent 1133 (30.6%), 3d 1124 (30.4%), gamedev 1108 (29.6%) — bottom-third
  everywhere (note: gamedev sits just under the brief's 30% band).
- **Vendor numbers (NVIDIA-reported, NVFP4 checkpoint):** GPQA-Diamond 89.90, SWE-bench Verified
  71.07, Terminal-Bench 2.1 60.80, BrowseComp 77.5, OSWorld-Verified 52.3, IFBench 71.50 — and
  **tau3-bench banking 17.78 as its worst result**; beats Nemotron 3 Ultra on harness evals
  (Hermes 63.44% vs 56.33%; LangChain 87.05% vs 84.3%)
  (MarkTechPost launch teardown, 2026-10-15, https://www.marktechpost.com/2026/10/15/nvidia-nemotron-3-5-super-vl-release/;
  NVIDIA blog: https://blogs.nvidia.com/blog/nemotron-3-5-super-vl/; model card:
  https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4).
- **Traffic — ramping, not declining:** `nvidia/nemotron-3.5-super-vl-20261015:free` carried
  **4.05T tokens over 16/30 days** 2026-10-02→10-31 (0.53% share; ≈0.25T/day while present —
  nearly **double** Lightning's daily rate of ≈0.135T/day)
  (https://openrouter.ai/api/v1/datasets/rankings-daily?window=30d, 2026-11-01). Absent from all
  29 tags' top-10 and all five domains (this cycle's check) — for a two-week-old model this is
  board-invisibility, not decline; it was never ranked long enough to be "re-ranked" downward.
- Availability (2026-10-31/11-01): OpenRouter shows 8 paid providers from $0.10–0.15/M in
  (Crusoe, CoreWeave, DeepInfra, Io Net, PrimeIntellect, Together…), 1M ctx on several
  (MarkTechPost's OpenRouter widget, verified Oct 31, link above); **not available via EU
  in-region routing** (https://openrouter.ai/nvidia/nemotron-3.5-super-vl/llms.txt).

### Opinions
- Positive: "From what I can throw at Nemotron 3.5 Super VL, it seems to be better at knowledge
  than any other 120B model I've tried so far" (r/LocalLLaMA,
  https://www.reddit.com/r/LocalLLaMA/comments/1x9mwmz/); day-0 local runs already working
  (r/StrixHalo, https://www.reddit.com/r/StrixHalo/comments/1x6v6o1/).
- Negative: "Nemotron 3.5 Super VL is disappointing… I was excited for this but I have been trying
  it out for the last couple of days and the results are [poor]" (r/opencode,
  https://www.reddit.com/r/opencode/comments/1xcox9l/); "The Nemotron-3.5 releases are
  particularly not so good at the pandas/numpy and DDDM [tasks]" (r/LocalLLaMA tests,
  https://www.reddit.com/r/LocalLLaMA/comments/1x7frdn/); "Nemotron 3.5 Super VL is a whole tier
  behind Qwen 3.8 27B" (r/unsloth,
  https://www.reddit.com/r/unsloth/comments/1x6oo8k/).
- Integration coverage: Cline agent-harness tests (https://cline.bot/blog/nvidia-nemotron-3-5-super-vl-cline-agent-harness),
  LangChain/ChatNVIDIA test write-up (https://www.reddit.com/r/LangChain/comments/1x6ul8v/),
  vision-task hands-on (https://www.mindstudio.ai/blog/nemotron-3-5-super-vl-vision-model),
  automation/pricing analysis (https://www.activepieces.com/blog/nemotron-35-super-vl-pricing-and-benchmarks-2026),
  day-0 vLLM/llama.cpp/Ollama support (https://daily.dev/posts/nemotron-3-5-super-vl-shipped-with-vllm-support-on-day-zero-zii5aypym).
- Early enterprise claims (vendor-mediated): Scale AI "40x lower inference cost and 5x lower
  latency", Ramp "up to 50% higher throughput" (MarkTechPost, link above — NVIDIA-sourced).

### Known for
NVIDIA's free open multimodal agent model — one 120B-A12B checkpoint that reads text, images,
documents and video while calling tools and coding, given away on the OpenRouter `:free` and
OpenCode free lanes.

### Caveats
- **Data terms (`trains`):** on OpenCode's route, OpenCode's privacy table carries NVIDIA's trial
  terms verbatim — "Trial use only — do not submit personal or confidential data. Your use is
  logged … to improve NVIDIA products and services … NVIDIA API Trial Terms of Service"
  (https://opencode.ai/v2/docs/console/models/). On OpenRouter, free-model training-capable
  routing is governed by the account's separate free-model privacy toggle, with zero prompt
  logging by default (https://openrouter.ai/docs/faq;
  https://openrouter.ai/docs/guides/privacy/provider-logging.md). Exposure stays `trains`;
  OpenCode's sibling route (`opencode/nemotron-3.5-super-vl-free`, 1,048,576 ctx / 131,072 out,
  models.dev 2026-11-01) carries the same NVIDIA terms.
- **Free-route shape not fully re-verifiable this cycle:** one raw `/endpoints` snapshot
  (2026-11-01) showed a single Nvidia-hosted endpoint before the API began 404ing; OpenRouter
  free quotas apply (50/day, or 1,000/day with ≥10 credits purchased,
  https://openrouter.ai/docs/faq). The brief's 977K context matches neither OpenRouter (1,000,000)
  nor models.dev (1,048,576).
- **Cost trap despite $0.50/M out:** 120M output tokens per AA Index task makes it **$0.54/task —
  the most expensive of this batch per task** on AA's own accounting (AA page, 2026-11-01);
  verbosity, not price rate, sets the bill. On the free lane money isn't the constraint — tokens
  and quota are.
- **Weak spots:** Design Arena bottom-third (1108–1165; 29.6–35% wins), vendor-reported
  tau3-bench banking 17.78 (long-horizon tool use in that domain), community reports of weak
  pandas/numpy work. Vision/document strengths are the pitch; numeric-heavy coding is not.
- **New & churning:** 16/30-day traffic, OpenMDW-1.1 (commercial-friendly), Bolt 74B-A9B sibling
  released same day with Bolt E4B promised Oct 23 (MarkTechPost) — expect rapid lineup change;
  free economics can end without warning.

### Verdict: **update** (rewrite — the old summary said "no independent benchmark row at the Oct
snapshot"; rows now exist)

---

## Policy summaries

**opencode/mimo-v2.6-flash-free** — Free, limited-time OpenCode-harness-only route over Xiaomi's
MiMo-V2.6-Flash (registry-confirmed base_model; no benchmark rows exist for `opencode/*` ids —
its standing is Flash's: AA 26.7 on v5.0 as of 2026-11-01, gpqa 73.2%, MIT weights). Pick it as
the zero-cost coding/agent lane inside OpenCode only; **its documented data term is a training
carve-out** ("During its free period, collected data may be used to improve the model" —
OpenCode docs, 2026-11-01), so never send sensitive material, and note the registry caps it at
200K context / 32K output (not the model's 1M) with an undocumented, previously-changing daily
quota; the privacy-preserving route to the same model is the paid/Go lane ($0.14/$0.28, zero
retention).

**xiaomi/mimo-v2.6-pro** — The MIT-licensed 1T/42B quality rung at $0.435/$0.87 (OpenRouter
catalog and AA, 2026-11-01), still moving 6.20T tokens/month (flat, all 30 days) but no longer
wearing any crown: AA's v5.0 rescale put it at 29.9 (#3/22 in class, behind GLM-5.3 Max) and Kimi
K3.1 Pro's promised weights (2026-11-04) may reset the open-weights leader days after this write.
Pick it for cost-sensitive agentic/tool, security and long-form work where decode speed doesn't
matter — it runs ~49 tok/s, is very verbose (130M tokens/Index task), over-thinks, spins in tool
loops, and has Vals-documented reward hacking, so supervise unattended runs; its absence from all
board top-10s is truncation, not decay. Prices/index numbers dated 2026-11-01.

**opencode/nemotron-3-ultra-free** — Free, limited-time OpenCode-harness-only route over NVIDIA
Nemotron 3 Ultra (registry `base_model` confirmed; **registry status: deprecated** as of
2026-11-01, though still listed in OpenCode's docs), whose standing is the base model's AA 11.8
(#21/22 in class) with a decent coding index (49.3) and stale August eval runs. Use only inside
OpenCode where cost is literally zero and quality variance is acceptable (its one domain rank is
ops #14/24); **NVIDIA's trial terms apply verbatim — "do not submit personal or confidential
data", logged to improve NVIDIA products** — and there is no privacy-preserving OpenCode sibling
for Nemotron, context claims disagree (1M vs AA-measured 262k), and the deprecation flag says this
lane may close first.

**nvidia/nemotron-3.5-lightning:free** — A distilled 31.6B-A3.6B executor whose single selling
point is speed — AA #1/62 at 292.8 tok/s, $0.05–0.07/M in (three sources, 2026-11-01), intelligence
5.5 on v5.0 (page: 6, "among the least intelligent") — free on OpenRouter's `:free` lane and still
busy: 4.06T tokens over all 30 days of October, up from 3.61T (so "stale" means truncation below
every tag's top-10, not decline). Use it for mechanical high-volume pipeline steps where the
50–1,000 free requests/day quota (OpenRouter FAQ) and a single flapping Nvidia endpoint (36.7%
uptime 2026-10-18 → 100% 2026-10-25; not re-verified this cycle) are tolerable; never for
reasoning, prose or design, and pin the paid route ($0.07/$0.20, 262K ctx) for anything that must
run. Free-model training toggles govern exposure; NVIDIA trial terms apply.

**nvidia/nemotron-3.5-super-vl:free** — NVIDIA's 120B-A12B open multimodal agent model (text +
image + document + video in, tools/code out, OpenMDW-1.1, released 2026-10-15) served free on
OpenRouter's `:free` lane, where it has already moved 4.05T tokens in its first 16 days
(2026-10-02→10-31 window) despite ranking in no domain — a ramping newcomer, not a decliner. Now
benchmarkable: AA 13.6 (v5.0), gpqa 86.8%, tau 72.9% (runs 2026-10-31), fastest in its class
(474 tok/s) but very verbose (120M tokens/task → $0.54 per AA task) with bottom-third Design Arena
(1108–1165, 29.6–35% wins) and vendor-reported weak spots (tau3 banking 17.78). Pick it for
zero-cost vision/document/screen triage and multimodal agent steps; avoid for design taste and
numeric-heavy coding, mind the free quota, EU in-region routing is unavailable, and NVIDIA trial
terms ("do not submit personal or confidential data", logged to improve NVIDIA products) apply on
the OpenCode sibling route.