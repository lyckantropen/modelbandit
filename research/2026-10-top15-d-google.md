# Google family (Gemini 2.5/3.1 Flash-Lite, Gemma 4 26B A4B / 31B) — model research (2026-10-18)

Scope: the four Google-family gap models in the top-15 refresh — two proprietary Gemini lite tiers
and two open-weight Gemma 4 checkpoints — kept together as one family group. All OpenRouter prices
pulled live from `/api/v1/models/<id>/endpoints` on 2026-10-18; AA pages, HN threads and vendor
pages current as of the same date. Benchmark anchors supplied in the brief (first-party OpenRouter
AA feed) are verified or contradicted per model below.

## Cross-cutting notes: AA anchor verification, index scale, and Google's churn

- **Index scale**: all AA figures below are Intelligence Index **v4.3.2** (the scale named on every
  current AA page, e.g. https://artificialanalysis.ai/models/gemini-3-1-flash-lite). The three 2026
  anchors match current AA pages within rounding — 15.6→16, 16.7→17, 14.7→15 — so **no rescale
  correction is needed for these**; they are current-scale. The 2025-era anchor for
  gemini-2.5-flash-lite (10.4) does **not** reproduce (see §1) — that looks like estimate drift on an
  AA "Estimated" entry, not a rescale.
- **All four models are moving targets in Google's lineup.** AA marks both Gemini lite pages
  deprecated and points to successors: "Google has launched a newer release, Gemini 3.5
  Flash-Lite. We suggest considering it instead"
  (https://artificialanalysis.ai/models/gemini-3-1-flash-lite; the 2.5 page's banner names a
  "Gemini 2.5 Flash-Lite Preview (Sep '25)", https://artificialanalysis.ai/models/gemini-2-5-flash-lite).
  AA's Google sidebar as of 2026-10-18: Gemini 4 Argon 53, Gemini 3.8 Flash 41, Gemini 3.1 Pro
  Preview 30, **Gemini 3.5 Flash-Lite 22**, **Gemma 4 26B A4B 17**, **Gemma 4 31B 15**
  (https://artificialanalysis.ai/models/releases/gemma-4-26b-a4b). The writing tracker shows the same
  drift: Gemini 3.6/3.7/3.8 Flash now carry EQ-Bench Creative Writing Elos 1603–1748 while
  Gemini 3.1 Flash-Lite has only an LMArena Text row (1,433)
  (https://evy.so/compare/best-llms-for-writing/, updated 2026-10-12).
- **Not verifiable in this pass** (stated, not guessed): the brief's *coding* subscores (34.7 / 39.3
  / 43.4) come from the first-party AA feed; AA's public pages render category breakdowns via JS and
  no single "coding" figure was retrievable, so those three numbers are carried as given-first-party,
  cross-checked only for plausibility (their ordering matches Google's vendor coding benchmarks, see
  §3–4). EQ-Bench Creative Writing v3's table is JS-gated and its data-feed path 404s; the evy.so
  aggregate (which scrapes it weekly) shows **no Gemma 4 rows and no Gemini 2.5 Flash-Lite row** —
  so creative-writing Elos for these four genuinely don't exist on that board, dash means
  not-on-leaderboard per https://evy.so/compare/best-llms-for-writing/. modelsentiment.com returned
  404 for all four slugs; no sentiment-aggregator numbers are quoted anywhere below.

---

## 1. google/gemini-2.5-flash-lite (no dated permaslug; OpenRouter created 2025-07-22)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Released June 2025 (AA: 2025-06-17), GA July 2025
  (https://developers.googleblog.com/en/gemini-25-flash-lite-is-now-stable-and-generally-available/).
  Proprietary; AA classifies it as both **deprecated** and **"Estimate (independent evaluation
  forthcoming)"** — it has never been fully evaluated by AA
  (https://artificialanalysis.ai/models/gemini-2-5-flash-lite).
- 5 endpoints, **all first-party Google** (Vertex EU, Vertex, AI Studio, AI Studio flex, AI Studio
  priority). Output **$0.20/M (AI Studio flex) – $0.72/M (priority)**; standard $0.10 in / $0.40 out
  (matches AA's quote); cache reads from $0.005/M. **1M context** on every endpoint; max completion
  65,535 tokens. Full multimodal input (text+image+file+audio+video→text). Reasoning supported but
  with no `reasoning_effort` knob on OpenRouter.

### Benchmark standing
- Supplied anchor **intel 10.4 could not be verified.** AA's current pages show two entries:
  **(Reasoning) 9 estimated** and **(Non-reasoning) 7 estimated** on v4.3.2
  (https://artificialanalysis.ai/models/releases/gemini-2-5-flash-lite). Both are AA estimates, so
  the number moves as AA's estimator is refined; 10.4 is plausibly an earlier estimate or the
  OpenRouter feed's own reading. Flagging the discrepancy rather than resolving it.
- AA speed is the headline: **283.3 t/s non-reasoning (#2/59 in class)**, 366 t/s reasoning, TTFT
  **0.31s** (same pages) — among the fastest models AA tracks at any price. 90% cache discount.
  Knowledge cutoff Jan 2025.
- No EQ-Bench Creative Writing row and no LMArena Text row in the 2026-10-12 writing tracker
  (https://evy.so/compare/best-llms-for-writing/). Third-party stylometrics find its prose strongly
  Claude-flavored: "Gemini 2.5 Flash Lite writes 78% like Claude 3 Opus. Costs 185× less"
  (rival.tips model-similarity study, https://rival.tips/research/model-similarity).

### Opinions
- Beloved as a cheap workhorse before the sunset: "I still use 2.5 Flash Lite for a lot of my
  non-coding jobs, super cheap but great performance"
  (https://news.ycombinator.com/item?id=47235312); "I eventually settled on Gemini 2.5 Flash Lite as
  my workhorse, using it against structured data/vectors as a chatbot. It was cheap, good enough,
  and most importantly, fast — but it's now being sunset and I'm not sure where to go"
  (https://news.ycombinator.com/item?id=49121047).
- Real deployments in the wild: Asxiv.org ("Ask ArXiv papers questions through chat") is built on
  it ("switch to 2.5 pro for better results", 161 pts,
  https://news.ycombinator.com/item?id=45212535); a self-hosted memory MCP routes "near-free" graph
  extraction to it, 85.4% entity-extraction accuracy in their split-model setup
  (https://news.ycombinator.com/item?id=47053534); a /pol/ politeness rewriter uses it for concise
  style transfer (https://news.ycombinator.com/item?id=45084368).
- The deprecation itself drew a small backlash: "there is a whole world of tasks for which Flash
  2.5-lite was sufficiently intelligent. Given Google's deprecation policy, there will soon be no way
  to get that intelligence at that price"
  (https://news.ycombinator.com/item?id=47236092); a commenter pins the shutdown at "22nd July 2026"
  (https://news.ycombinator.com/item?id=47236133). Its June-2025 launch thread ran 368 points/222
  comments (https://news.ycombinator.com/item?id=44300717).

### Known for
The near-free, near-instant multimodal volume tier — translation, moderation, extraction and
classification at ~283–366 t/s — that everyone used to reach for and Google is now retiring.

### Caveats
Deprecated: AA no longer benchmarks it beyond one workload and Google's own sunset was scheduled for
2026-07-22 (community-cited), though Google endpoints on OpenRouter were still live at the
2026-10-18 snapshot — treat availability as borrowed time. Its intelligence is AA-estimated at 7–9
(brief's 10.4 unverified): fine for verifiable mechanical transforms, wrong for anything requiring
judgment. No thinking-effort control on OpenRouter, 65,535-token output cap, and Jan-2025 knowledge
cutoff. EQ-Bench/LMArena have no rows — its writing reputation rests on the stylometric
"Claude-like" finding, not measured creative quality.

---

## 2. google/gemini-3.1-flash-lite (permaslug -20260507; AA anchor -preview-20260303)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Preview 2026-03-03 ("Built for intelligence at scale",
  https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-lite/),
  GA 2026-05-07/08 (https://cloud.google.com/blog/products/ai-machine-learning/gemini-3-1-flash-lite-is-now-generally-available).
  Proprietary; "Google's GA high-efficiency multimodal model optimized for low-latency, high-volume
  workloads… lightweight agentic" (OpenRouter description).
- 8 endpoints, **all first-party Google** (Vertex global std/flex/priority, Vertex EU, Vertex US,
  AI Studio std/flex/priority). Output **$0.75/M (flex) – $2.70/M (priority)**; the standard tier is
  $0.25 in / $1.50 out (AA quotes the same, https://artificialanalysis.ai/models/gemini-3-1-flash-lite).
  1M context everywhere; max completion 65,536. Text+image+video+audio+file input; **native
  Google-Search tool**; `reasoning_effort` supported. Watch the flex tiers: Google Vertex global flex
  showed **51% uptime over 24h** at snapshot time — flex = spare capacity, throttled by design.

### Benchmark standing
- **Anchor verified**: AA scores it **16** on v4.3.2 (vs supplied 15.6 ✓), #71/171, above class
  median 13 (https://artificialanalysis.ai/models/gemini-3-1-flash-lite). But the page is the
  **deprecated** one: "Google has launched a newer release, Gemini 3.5 Flash-Lite. We suggest
  considering it instead" (AA gives 3.5 Flash-Lite 22 on the Google sidebar).
- AA performance profile: **363.5 t/s (#7/149)**, TTFT 4.16s (high end — thinking time included),
  $0.06/task, **verbosity 54M output tokens (#23/66 — "fairly concise", median 96M)**. The supplied
  **coding 34.7** could not be independently verified (see cross-cutting note).
- Vendor claims (launch post, https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-lite/):
  "outperforms 2.5 Flash with a 2.5× faster Time to First Answer Token and 45% increase in output
  speed, according to the Artificial Analysis benchmark"; **LMArena Elo 1,432**, GPQA Diamond 86.9%,
  MMMU Pro 76.8%, "even surpassing larger Gemini models from prior generations like 2.5 Flash".
  The Arena number cross-checks: the 2026-10-12 writing tracker shows **LMArena Text 1,433**
  (https://evy.so/compare/best-llms-for-writing/). No EQ-Bench Creative Writing row exists for it
  (same tracker) — its writing ceiling is unmeasured.

### Opinions
- The launch thread (60 pts/30 comments, https://news.ycombinator.com/item?id=47234962) is dominated
  by **price-hike backlash**: "$0.25 IN / $1.50 OUT vs. Gemini 2.5 Flash-Lite $0.10 IN / $0.40 OUT"
  (https://news.ycombinator.com/item?id=47235369); "That's a 150% increase in input costs and 275%
  increase on output costs over the same sized previous generation"
  (https://news.ycombinator.com/item?id=47236090); "What the fuck is this price hike? … I'm gonna
  switch some workflows to qwen3.5… Can we get flash lite lite please?"
  (https://news.ycombinator.com/item?id=47237891). One thread quotes Google's Logan Kilpatrick
  answering "I think open source models like Gemma might be the answer here" for the missing cheap
  tier (same thread).
- A startup's pricing complaint generalizes it: "We priced an enterprise contract using Flash 1.5
  pricing last summer, and today that contract would be unit economic negative if we used Flash 3.
  Flash 2.5 and now Flash 3.1 Lite barely breaks even. I predict open-source models and fine-tuning
  are going to make a real comeback this year for economic reasons"
  (https://news.ycombinator.com/item?id=47235791).
- **The reasoning-cost trap** is the most operationally important comment: "Do not use 3.1
  Flash-Lite with HIGH reasoning, it reasons for almost max output size, you can quickly get to
  millions of tokens of reasoning in a few requests" (aibenchy.com operator,
  https://news.ycombinator.com/item?id=47239608; their effort-level comparison:
  https://aibenchy.com/compare/google-gemini-3-1-flash-lite-preview-low/google-gemini-3-1-flash-lite-preview-medium/google-gemini-3-1-flash-lite-preview-high/google-gemini-3-flash-preview-low/).
  Counterpoint on total cost: AA found 3.1 FL (reasoning) used "fewer than half of the tokens of 2.5
  Flash-Lite (reasoning)" but was "20% more expensive to run for their complete Intelligence index
  benchmark" — cost is task-dependent, not token-price-dependent
  (https://news.ycombinator.com/item?id=47236248).
- **Transcription is the praised niche**: a dictation-app developer benchmarked it at "1.8× faster
  than Gemini 3 Flash… ~$0.50/mo for heavy users (10h+ transcription)… Close to SOTA audio
  understanding and formatting instruction following… 100+ languages"
  (https://news.ycombinator.com/item?id=47235912, https://ottex.ai); a daily bilingual user: "I
  haven't seen any model that provides better overall quality in terms of understanding, custom
  dictionary support, instruction following, and formatting. It's the best STT model in my
  experience… Flash Lite is much better [on latency] than Gemini 3 Flash"
  (https://news.ycombinator.com/item?id=47236467).
- Agentic hopes were conditional: "Unfortunately 2.5-flash and therefore 2.5-flash-lite failed some
  of my agentic workflows. If 3.1-flash-lite can do the job, this solves basically all latency issues
  for agentic workflows" (with published workflow tests,
  https://news.ycombinator.com/item?id=47235401, https://upmaru.com/llm-tests/simple-tama-agentic-workflow-q1-2026).
  A hybrid on-device startup uses it as the cloud fallback tier — routing only 15–35% of queries to
  it lets a Gemma-4-E2B match it on most benchmarks (191-pt Show HN,
  https://news.ycombinator.com/item?id=49010782); a privacy-focused developer found it clearly
  better than on-device Gemma 4 on long inputs ("Cloud based models had no problems even Gemini 3.1
  Flash-Lite… do a lot better and a way faster",
  https://news.ycombinator.com/item?id=48434992). A solo game dev runs live game-master calls on it
  because "these models are SO cheap to run"
  (https://news.ycombinator.com/item?id=47275483).

### Known for
Google's fast, fairly concise, fully multimodal volume tier — the default cheap cloud call for
transcription, translation, moderation and light agentic/tool work at ~364 t/s, now sold at a
lite-model-unfriendly price.

### Caveats
Price is 3–4× its predecessor ($0.25/$1.50 list; $0.75–2.70/M out across OpenRouter tiers) and the
community's main complaint; pin `reasoning_effort` to low/medium — high effort "reasons for almost
max output size" and can burn millions of tokens across a few requests. AA has already deprecated it
in favor of Gemini 3.5 Flash-Lite (int 22), and Gemini 3.6–3.8 Flash now out-write it on EQ-Bench
(1603–1748 Elo vs its absence). Flex-tier endpoints are throttled (51% uptime seen); TTFT 4.16s
with thinking; no measured creative-writing score — utility prose and structure, not literary voice.

---

## 3. google/gemma-4-26b-a4b-it (permaslug -20260403)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Released 2026-04-02 (HN launch, https://news.ycombinator.com/item?id=47616361; technical report
  arXiv 2607.02770 published Jul 2026, https://huggingface.co/google/gemma-4-26B-A4B-it). **MoE:
  25.2B total / 3.8B active**, 8-of-128 experts + 1 shared; text+image(+video-frames)→text; 256K
  context; **Apache 2.0** (HF card and AA agree:
  https://huggingface.co/google/gemma-4-26B-A4B-it,
  https://artificialanalysis.ai/models/releases/gemma-4-26b-a4b). One dissenting community claim
  says "Gemma model use remains subject to the Gemma terms"
  (https://news.ycombinator.com/item?id=49010782) — the model card's license tag is apache-2.0, so
  treat Apache 2.0 as the operative license but re-read terms before shipping a product.
- 13 endpoints (DeepInfra, CoreWeave, Cloudflare, Novita, Parasail, SiliconFlow, DekaLLM, NextBit,
  Io Net, Makora, Venice, Darkbloom, Google Vertex). Output **$0.18/M (Makora) – $0.60/M (Google)**.
  Quants: **bf16** (CoreWeave, DekaLLM, NextBit, Io Net, Parasail, Novita, Venice), **fp8** (DeepInfra,
  SiliconFlow), unknown (Darkbloom, Makora, Cloudflare, Google). Context caps vary: Darkbloom 131K,
  Makora/Cloudflare/Venice 256,000 vs the 262,144 claim; max completion from 8,192 (Venice) to
  235,929. Google's own Vertex endpoint was paused (status −2, 91% 1-day uptime) at snapshot.

### Benchmark standing
- **Anchor verified**: AA shows **(Reasoning) 17 (estimated)** and (Non-reasoning) 13 (vs supplied
  16.7 ✓) — both AA **estimates** ("Estimate (independent evaluation forthcoming)",
  https://artificialanalysis.ai/models/releases/gemma-4-26b-a4b). AA's sidebar puts the release at 17
  — **above Gemma 4 31B's 15**. Speed 68 t/s reasoning / 98 t/s non-reasoning; blended price ~$0.16–0.19.
  The supplied **coding 39.3** is unverified on AA's JS-gated pages, but the ordering (below 31B's
  43.4) matches Google's vendor table: LiveCodeBench v6 **77.1%**, Codeforces Elo **1718** vs the
  31B's 80.0%/2150 (https://huggingface.co/google/gemma-4-26B-A4B-it).
- Vendor card (same HF page): MMLU Pro 82.6%, AIME 2026 88.3%, GPQA Diamond 82.3%, τ2 (avg-3) 68.2%,
  HLE 8.7% (17.2% with search), MMMU Pro 73.8%, MRCR v2 8-needle-128k **44.1%** (vs Gemma 3 27B's
  13.5%); "The A in 26B A4B stands for active parameters… runs almost as fast as a 4B-parameter
  model"; "excellent choice for fast inference compared to the dense 31B". DeepMind positions the
  family as "Our most intelligent open models, built from Gemini 3 research"; its own chart gives
  **LMArena text 1,441** (thinking, as of 2026-04-02) and τ2-retail 85.5%
  (https://deepmind.google/models/gemma/gemma-4/).
- Local-hardware reality checks (these are what the community benchmarks, not AA): llama.cpp fits
  ~200K context on a 24GB RX 7900 XTX at **100+ tok/s** (UD-Q4_K_XL,
  https://news.ycombinator.com/item?id=47616361); ~50 tok/s on an M1 Max 64GB (same thread); 5–6
  tok/s on an 8GB M2 MacBook Air by streaming experts from SSD
  (https://news.ycombinator.com/item?id=49098510); 5 tok/s on a 13-year-old Xeon with no GPU
  (https://news.ycombinator.com/item?id=48922434). Unsloth: 4-bit ≈ 16–18GB, 8-bit ≈ 28–30GB,
  QAT variants "reduce memory requirements around 3×"
  (https://unsloth.ai/docs/models/gemma-4).

### Opinions
- The launch was an event: **1,812 points / 474 comments**
  (https://news.ycombinator.com/item?id=47616361). Unsloth's maintainer: "Gemma-4 haha — it's sooooo
  good!!!" and names Google the most cooperative lab to work with (same thread). "Best thing is that
  this is Apache 2.0 (edit: and they have base models available)… the 31B seems to be strong in
  agentic stuff. 26BA4 stands somewhere in between, similar VRAM footprint, but much faster
  inference" (same thread).
- Coding reception is positive at the margin: "for writing some Nix, I'm VERY impressed — seems
  significantly better than qwen3.5-35b-a3b" (UD-Q4_K_XL, same thread); "I ran Gemma 4 as a local
  model in Codex CLI" (285 pts, https://news.ycombinator.com/item?id=47744255); "Running Gemma 4
  locally with LM Studio's new headless CLI and Claude Code" (407 pts,
  https://news.ycombinator.com/item?id=47651540).
- **Benchmark skepticism is the main dissent**: "Featuring the ELO score as the main benchmark in
  chart is very misleading. The big dense Gemma 4 model does not seem to reach Qwen 3.5 27B dense
  model in most benchmarks… the release is a bit disappointing"
  (https://news.ycombinator.com/item?id=47616361); "Doing great on public datasets and
  underperforming on private benchmarks is not a good look"; "Wild differences in ELO compared to
  [Google's] graph" (same thread) — the launch chart's Elo framing vs HF-card numbers confused even
  enthusiasts. Treat Google's Elo headline (1,441) as vendor-curated.
- Ecosystem velocity is real: QAT int4 models (406 pts,
  https://news.ycombinator.com/item?id=48414653), multi-token-prediction drafters "1.4–2.2× faster
  inference without accuracy loss" (687 pts, https://news.ycombinator.com/item?id=48024540,
  https://unsloth.ai/docs/models/mtp.md), 402 quantizations and 195 finetunes already on its HF tree,
  10.5M downloads/month (https://huggingface.co/google/gemma-4-26B-A4B-it). On-device phone runs
  (868 pts, https://news.ycombinator.com/item?id=47652561) and Ollama Mac-mini setup guides (330
  pts, https://news.ycombinator.com/item?id=47624731) round out the local halo.

### Known for
The open-weight speed/quality tradeoff of the moment — 3.8B-active MoE that runs like a 4B model but
answers like a small frontier model, the default local coding/agentic pick at ~16–18GB (4-bit).

### Caveats
AA intelligence is *estimated* (17/13) and the community openly disputes Google's benchmark framing
vs Qwen 3.5 (dense 27B/35B-A3B); its long-context is mediocre (MRCR 44.1% @128k vs 31B's 66.4%) so
don't pick it for document-heavy research. Provider spread matters: fp8 vs bf16 vs unknown quants,
131K-context caps on some endpoints (Darkbloom), max-completion as low as 8,192 (Venice), and
Google's own endpoint was paused at snapshot. Thinking is toggled via `<|think|>`/chat-template flags
that behaved inconsistently in llama.cpp at launch (`--reasoning off` eventually required,
https://news.ycombinator.com/item?id=47616361); Google's recommended sampling is temp 1.0 / top_p
0.95 / top_k 64 (https://unsloth.ai/docs/models/gemma-4).

---

## 4. google/gemma-4-31b-it (permaslug -20260402)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Released 2026-04-02 alongside the family; **dense 30.7B**, text+image(+video)→text, 256K context,
  **Apache 2.0** (https://artificialanalysis.ai/models/releases/gemma-4-31b,
  https://huggingface.co/google/gemma-4-26B-A4B-it [family card]).
- 15 endpoints (CoreWeave, Venice, Chutes, DeepInfra ×4 tiers, Crusoe, Friendli, Novita, Parasail,
  Io Net, SambaNova, ModelRun, SiliconFlow). Output **$0.32/M (DeepInfra flex) – $1.15/M
  (SambaNova)**. Quants: **fp4** (CoreWeave, Venice, Chutes, DeepInfra turbo, ModelRun), **fp8**
  (Parasail, DeepInfra, SiliconFlow), **bf16** (Crusoe, Novita), unknown (Friendli, Io Net,
  SambaNova). Context caps: Chutes and SambaNova run 131K vs the 262,144 claim. Provider health was
  poor at snapshot: Chutes/Novita/Io Net/SiliconFlow/SambaNova endpoints showed degraded status
  (−5/−2; Novita 67% and SiliconFlow 67% 1-day uptime) — routing resilience matters here.

### Benchmark standing
- **Anchor verified**: AA shows **(Reasoning) 15** and (Non-reasoning) 14 (vs supplied 14.7 ✓),
  https://artificialanalysis.ai/models/releases/gemma-4-31b — i.e. **below the 26B A4B's
  estimated 17** on composite intelligence, even though the supplied **coding 43.4 is the highest of
  the four** and matches the vendor coding table (LiveCodeBench v6 **80.0%**, Codeforces Elo
  **2150**, https://huggingface.co/google/gemma-4-26B-A4B-it). The split is real: dense 31B wins
  coding/agentic depth, the MoE wins AA's composite estimate.
- AA speed: **35.2 t/s (#54/64 — the slowest of the four)**, non-reasoning 49 t/s, non-reasoning
  TTFT 1.84s; AA rates it **#1/24 on cost per task** in class; verbosity 49M tokens (#10/27).
- Vendor card: MMLU Pro **85.2%**, AIME 2026 89.2%, GPQA Diamond **84.3%**, τ2 (avg-3) **76.9%**
  (DeepMind quotes τ2-retail **86.4%**, https://deepmind.google/models/gemma/gemma-4/), HLE 19.5%
  (26.5% with search), MMMU Pro 76.9%, and the family's best long context: **MRCR v2 8-needle-128k
  66.4%** vs 26B A4B's 44.1% (https://huggingface.co/google/gemma-4-26B-A4B-it). DeepMind's launch
  chart claims **LMArena text 1,452** (thinking, as of 2026-04-02) — vendor-cited and contested (see
  §3 opinions). No EQ-Bench Creative Writing or LMArena row in the 2026-10-12 writing tracker
  (https://evy.so/compare/best-llms-for-writing/).

### Opinions
- Local-deployment love is concrete: "Indexing a year of video locally on a 2021 MacBook with
  Gemma4-31B (50GB swap)" — 471 points, 142 comments
  (https://news.ycombinator.com/item?id=48222733, https://blog.simbastack.com/indexed-a-year-of-video-locally/);
  an OCR/translation pipeline for 19th-century land records runs on Gemma GGUFs
  (https://news.ycombinator.com/item?id=47616361); "Just switched from 3.1 Flash Lite to Gemma-4 31B
  on the AI Studio API since there is a generous 1500/day on non-billed projects. It's doing
  fantastic" (same thread) — a direct in-family substitution away from the Gemini lite tier.
- Task niches get specific praise: "Give Gemma 31B a shot for translation, it does a very good job
  at that given its size" and "the 31B seems to be strong in agentic stuff"
  (https://news.ycombinator.com/item?id=47616361); its UD-Q8_K_XL quant produced usable web-search
  summarization at 4.9 tok/s on an M1 Max (same thread).
- Hardware caveats travel with the praise: "Try 26B first. 31B seems to have very heavy KV cache…
  there's static SWA cost of 3.6GB… even then barely enough for 64K for 24GB VRAM"
  (https://news.ycombinator.com/item?id=47616361); Unsloth rates it "currently the strongest Gemma 4
  model. Pick it for maximum quality if you have enough memory and can accept slightly slower
  speeds" (https://unsloth.ai/docs/models/gemma-4).
- The same benchmark-skeptic thread applies: Google's Elo-centric launch chart called "very
  misleading" and "wild differences in ELO compared to [Google's] graph" — with a commenter
  concluding "the benchmarks showing the 'old' Chinese qwen models performing basically on par…
  kinda has me thinking the google models are DOA no?"
  (https://news.ycombinator.com/item?id=47616361). Dissent exists; taste-testing beats the chart.

### Known for
The strongest open Gemma — dense 31B coding depth (Codeforces Elo 2150, coding anchor 43.4) plus the
family's best long-context and translation, runnable locally at 17–20GB (4-bit) under Apache 2.0.

### Caveats
The slowest of the four (AA 35–49 t/s) with heavy KV-cache overhead (3.6GB static SWA; ~4.9GB at 16K
context in llama.cpp) — reserve it for quality-first work, not latency-sensitive or bulk pipelines.
AA composite (15) sits below the cheaper 26B A4B's estimate (17) — pay for 31B specifically when
coding/agentic depth and long context matter. fp4 quant routes dominate several providers (CoreWeave,
Venice, Chutes, DeepInfra turbo, ModelRun) — pin bf16/fp8 for quality — and over half its OpenRouter
endpoints were degraded at the 2026-10-18 snapshot. Google's LMArena-chart framing is vendor-curated
and contested on HN; no measured creative-writing score exists.

---

## Verdict sanity-check (brief-supplied claims)

- **"AA anchor gemini-2.5-flash-lite intel 10.4" — NOT REPRODUCED.** AA (v4.3.2, 2026-10-18) shows 9
  (Reasoning, estimated) and 7 (Non-reasoning, estimated). Both entries are AA estimates, so drift is
  expected; 10.4 is an earlier-estimate or feed-side reading. Don't quote 10.4 as current AA.
- **"gemini-3.1-flash-lite-preview-20260303 intel 15.6, coding 34.7" — intel VERIFIED (16 on AA,
  v4.3.2), coding unverifiable on public pages.** The preview permaslug is the right anchor: the
  preview launched 2026-03-03 and GA'd 2026-05-07. The number is now a deprecated-entry score
  (successor Gemini 3.5 Flash-Lite = 22).
- **"gemma-4-26b-a4b-it-20260403 intel 16.7, coding 39.3" — intel VERIFIED (17 estimated on AA),
  coding unverifiable but ordering-consistent** with LiveCodeBench/Codeforces (77.1% / 1718 vs
  31B's 80.0% / 2150).
- **"gemma-4-31b-it-20260402 intel 14.7, coding 43.4" — intel VERIFIED (15 on AA), coding
  unverifiable but the highest of the four and consistent with vendor coding benchmarks.**
- Price ranges and endpoint counts in the brief all match the live OpenRouter API exactly
  (5/8/13/15 endpoints; out $0.20–0.72 / $0.75–2.70 / $0.18–0.60 / $0.32–1.15 per M).

---

## Policy summaries

**google/gemini-2.5-flash-lite.** Google's June-2025 near-free multimodal volume tier (AA int 7–9
*estimated*, 2026-10-18; $0.20–0.72/M out on 5 first-party endpoints, 1M ctx, ~283–366 t/s) — pick
it only for high-volume, verifiably mechanical work: translation, moderation, classification,
research triage, ops log summarization, cheap orchestration sub-calls; not for coding or judgment.
It is deprecated (Google sunset scheduled 2026-07-22; AA stopped benchmarking it) with no measured
writing score, so legacy pipelines only — new work should go to 3.1 Flash-Lite or Gemma 4.

**google/gemini-3.1-flash-lite.** The current GA lite tier (AA-16, LMArena Text 1,433, ~364 t/s, 1M
ctx, audio+video in, native search tool) at $0.75–2.70/M out — the default cheap call for
transcription (community: "best STT model in my experience"), translation, utility writing,
moderation, and fast tool-using orchestration. Pin `reasoning_effort` low/medium (high effort "reasons
for almost max output size" and can burn millions of tokens), mind flex-tier throttling and the 3–4×
price vs 2.5 Flash-Lite, and note AA already points to Gemini 3.5 Flash-Lite (int 22) as its
replacement.

**google/gemma-4-26b-a4b-it.** Apache-2.0 MoE (25.2B/3.8B active) that runs like a 4B model and
scores like a small frontier one (AA 17 est./13 non-reasoning; coding 39.3 per first-party feed;
$0.18–0.60/M out, 256K ctx) — the local/community default for coding assistance, agentic tool use,
and private ops automation on a budget (4-bit ≈ 16–18GB, 100+ tok/s on a 24GB GPU). Skip it for
long-document research (MRCR 44.1% @128k) and pin bf16/fp8 routes (fp8/bf16/unknown quants, 131K
caps and 8K completion limits on some providers); its AA score is estimated and HN disputes Google's
benchmark framing vs Qwen 3.5.

**google/gemma-4-31b-it.** The strongest Gemma 4 — dense 30.7B with the best coding of the four
(coding 43.4 first-party; LiveCodeBench v6 80.0%, Codeforces Elo 2150), best long context (MRCR
66.4% @128k) and praised translation, at $0.32–1.15/M out or free locally (4-bit ≈ 17–20GB, Apache
2.0). Pick it for quality-first coding, agentic/ops work, and long-document reading/translation where
speed doesn't matter — it is the slowest of the four (AA 35–49 t/s) with heavy KV-cache costs, fp4
routes dominate several endpoints, provider uptime was poor at the 2026-10-18 snapshot, and its
AA-15 composite trails the cheaper 26B A4B's estimate, so buy it for depth, not headline intelligence.
