# Top-15 traffic models, group G (2026-11): Tencent Hy4 + NVIDIA Nemotron 3.5 Super VL (paid)

Research date: **2026-11-15**. Compiled for the model-selection policy (procedure: research/README.md §2).
Two ungrouped gap models at `--top 15`: a brand-new flagship (`tencent/hy4`) and the paid sibling of an
already-summarized free route (`nvidia/nemotron-3.5-super-vl`).

**Method & sources.** First-party anchors (combined benchmarks feed as of 2026-11-15, per the group brief)
were cross-checked against: OpenRouter model pages and the public GPQA-Diamond leaderboard page
(fetched 2026-11-15), Artificial Analysis coverage via aggregators, Design Arena ELOs as displayed on
OpenRouter's benchmark panel (fetched 2026-11-15), vendor materials (Tencent Hy post and press release,
NVIDIA/Hugging Face model cards), launch teardowns, press (SCMP, THE DECODER, Unite.AI, MACCUS, technode,
ORIENS), third-party benchmark aggregators (Vals AI, BenchmarkList, LLMBenchmark, benchlm, datalearner,
llmlearner, Plotly, ARC Prize), and community threads (HN, Reddit). Every opinion claim carries a URL.
Dated snapshots are dated. **Thin coverage is expected — Hy4 is 11 days old on research day; how thin each
stream is, is stated per section.**

**Anchor verification notes (stated, not silently accepted):**
- `tencent/hy4`: AA intelligence **34.6** in the feed matches aggregator renderings of AA's page at **35**
  ("index 35, No. 2 in China", AA measurement published 2026-11-05, https://modelbrief.app/hy4/ —
  rounding, same pattern as other v5.0 rows). Design Arena numbers in the brief (gamedev **1271 / 49.4%**,
  codecategories **1253**, 3d **1251**, website **1250**, uicomponent **1194 / 38.7%**) **disagree slightly
  with OpenRouter's own benchmark panel fetched the same day** (3D 1255, Code Categories 1256,
  Game Development 1255, UI Component 1180, Website 1256 — https://openrouter.ai/tencent/hy4-20261104).
  Both are same-day snapshots of a live arena; treat the ~10–16 point spread as inter-pull drift, and note
  uicomponent is the weak category on both (1180–1194, ~38–39% win). OpenRouter GPQA row **83.2% at
  ~$0.064/task** verified live (below).
- `nvidia/nemotron-3.5-super-vl`: brief anchors (AA 13.6; Design Arena website 1160 / 34.8%, uicomponent
  1155, codecategories 1140, 3d 1118, dataviz 1083, gamedev 1081; gpqa 86.8% @ $0.0219, tau airline
  72.9% @ $0.0331) are consistent with the prior cycle's verified 2026-10-31 run values (research/
  2026-11-top15-b-mimo-nemotron.md: gpqa 86.8%, tau 72.9%, Design Arena 1108–1165) and with aggregator
  echoes (Design Arena websites 1160 / UI 1155 / gamedev 1082 / dataviz 1084, https://llmbenchmark.ai/compare/nvidia-nemotron-3-5-super-vl-vs-xiaomi-mimo-v2-5-pro,
  2026-11-15). Small ELO drift between pulls (e.g. website 1165 on 2026-10-01 vs 1160 now).
- **LMArena:** no actual LMArena board standing was found for either model in this pass. NVIDIA's model
  card reports an "LMArena v3 proxy" score of 52.67 — a vendor-run proxy, not a board placement
  (https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16). Absence from the arena is
  reported as absence, not guessed around.

---

## tencent/hy4

Slug note: OpenRouter's `tencent/hy4-20261104` date suffix is the **listing date (2026-11-04)**, matching
Tencent's own announcement date; the vendor revision claim is that this is the *full release* following the
open-weight **Hy4 preview of 2026-08-28** (HF repos published 2026-08-27 — the `hy4-preview-20260827` slug
date). These are two different checkpoints: only the preview's weights exist publicly.

### Benchmark standing
- **What it is, first:** the full release of Tencent's Hy-generation flagship. Tencent says it "substantially
  scales up both pre-training and post-training" over the preview, "adds vision capabilities for the first
  time", and adds computer use (CLI + GUI), with targeted training on Blender/CAD and multi-app workflows
  (https://hy.tencent.ai/research/hy4, 2026-11-04). Parameter count for the full release was **not
  restated** — 770B total / 49B active is the preview's figure, repeated by aggregators as a Tencent Cloud
  figure but unconfirmed for the final checkpoint
  (https://technewsexplained.com/en/ai/tencent-hy4-vision-computer-use;
  https://www.techiesjournal.com/tencent-hy4-ai-model-capabilities-pricing-availability/11606/). So: a true
  successor in the preview→GA sense (scaled training, new modalities), **not** a disclosed architecture
  rewrite.
- **Artificial Analysis (v5.0/v5.0.1, 2026-11-15 feed): intelligence 34.6** (page displays 35),
  **#2 in China** on AA's own count (https://modelbrief.app/hy4/). AA's independent measurement landed
  2026-11-05, one day after release. AA-Omniscience rows on OpenRouter's panel: accuracy **50.0%**,
  non-hallucination rate **10.9%** — i.e. when it answers unverifiable questions it is right about half the
  time (https://openrouter.ai/tencent/hy4-20261104). Coding/agentic AA columns are empty — **no AA coding
  or agentic index exists for Hy4 yet** (brief anchor, confirmed empty on the panel).
- **AA security boards (2026-11-03, pre-release measurement):** leads CWE-Bench-AA at **75.8%** (DeepSeek
  V4.1 Flash 1017 second at 69.2%), #2 on the AA Cyber Index (58.0, behind Kimi K3.1 Pro's 64.1), #10 on
  CyberGym end-to-end (72.5%) — collected at https://modelbrief.app/hy4/.
- **OpenRouter evals:** GPQA-Diamond **83.2%** at **$0.064/question**, 8.2 min and 51.2k output tokens per
  question — verified live on OpenRouter's leaderboard (run window: newest 90 days, page generated
  2026-11-14, https://openrouter.ai/benchmarks/gpqa-diamond). Rank #76 on that board.
- **The predecessor comparison — stated carefully.** The same leaderboard shows **Hy4 preview at 89.8% ±0.6**
  ($0.12/q, #30). So the briefed "89.8 → 83.2 drop" is real *as two rows on one leaderboard*, but it is
  **not a paired evaluation**: OpenRouter aggregates whatever runs happened in the last 90 days per
  model-provider pair, Hy4's row carries **no stddev** (fewer runs), and cost/time per question differ
  ($0.064 vs $0.12; 8.2 vs 13.8 min). Hy4 is also a different, vision-capable checkpoint with scaled-up
  training, and Tencent never published a GPQA figure for the full release (its launch chart has no GPQA
  row — https://a2agent.me/blog/tencent-hy4-benchmarks). **Whether science-reasoning actually regressed is
  unresolved; the honest read is "two incomparable runs, Hy4's is the weaker one, no error bars"** — do not
  treat 83.2 vs 89.8 as a measured capability drop, and do not dismiss it either. Vendor-side GPQA numbers
  exist only for the preview (92.3% self-reported, https://benchgen.com/models/hungyuan/hy4-preview).
- **Vendor benchmarks (all Tencent-run, 2026-11-04):** the appendix table puts Hy4 above preview on every
  paired row — WebCraftBench 52.7→78.9, APEX-Agents v1.1 53.9→75.2, AutomationBench 36.3→56.2,
  Terminal-Bench 4.0 26.3→44.4, DeepSWE 64.3→74.9; vs the open field it leads 6 of 12 panels (ProgramBench,
  FrontierCode 2.0, 3DArena-Modeling, E-Bench 2.0, Hy-BrowseComp 2.0, TenureTrail) while **Kimi K3.1 Pro
  beats it on the other six** — Terminal-Bench 4.0 66.8 vs 44.4, AutomationBench 65.6 vs 56.2, Terminal-Bench
  Science 41.7 vs 19.8 (https://a2agent.me/blog/tencent-hy4-benchmarks;
  https://aimlapi.com/blog/tencent-hy4-review). Tencent also concedes large gaps to closed models on its own
  internal chart: Hy-FrontierMath T5 **13.0 vs 97.5 (GPT-6.1 Sol)**, Goal2Repo 23.2 vs 74.0 (Opus 5.5)
  (same a2agent page). Its blind finance eval (213 professionals, 579 tasks) ranked Hy4 first among open
  models at 3.04 vs DeepSeek-V4.1-Flash 2.97, Kimi K3.1 Pro 2.68, GLM-5.3 2.68 — **Tencent-run, scale and
  rubric unpublished** (https://www.tencent.com/tencent-launches-hy4-joining-the-ranks-of-the-worlds-leading-open-source-ai-models).
- **Independent third-party:** Vals AI is the one independent full-suite measurement — **Vals Index 59.35%
  ±1.08, #15 of 36** (leaderboard updated 2026-11-09, https://www.techiesjournal.com/tencent-hy4-ai-model-capabilities-pricing-availability/11606/),
  versus the preview's 53.21% (#26/36, https://www.vals.ai/models/tencent_hy4-preview) — a real
  improvement on an independently run index. OpenRouter's panel also carries Vals **Hy4 EMB v1.1 66.2%**
  (preview: 68.9%, https://openrouter.ai/tencent/hy4-20261104).
- **Design Arena (feed 2026-11-15):** gamedev 1271 / 49.4% win, codecategories 1253 / 47.2%, 3d 1251 /
  47.2%, website 1250 / 47.4%, uicomponent 1194 / 38.7% (brief); OpenRouter's same-day panel reads
  1255–1256 on four categories and 1180 on uicomponent. Either way: **upper-mid board on web/game/3D
  categories (~47–49% wins), clearly weakest on UI components** — no category crown, disagreement is
  inter-pull drift, not a substantive conflict.
- **Traffic (catalog, brief):** 28.99T tokens over **11/30 days** in window 2026-10-16 → 2026-11-14 — i.e.
  ~2.6T/day since listing on 2026-11-04, an enormous debut rate (for scale, its preview did 8.97T in the
  week through 2026-10-27, then 5th-most-used model on OpenRouter —
  https://a2agent.me/blog/tencent-hy4-benchmarks). Domain ranks: research #12/19, writing #15/18,
  **coding #4/20, orchestration #5/22**, ops #7/14, conversational_reply #9/10 (this cycle's policy check).
- **Price (2026-11-15):** list **$0.834 / $2.501** per 1M in/out with $0.042 cached, shown at **50% off →
  $0.417 / $1.251** on OpenRouter (promo end date not stated on OpenRouter; Tencent Cloud TokenHub's 50%-off
  runs through **2026-12-31**). 1,048,576 context / 65,536 max output
  (https://openrouter.ai/tencent/hy4-20261104; https://mcsaguru.com/tencent-hy4-open-model-openrouter-pricing).
  The brief's $0.42/$1.25 is the discounted rate.

### Opinions
- Reception is **positive but pricing- and weights-skeptical**. Main HN thread: 272 points, 111 comments
  (https://news.ycombinator.com/item?id=50365780). Recurring themes:
- Value framing: "Slightly worse than Kimi 3.1M Pro … but much cheaper even excluding the current 50% off
  promotion" (minimaxir, https://news.ycombinator.com/item?id=50369069); Plotly's independent data-analytics
  bench put Hy4 "on the cost/accuracy frontier … right in between GPT-6.1 Sol and GPT-6.1 Terra" but
  "Verrrry thorough … verrrrry slow" — ~26 SQL queries per question, some 64 (chriddyp,
  https://news.ycombinator.com/item?id=50369676; full write-up
  https://plotly.com/blog/tencent-hy4-plotly-data-analytics-bench).
- Cost criticism: "Not cost competitive. The performance difference is not commensurate with the price"
  vs DeepSeek's off-peak $0.15/$0.60 (https://news.ycombinator.com/item?id=50369295); rebuttal that
  per-task cost, not per-token, is the real metric (https://news.ycombinator.com/item?id=50369585).
  A third-party PacBench run ties it with DeepSeek V4.1 Flash at ~1/7 the cost
  (https://news.ycombinator.com/item?id=50370557).
- Honesty noted approvingly: Tencent's own "notable gap remains between it and top proprietary models"
  framing drew "I like that they acknowledge that" (https://news.ycombinator.com/item?id=50369691).
- Weights criticism is the sharpest recurring complaint: "Tencent says Hy4 ranks among the best open
  models. Its weights aren't out yet" — MACCUS, 2026-11-04, https://maccus.fr/en/tencent-hy4-ai-model;
  THE DECODER: "the model weights won't be released until later"
  (https://the-decoder.com/tencent-releases-hy4-with-vision-and-computer-use-claims-second-place-among-chinese-ai-models);
  still unpublished as of 2026-11-12 (HF `tencent/Hy4` 401s, GitHub repo 404s —
  https://www.techiesjournal.com/tencent-hy4-ai-model-capabilities-pricing-availability/11606/; repeatable
  check documented at https://www.digitalapplied.com/blog/tencent-hy4-release-what-is-confirmed). Press
  coverage beyond that is standard launch reporting: SCMP
  (https://www.scmp.com/tech/big-tech/article/3373227/tencent-unveils-hy4-open-weight-ai-race-deepseek-zai-alibaba-heats),
  Unite.AI (https://www.unite.ai/tencent-releases-full-hy4-model-with-vision-and-computer-use),
  technode (https://technode.global/2026/11/09/tencent-hy4-visual-computer-use/).
- Safety filtering read both ways: r/LocalLLaMA — "Like Kimi K3.1, they also neutered its cyber
  capabilities" (https://www.reddit.com/r/LocalLLaMA/comments/1xnhzbz/introducing_hy4_open_weights_soon);
  HN discussion of the deliberate exclusion of exploit/RE/pentest data summarized at
  https://hndistilled.com/story/50365780.
- Coverage thinness: hands-on community reviews of the *full* release are almost nonexistent on research
  day (11 days old); most Reddit reaction still targets the **preview** (overthinking, size,
  quantization — https://www.reddit.com/r/LocalLLaMA/comments/1w0igxk/, community roll-up at
  https://aexol.ai/benchmarks/localllama/hy4-preview/). One preview-era negative datapoint worth carrying:
  a German-language eval index ranked preview ~14th overall, "below Deepseek pro and significantly below
  GLM 5.3 Flash" (https://news.ycombinator.com/item?id=49502506).

### Known for
Tencent's 11-day-old hosted flagship that lands a top-5 OpenRouter presence on coding/orchestration and
#2-in-China AA intelligence (34.6) at half-price promo rates — an API-only "open-source" model whose
weights are still a promise.

### Caveats
- **Not actually open yet.** "We plan to open-source Hy4's model weights" — no date, no system card, no
  license, no final parameter count (https://hy.tencent.ai/research/hy4; HF check 401/404 as of 2026-11-12,
  links above). Only the *preview* is Apache 2.0. Any policy language saying "open-weight" for `tencent/hy4`
  is wrong today.
- **Single provider on OpenRouter:** Tencent Cloud only — "OpenRouter forwards every request to it
  directly — no routing decisions to make", 54 tok/s P50 throughput, 3.30 s latency, 100% uptime (page
  fetched 2026-11-15, https://openrouter.ai/tencent/hy4-20261104). No failover; slow decode (~54 tok/s)
  plus Plotly's "very thorough, very slow" behavior means wall-clock cost is high even when the bill isn't.
- **Promo price risk:** the $0.417/$1.251 is a 50%-off promotion of unstated end on OpenRouter (TokenHub's
  runs to 2026-12-31). Effective list is $0.834/$2.501 — roughly 2× the headline. Dated 2026-11-15.
- **Recency risk:** 11 days old, ~2.6T tokens/day compressed into that window, Hy4 Flash promised "soon"
  (announcement text contradicts its own heading, https://mcsaguru.com/tencent-hy4-open-model-openrouter-pricing),
  weights/system card promised "in the coming days". Expect churn in price, lineup and standing within
  weeks.
- **Eval disagreement to carry:** GPQA 83.2% (OpenRouter, no error bars) vs preview 89.8% ±0.6 vs vendor
  preview claim 92.3% — unresolved methodology difference (see benchmark standing). Vals #15/36 and
  Terminal-Bench-4 44.4 (vendor) vs Kimi's 66 say it is *not* the open leader on hard agentic terminal work.
- **Capability caveats:** uicomponent is the weak Design Arena category (1180–1194, ~38–39% wins);
  Tencent's own chart concedes frontier gaps on research math (13.0 vs 97.5), long-horizon repo building and
  hard VQA; cyber-offensive capability was deliberately trained out; AA-Omniscience non-hallucination 10.9%
  means heavy confabulation pressure on unverifiable questions.
- **EU in-region routing unavailable** (https://maccus.fr/en/tencent-hy4-ai-model). Context/output caps:
  1,048,576 / 65,536 (OpenRouter); TokenHub reportedly caps input at ~960K (https://modelbrief.app/hy4/).

---

## nvidia/nemotron-3.5-super-vl

Slug note: `nvidia/nemotron-3.5-super-vl-20261015` — listing date **2026-10-15**, identical to NVIDIA's
announcement date; no vendor revision suffix. The same-day BF16 and NVFP4 checkpoints are quantization
variants of one release, not revisions. This is the **paid** sibling of the already-summarized
`nvidia/nemotron-3.5-super-vl:free`.

### Benchmark standing
- **Multimodal — confirmed.** Text, image, document and **video (MP4 up to ~2 minutes, frame-sampled)**
  input, text out; 120B total / 12B active MoE with interleaved Mamba-2 + attention and a C-RADIO vision
  encoder; 1M context; OpenRouter modalities list in: text/image/video
  (https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16;
  https://ai-api-hub.com/providers/openrouter/models/openrouter-nvidia-nemotron-3-5-super-vl).
- **Serving on OpenRouter (page fetched 2026-11-15): 10 paid providers** — CoreWeave $0.15/$0.47,
  Venice $0.20/$0.50, Prime Intellect $0.15/$0.50, Together $0.15/$0.50, DeepInfra $0.15/$0.50,
  Crusoe $0.10/$0.40, Nebius $0.30/$0.90, io.net $0.09/$0.30 (40%-off promo), Darkbloom $0.06/$0.35,
  Baseten $0.20/$0.50 — spread $0.06–$0.30/M in, $0.35–$0.90/M out; weighted-average effective input
  $0.068 (cache-heavy) / output $0.5195. Brief's $0.15/$0.50 is the **median**, dated 2026-11-15
  (https://openrouter.ai/nvidia/nemotron-3.5-super-vl; full list:
  https://openrouter.ai/nvidia/nemotron-3.5-super-vl/llms.txt). Price history shows a brief dip to
  $0.10/$0.40 on 2026-10-19→10-22 before returning (https://ai-api-hub.com/providers/openrouter/models/openrouter-nvidia-nemotron-3-5-super-vl).
  Uptime 96.6–99.95% across providers; throughput 9–272 tok/s depending on host (same page).
- **Artificial Analysis (v5.0, feed 2026-11-15): intelligence 13.6**, #1/2 in its two-member class; coding/
  agentic columns empty. Note the launch-week figure of ~26.5 quoted everywhere (eesel, 2026-10-18,
  https://www.eesel.ai/blog/nemotron-3-5-super-vl) was **index v4.3** — the fall to 13.6 is the v4.3→v5.0
  rescale of 2026-11-01, not a model change (documented in research/2026-11-top15-b-mimo-nemotron.md).
  Aggregator cross-checks agree at 13.6 (https://benchmarklist.com/models/nvidia-nemotron-3.5-super-vl-120b-a12b;
  https://llmlearner.com/models/nemotron-3-5-super-vl).
- **OpenRouter evals (brief; runs 2026-10-31, verified in prior cycle):** gpqa_diamond **86.8%** at
  $0.0219/task, tau_bench_verified_airline **72.9%** at $0.0331/task. (Vendor GPQA is higher: 89.52 BF16 /
  89.90 NVFP4, model card.)
- **Vendor-reported (NVIDIA, NeMo Gym, model card):** SWE-bench Verified 71.10, Terminal-Bench 2.1 60.67,
  OSWorld-Verified 51.14, CharXiv reasoning 80.82, OCRBench v2 EN 68.12, MMLongBench-Doc 62.82, GraphWalks
  89.71, BrowseComp 78 — with the card noting several baselines were re-run in different scaffolds, and the
  model **trailing** Qwen3.8-Flash-Next / GLM-5.3-Flash on Terminal-Bench 2.1, SWE-bench Multilingual,
  BrowseComp and HLE (https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16; readable
  teardown: https://aitoolsreview.co.uk/insights/nvidia-nemotron-3-5-super-vl).
- **Design Arena (feed 2026-11-15):** website 1160 / 34.8%, uicomponent 1155 / 32.9%, codecategories 1140 /
  32.4%, 3d 1118 / 30.5%, dataviz 1083 / 25.9%, gamedev 1081 / 27.4% — bottom-third everywhere (prior cycle
  2026-10-01 snapshot read 1108–1165; drift only).
- **Other independent boards:** LLMBenchmark Index **24.3, #116 of 118** overall, coding index 14.8
  (2026-11-15, https://llmbenchmark.ai/models/nvidia-nemotron-3-5-super-vl); AI Coding Daily's harness
  leaderboard: **#51, 44.96 pts** with OpenCode, evaluated 2026-11-04
  (https://aicodingdaily.com/model/nemotron-3.5-super-vl); ARC Prize verified: **22.7% ARC-AGI-1 (high
  reasoning), 1.9% ARC-AGI-2** (https://arcprize.org/results/nvidia-nemotron-3-5-super-vl-120b-a12b);
  Vibe-code and Terminal-Bench-4 readings near zero (0.0% TB4 per Vals run,
  https://llmbenchmark.ai/compare/claude-sonnet-4-5-vs-nvidia-nemotron-3-5-super-vl). Plotly's independent
  data-analytics bench: **30/43 (70%) for $0.46 total, fastest of 28 models at 12 s/question** — but 0/5 on
  planted data-quality checks (https://plotly.com/blog/nvidia-nemotron-3-5-super-vl-plotly-data-analytics-bench).
- **LMArena: no board standing found** (see method note); only NVIDIA's vendor "LMArena v3 proxy 52.67".
- **Traffic (catalog, brief):** 1.34T tokens over 11/30 days in window 2026-10-16 → 2026-11-14 on the paid
  slug — small next to the `:free` sibling (4.05T in its first 16 days, prior cycle); demand is mostly
  free-lane. Domain rank: **research #15/19** — its only placement.

### Opinions
- Split community verdict, same as the free sibling: "Nemotron 3.5 Super VL is disappointing … results are
  abysmal. Nemotron 3 Ultra still mogs Super VL even though the benchmarks say otherwise" (r/opencode,
  2026-11-08, https://www.reddit.com/r/opencode/comments/1xcox9l/) vs "Don't sleep on Nemotron 3.5 Super VL"
  — a RAG user finding it beats Gemma 4 31B and is "way faster on my Mac Studio" (r/LocalLLaMA,
  https://www.reddit.com/r/LocalLLaMA/comments/1x9mwmz/).
- Launch-thread consensus: "not as good as Qwen 3.8 FN, but in the same vague ballpark … Terminal Bench 2.1
  being only 60.7 is really bad" and "they're not meant to be state of the art class leaders out of the box"
  (r/LocalLLaMA, https://www.reddit.com/r/LocalLLaMA/comments/1x6nl8m/).
- Hands-on agentic test: fixed a real multi-container bug end-to-end but also made **three unnecessary edits
  in files that weren't broken** — "Review diffs before merging" (goremy, 2026-10-21,
  https://goremy.ai/blog/articles/nemotron-3-5-super-vl-hands-on-test).
- Vision workloads are where praise concentrates: a 300-receipt structured-extraction pipeline hit 91%
  (98% with reasoning on, at 3× latency) (r/aiagents,
  https://www.reddit.com/r/aiagents/comments/1x6yfmz/); LangChain's Deep Agents suite: 87% pass rate and
  55% less task time than DeepSeek V4.1 Flash at similar success (vendor-mediated test,
  https://www.reddit.com/r/LangChain/comments/1x6ul8v/).
- Review-tier coverage: eesel's read — "Super VL isn't the smartest open model, it's the fastest good one
  that can see" (https://www.eesel.ai/blog/nemotron-3-5-super-vl); miraflow — "a fast, open, agent-oriented
  vision model rather than a benchmark champion" (https://miraflow.ai/blog/nemotron-3-5-super-vl-explained-benchmarks-open-vision-agents-2026);
  host-by-host cost/latency test (MxChat, https://mxchat.ai/nemotron-3-5-super-vl-pricing-chatbot-test/).
- Enterprise claims are NVIDIA-sourced (Scale AI "40x lower inference cost", Ramp "up to 50% higher
  throughput" — via https://www.marktechpost.com/2026/10/15/nvidia-nemotron-3-5-super-vl-release/); treat as
  vendor-mediated.

### Known for
NVIDIA's cheap, fast, genuinely multimodal 120B-A12B open workhorse — text/images/2-min video/documents in,
tools out — whose paid OpenRouter route spans 10 hosts from $0.06/M in and which earns its keep on
document, chart and screenshot work rather than on any leaderboard crown.

### Caveats
- **Host variance is the paid route's defining quirk:** quantization differs by provider (NVFP4/FP4/BF16),
  max output ranges **32K (Darkbloom/Venice) to 944K (CoreWeave/Baseten)**, throughput 9–272 tok/s, and
  NVFP4 vs BF16 isn't free — NVIDIA's own controlled comparison shows **WebVoyager 77.72→66.31 and DeepSWE
  24.65→18.2** on the quantized build (https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4;
  host table: https://mxchat.ai/nemotron-3-5-super-vl-pricing-chatbot-test/). Pin a host if your workload
  is browser/deep-SE agents.
- **Price is a moving median:** $0.15/$0.50 today (2026-11-15), $0.10/$0.40 briefly in late October, effective
  input far lower with caching ($0.068 weighted). Cheap tier: cheaper than most (297/389 OpenRouter priced
  models cost more per 1M in+out, https://overpayingforai.com/pricing/nemotron-3-5-super-vl-pricing/).
- **Quality floors that change decisions:** bottom-third Design Arena (1081–1160, 25.9–34.8% wins); vendor
  tau3-bench banking 17.78–18.88 (worst row in NVIDIA's own table); Terminal-Bench 4 near-zero; ARC-AGI-2
  1.9%; AA-Omniscience hallucination rate 30.0% (model card) — ground it in documents; LLMBenchmark
  #116/118 overall. Not for design taste, long-horizon finance tool use, or hard reasoning.
- **Verbosity:** 120M output tokens per AA Index task → **$0.54 per task** on AA's accounting despite the
  low rate (prior cycle, AA page 2026-11-01) — the bill comes from output volume, not sticker price.
- **Licensing:** OpenMDW-1.1 (commercial-friendly, "ready for commercial or non-commercial use") —
  (https://aitoolsreview.co.uk/insights/nvidia-nemotron-3-5-super-vl; model card). Data terms on OpenRouter
  follow the account's provider-logging/training toggles; the NVIDIA free endpoints' "trial use only, no
  confidential data" terms apply to the `:free` sibling, **not** this paid route
  (prior cycle file, https://openrouter.ai/docs/guides/privacy/provider-logging.md).
- **Recency:** released 2026-10-15 — one month old; NVIDIA's lineup churns fast (Bolt 74B same day, Hy4-like
  rapid sibling cadence), and Quant/price/provider sets have already changed twice in a month. Not EU
  in-region routable (prior cycle, https://openrouter.ai/nvidia/nemotron-3.5-super-vl/llms.txt).
- Split community reliability reports persist (pandas/numpy weak spots,
  https://www.reddit.com/r/LocalLLaMA/comments/1x7frdn/); review diffs — over-editing is documented above.

---

## Policy summaries

**tencent/hy4** — Tencent's Hy4 full release (2026-11-04; the `20261104` slug date is the listing date, and
the vendor "full release" claim means a new checkpoint over the Aug-28 preview: scaled pre/post-training plus
first-ever vision and computer use). Standing as of 2026-11-15: AA intelligence 34.6 (#2 in China),
OpenRouter coding #4/20 and orchestration #5/22 with 28.99T tokens in its first 11 days, Vals Index 59.35%
(#15/36), Design Arena upper-mid (~1250–1256, uicomponent weak at ~1180); but OpenRouter GPQA reads 83.2%
with no error bars against the preview's 89.8% ±0.6 — an unpaired-methodology disagreement, not a proven
regression. Pick it for cost-sensitive agentic/coding/orchestration work at half-price promo rates
($0.417/$1.251 vs list $0.834/$2.501, promo end unstated on OpenRouter); caveats that change decisions:
**weights, license and system card are still unpublished** (API-only despite "open-source" framing), it runs
on a single Tencent Cloud provider at ~54 tok/s with a 65,536 output cap and no EU in-region routing, cyber-
offensive capability was trained out, and Tencent's own chart concedes large frontier gaps on research math
and long-horizon repo work. Expect churn — Hy4 Flash and the weights are both promised.

**nvidia/nemotron-3.5-super-vl** — NVIDIA's paid route for the 120B-A12B open multimodal agent model
(released 2026-10-15; text + image + document + 2-min video in, OpenMDW-1.1, 1M context), spread across 10
OpenRouter hosts at $0.06–$0.30/M in and $0.35–$0.90/M out — the brief's $0.15/$0.50 is the median as of
2026-11-15. Standing: AA 13.6 on v5.0 (the drop from the launch-week "26" is the index rescale, not decay),
gpqa 86.8% / tau airline 72.9% (runs 2026-10-31), vendor SWE-bench Verified 71.1, fastest-in-class decode
and the best cheap lane for chart/document/screenshot work (independent: Plotly 70% at 12 s/question;
receipt-extraction tests ~91–98%) — while ranking #116/118 overall on LLMBenchmark, bottom-third on Design
Arena, ~0 on Terminal-Bench 4, and 17.8–18.9 on tau3-banking. Pick it as the budget vision/document/
screenshot-executor where latency and price dominate; pin a host (quant and max-output differ 32K–944K per
provider, and NVFP4 costs up to 11 points of WebVoyager), ground answers in source documents (30%
Omniscience hallucination rate), review diffs (documented over-editing), and never for design taste, prose or
hard reasoning. Demand mostly lives on the free sibling; the paid slug carries ~1.34T tokens over 11/30 days
(window ending 2026-11-14).