# DeepSeek V3.2 / Kimi K3 / Drex v1.5 / Nemotron 3.5 Lightning — model research (2026-10-18)

Scope: the four remaining top-15 gap models spanning DeepSeek legacy, a Moonshot premium tier, a
NVIDIA free route and an unselectable decision model, researched for a model-selection policy across
the five domains (research, writing, coding, orchestration, ops). Live data pulled from the OpenRouter
API (models catalog, endpoints) on **2026-10-18**; Artificial Analysis (AA) figures via OpenRouter's
benchmark feed (`as_of 2026-10-17`) and AA model pages; EQ-Bench Creative Writing v3 board data as
fetched 2026-10-17; community/press current to the same dates. Every factual claim carries a URL;
gaps are stated, not filled.

## Cross-cutting notes (read first)

**1. The supplied AA anchors are current — except the Nemotron one, which is wrong in the optimistic
direction.** The 2026-10-17 AA feed (350 rows, Intelligence Index **v4.3.2** scale) carries exactly the
supplied numbers: `moonshotai/kimi-k3-20260715` 43.6/76.2 (intel/coding) and
`deepseek/deepseek-v3.2-20251201` 21.5/44.2 — no rescale movement since the anchor snapshot. But the
brief's "**nemotron-3.5-lightning:free — NO AA row**" is a lookup miss: the feed row
`nvidia/nemotron-3.5-lightning-20260807` "Nemotron 3.5 Lightning" exists (intel **12.9**, coding
26.8, agentic 3.5), as does a live AA model page
(https://artificialanalysis.ai/models/nemotron-3-5-lightning). The gap is presumably the `:free`
variant slug not matching the permaslug. Stated here so the policy refresh does not record a false
coverage gap. The general rescale caveat from the batch-A file stands: pre-v4.3.2 press claims
("GPT-5 level", "scores 50") are old-scale; within one scale version ratios hold.

**2. EQ-Bench column ambiguity resolved.** The Creative Writing v3 data feed
(https://eqbench.com/creative_writing.html, board data fetched 2026-10-17) is
`model_name,elo_score,creative_writing_score,avg_length,vocab_complexity,slop_score,repetition_score`
— `slop_score` is the **6th** column. This settles the mapping the batch-A GLM-5.3 section hedged
("could not fully disambiguate the feed's column order"): GLM-5.3 slop 8.42, kimi-k3 9.70,
DeepSeek-V3.2 23.19 are column-correct. Cross-file correction to batch A: the **highest-ranked
open-weight model on the board is kimi-k3 (Elo 2082.3, #5/140), not GLM-5.3 (2075.0, #6/140)** —
kimi-k3's weights have been public since 2026-07-27 (https://www.kimi.com/blog/kimi-k3).

**3. OpenRouter's Decisions API is a separate lane.** Models whose output modality is `decisions`
(see the drex section) live on `/rankings/decisions` and a non-OpenAI request shape
(https://openrouter.ai/nace-ai/drex-v1.5). They are absent from `/api/v1/models` and cannot be routed
to as chat-completion models.

---

## 1. deepseek/deepseek-v3.2 (permaslug -20251201; sibling `-exp`)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Released 2025-12-01 as the production successor to V3.2-Exp (2025-09-29, which debuted DeepSeek
  Sparse Attention and cut DeepSeek API prices 50%+ — https://www.deepseek.com/en/news/v3-2-exp/).
  685B total / 37B active MoE, DSA + Multi-head Latent Attention, text-only, **MIT**
  (https://artificialanalysis.ai/models/deepseek-v3-2; tech report https://arxiv.org/abs/2512.02556;
  HF https://huggingface.co/deepseek-ai/DeepSeek-V3.2). One source says 671B total
  (https://deepseekai.guide/models/deepseek-v3-2/, third-party guide); AA and HF's transformers doc
  say 685B. Context: OpenRouter 163,840; AA says 128k; AWS Bedrock says 164K with **max output 8K**
  (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-deepseek-deepseek-v3-2.html) —
  provider context ceilings genuinely differ (below).
- "Thinking in tool-use": V3.2 was DeepSeek's first model integrating reasoning directly into
  tool-calling, trained on 1,800+ synthesized agent environments
  (https://api-docs.deepseek.com/news/news251201/). The high-compute sibling V3.2-Speciale (gold-medal
  IMO/IOI 2025 results, vendor-reported) ran on a temporary endpoint that expired 2025-12-15; a
  Speciale checkpoint survives on OpenRouter's AA feed at intel 14.5 only.
- Price (OpenRouter): default **$0.28/M in, $0.42/M out** (DeepSeek's historical V3.2 rates, also what
  AA's page quotes). **12 endpoints; output spread $0.31 (GMICloud, fp8) – $4.50 (Mara, SambaNova)** —
  and the expensive rows are the *worst* service shape: Mara/SambaNova cap context at **32,768** with
  7,168 max completion. Baidu (the default route) caps 131,072 ctx; DeepInfra fp4 caps completion at
  16,384. Quants fp4/fp8/unknown. Google Vertex ($1.68/M out) and AWS Bedrock still serve it
  (Bedrock lifecycle "Active", EOL no sooner than 2026-12-01).

### Benchmark standing
- **AA (v4.3.2): Intelligence 21.5, Coding 44.2** for the reasoning variant
  (`deepseek/deepseek-v3.2-20251201`, feed as_of 2026-10-17) — = the supplied anchor ✓, rank
  **#103/350** in the feed (coding #70/140). The non-reasoning variant scores **16 (estimated)**,
  #16/46 in its size/price class (https://artificialanalysis.ai/models/deepseek-v3-2). **AA marks the
  model deprecated**: "We only continue performance benchmarking for the default 10k input token
  workload… DeepSeek has launched a newer release, DeepSeek V4 Pro 0424. We suggest considering it
  instead" (same page). No index rescale has moved these numbers since the anchor snapshot; older
  press claims ("performs comparably to GPT-5", Dec 2025 launch page,
  https://www.deepseek.com/en/news/deepseek-v3-2/) are pre-rescale vendor framing against a different
  frontier.
- Position in DeepSeek's lineup (Oct 2026): **legacy, two generations behind — not a distinct tier.**
  It was the flagship `deepseek-chat`/`deepseek-reasoner` from 2025-12-01 until V4 (2026-04-24)
  (https://api-docs.deepseek.com/updates/); those legacy names were **retired 2026-07-24** and the
  first-party API now exposes only `deepseek-flash` (V4.1-Flash-1017) and `deepseek-v4-pro`
  (V4-Pro-0813) (https://api-docs.deepseek.com/; https://deepseek.ai/pricing, third-party guide).
  V3.2 survives only as MIT open weights on third-party routes (OpenRouter's 12 endpoints, Azure
  Foundry preview from 2025-12-15,
  https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-deepseek-v3-2-and-deepseek-v3-2-speciale-in-microsoft-foundry/4477549,
  and Bedrock). For scale: the V4.1-Flash rows in the same feed sit at 24.7 (non-reasoning entry) and
  39.5 (1017 checkpoint) — the V3.2 reasoning row (21.5) is ~3 points below the current cheap tier's
  floor and ~18 points below its checkpointed reasoning row.
- Independent evals on the HF card (Dec 2025 era): Terminal-Bench 2.0 **39.6**, GPQA Diamond **82.4**,
  Apex Agents 7 (https://huggingface.co/deepseek-ai/DeepSeek-V3.2). HF's transformers doc frames
  DSA's value as efficiency, with V3.2-Exp deliberately "on par with V3.1-Terminus" on quality
  (https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/deepseek_v32.md).
- **EQ-Bench Creative Writing v3: Elo 1515.0 (#60/140), rubric 16.28/20, slop 23.19** (board data
  2026-10-17, https://eqbench.com/creative_writing.html) — mid-board, below every V4 checkpoint
  except 0731... and below the April V4-Flash (1559), with a high slop score. The Speciale variant
  scores 1276.3 (#97). LMArena/Design Arena standing not found for this checkpoint.

### Opinions
- Zvi Mowshowitz lists "DeepSeek v3.2" among the "top 10 potential [DeepSeek] moments" of the cycle,
  with the verdict on that whole class: "Many of these were good models, but none fundamentally
  changed the game" (https://thezvi.substack.com/p/on-kimi-k3-its-capabilities-and-related).
- Launch reception on r/DeepSeek was warm but thin: "Golden age of open source models" (38 upvotes);
  a reseller-style account praises third-party access as "great and cheap pay as you go… far less
  censorship (compared to OpenRouter's APIs)" (https://www.reddit.com/r/DeepSeek/comments/1pba2w3/);
  a separate thread "DeepSeek V3.2 in the chat ui is great" (54 upvotes, surfaced via search, same
  subreddit).
- Technical hindsight on HN: "DeepSeek V3.2 which uses DSA only (sparse attention, but without
  compression from HCA and CSA) is a smaller model but uses **10x more memory at 1M context** compared
  to DS V4 Pro" (Palmik, https://news.ycombinator.com/item?id=48241620) — the KV-cache economics that
  made V4 cheap do not exist on V3.2.
- Retrospective framing from a third-party DeepSeek guide: "the right model to run from October 2025
  through April 2026", with the strengths as price, open weights and a then-generous 128K context,
  and the caveats "custom inference kernels (DSA is not a drop-in attention backend)" and no native
  vision (https://deepseekai.guide/models/deepseek-v3-2/).
- Community opinion at the margin is dated and quiet: this model has largely left the conversation
  (no modelsentiment page found; no active HN threads about it in 2026 found in search).

### Known for
The last V3-generation DeepSeek — the December 2025 "GPT-5-class at V3 prices" workhorse that
introduced Sparse Attention and thinking-in-tool-use, now a cheap legacy reasoning row.

### Caveats
Superseded twice (V4, V4.1-Flash) and **gone from DeepSeek's own API** (legacy names retired
2026-07-24) — every route is third-party with varying maintenance. AA deprecates the row; intelligence
21.5 is mid-table (#103/350 — the feed tail is hundreds of small/legacy models) and ~18 points below
the current V4.1-Flash checkpoint; the non-reasoning variant is worse (16 est.). Provider spread is a
trap: the $4.50/M-out rows cap context at 32K and the fp4 row caps completions at 16K; true context is
128–164K depending on host (Bedrock: 8K max output). 163K context and no vision input are a
generation behind; EQ-Bench prose is mid-pack (Elo 1515) with high slop (23.19). DSA-era serving
memory overhead is high vs V4 (HN link above). Fine-print: MIT license — the least restricted row of
this batch.

---

## 2. moonshotai/kimi-k3 (permaslug -20260715; also `:batch`)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Released 2026-07-16 (weights 2026-07-27), the first open model at **2.8T parameters / 104B active**
  (16 of 896 experts), built on Kimi Delta Attention + Attention Residuals, native multimodal, **1M
  context** (https://www.kimi.com/blog/kimi-k3;
  https://artificialanalysis.ai/models/kimi-k3). OpenRouter lists input modalities text+image+**video**
  while AA lists text+image only — one is wrong; treat video input as vendor-claimed but unverified on
  the routing layer. License: **Kimi K3 License** — "commercial use with restrictions"
  (https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE).
- Price: first-party **$3.00/M in, $15.00/M out** (AA, based on Kimi's API; cache discount 90%).
  OpenRouter default $0.304/$11.936 (the InferenceNet fp4 route). **26 endpoints; output spread $8.10
  (Sail Research, fp4) – $22.50 (Fireworks us/fast)** — the cheap end is entirely fp4/mxfp4 (Sail,
  Decart, Chutes, Wafer, InferenceNet, Makora, Relace…), fp8 only at Morph ($14.90) and BaseTen
  ($15.00); Amazon Bedrock, Alibaba ($17.25 out) and Moonshot first-party cluster at $15.00. Max
  completion varies: 943,718 on most, but Alibaba 131,072, Bedrock/BaseTen 128K/262K, Chutes 65,535;
  Parasail caps context at 1,000,000 vs the 1,048,576 claim. Fireworks us/fast showed **76.6%/95.6%
  1-day uptime** at fetch — route quality varies on the expensive end too.

### Benchmark standing
- **AA (v4.3.2, Max): Intelligence 44 (#4/120 — = the supplied 43.6 ✓), Coding 76.2 (#10/140 in the
  feed), Agentic 50 (#12/97)** (feed as_of 2026-10-17; https://artificialanalysis.ai/models/kimi-k3).
  In plain terms: top-5 intelligence on AA and a top-10 coding index — the strongest AA standing of
  the four models here by a wide margin. But: speed **42.2 t/s (#63/77, "notably slow")**, TTFT 3.75s,
  **$2.00 per Intelligence-Index task (#40/42 — second-most-expensive in class)**, verbosity 160M
  output tokens (#31/46, "somewhat verbose"). All Moonshot benchmarks are run at **maximum thinking
  effort** (https://www.kimi.com/blog/kimi-k3; Zvi, below) — the scores are the ceiling, not the
  default.
- **EQ-Bench Creative Writing v3: Elo 2082.3 (#5/140), rubric 16.85/20, slop 9.70** (board data
  2026-10-17) — above GLM-5.3 (2075.0), claude-opus-5-5 (2050.1) and every DeepSeek row; only
  gpt-6-astra, claude-fable-5-1, claude-opus-5 and gpt-6-sol rank higher (all frontier/preview rows).
  Radar strengths: Pacing, Avoids Purple Prose, Elegant Prose, Sentence Flow, Coherent; weaknesses:
  Strong Dialogue, Avoids Positivity Bias, Emotional Depth (EQ-Bench chart data). This is a decisive
  writing-domain fact for a model marketed on coding.
- LMArena: **#1 on Arena Frontend Code** at launch, ahead of Fable 5 and Sol
  (https://x.com/arena/status/2077824029126504525, cited in
  https://thezvi.substack.com/p/on-kimi-k3-its-capabilities-and-related); modelsentiment reads the
  boards as Arena text **#13/105**, Code Arena **#11/85**, AA coding #9/64, AA agentic #11/51, Epoch
  capabilities #15/87 (https://modelsentiment.com/m/kimi-k3). Harvey LAB-AA all-pass rate: first by a
  wide margin, 94.6% vs 93.6% criterion pass (Zvi, same URL). Debate Benchmark #2 behind Fable 5
  (Lech Mazur, via Zvi). Epoch Capabilities Index lands "exactly on the Chinese trend line", between
  Opus 4.6 and 4.7 (https://x.com/peterwildeford/status/2079052877801128237, via Zvi).

### Opinions
- Zvi Mowshowitz's long review is the canonical balanced take: "a very good model with excellent
  benchmarks… In aggregate it is several months behind the closed model frontier, at least four and my
  median guess is six"; "It is somewhat distilled. It likely outperforms on benchmarks relative to
  practical performance… Performance looks jagged"; "It is slow and appears hungry for tokens";
  "Kimi K3 Is Relatively Strongest At Typical Agentic Coding and 3D"
  (https://thezvi.substack.com/p/on-kimi-k3-its-capabilities-and-related). Same source: Ryan
  Greenblatt's forward-pass estimate puts pretrain quality "about halfway between Opus 4 and Opus
  4.5"; Dean Ball: "In agentic coding sessions, it seems pretty much on par with the best public models
  of Q1 2026… it also seemed very token hungry"; Ethan Mollick: "a very good model. But it is not a
  DeepSeek r1 moment."
- The cost complaint is the loudest signal: modelsentiment reads Reddit at **50/100, no clear lean**
  (56 opinions/7d, 20th of 24) with **cost praised by only 8% of 13 opinions** — while writing & tone
  sits at 62% and intelligence 70% (https://modelsentiment.com/m/kimi-k3). Representative: "$3/M input
  isn't as good a fit for me. GLM5.2/DSV4P get it done" (imog, via Zvi); "tried to use it on OR but the
  price makes it uncompetitive, no point using it when there's ant/oai subscriptions" (kyle, via Zvi);
  "For me, Kimi K3 seems fine… However, it is way too expensive"
  (https://www.reddit.com/r/kimi/comments/1vconet/). A price/provider analysis reaches the same
  conclusion: "pricing still high enough to force real provider shopping… token math matters more than
  usual" (https://deepinfra.com/blog/kimi-k3-pricing-providers-cost).
- Launch access was rocky — "Unusable right now via openrouter; slow, cuts outs all the time"
  (typebulb, via Zvi) — and Moonshot paused new subscriptions to prioritize existing members (via
  Zvi). Three months on, r/LocalLLaMA's headline thread reads "Kimi K3, three months after the hype:
  too big for almost anyone to run locally, and smaller models have already caught it", and
  r/SillyTavernAI reports "Nvidia NIM kimi 3 is gone and glm 5.3 is also going soon?" (both thread
  titles via https://modelsentiment.com/m/kimi-k3) — provider churn is real.
- Quality caveats from reviewers: "Best at Code, Worse at Honesty" — top of LMArena Frontend Code but
  with "a tripled price tag, a rising hallucination rate, and an unresolved distillation question"
  (https://awesomeagents.ai/reviews/review-kimi-k3); a third-party review frames the open question as
  "whether the price jump is earned"
  (https://www.buildfastwithai.com/blogs/kimi-k3-review). Security researcher s1r1us: "man, i am so
  disappointed about kimi k3. it performs worse than grok 4.5 on most of our security benchmarks" —
  with the working hypothesis that distillation from refusal-heavy Claude models left cyber jagged
  (via Zvi, same URL). Roleplay community rates its dialogue highly — "the best model I have used so
  far in dialogues after kimi k3" (r/SillyTavernAI comment, cited in
  research/2026-10-top15-a-deepseek-glm.md). Danielle Fong: "absorbed a lot of what make opus 4.7,
  4.8 difficult, but smart… seems to lie a bit" (via Zvi).
- Press: "the largest open-weight model in the world" and a coding/knowledge-work showcase
  (https://builtin.com/articles/kimi-k3-model); vendor case studies emphasize long-horizon coding,
  chip-design workflows, game/video creation and knowledge work
  (https://www.kimi.com/blog/kimi-k3).

### Known for
The premium open-weight all-rounder — top-5 AA intelligence, the best non-frontier coding index, and
(EQ-Bench's surprise) the best open-weight prose on the creative-writing board — picked when one model
must do hard coding, long-horizon agentic work and flagship-grade writing in the same breath.

### Caveats
**Price**: $3/$15 first-party and $8.10–22.50/M out on OpenRouter (2026-10-18) at output-weighted
authoring volumes; the $2/task AA cost is #40/42 in class and Reddit's cost praise is 8%. Slow and
token-hungry (42 t/s, TTFT 3.75s, max-effort thinking by default; billed thinking tokens inflate
output). Benchmarks are max-effort ceilings; Zvi's "several months behind the closed frontier" and the
distillation question mean practical performance trails the board numbers, and the model is jagged
(cyber notably weak per s1r1us). Cheap routes are all fp4/mxfp4 — pin fp8/first-party for quality;
completion caps drop to 128–262K on Alibaba/Bedrock/BaseTen, and Fireworks' us/fast routes had
<96% 1-day uptime at fetch. Custom license with commercial restrictions; no published safety
mitigations of note (Zvi). No local use in practice ("too big for almost anyone to run").

---

## 3. nvidia/nemotron-3.5-lightning:free (permaslug -20260807)

### Identity & pricing (OpenRouter API, 2026-10-18)
- Released 2026-08-11 (NGC NIM 2026-08-10/11): **30B total / 3.6B active** hybrid Mamba-2 + MoE +
  attention with Multi-Token Prediction, text-only, **OpenMDW-1.1** (commercial use OK), 1M context per
  NVIDIA's card (https://artificialanalysis.ai/models/nemotron-3-5-lightning;
  https://developer.nvidia.com/blog/nvidia-nemotron-3-5-lightning-delivers-fast-accurate-specialized-task-execution-for-long-running-agents/;
  https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b). **Distilled from Nemotron 3 Ultra**
  for the "execution layer of always-on agents": NVIDIA's pitch is planning to frontier models,
  execution to Lightning, with DFlash/DSpark spec-decode drafters and NVFP4 serving quantization
  (https://openrouter.ai/blog/insights/nemotron-3-5-lightning/;
  https://research.nvidia.com/labs/nemotron/Nemotron-3.5-Super-and-Lightning/). Full training recipe
  and data released (https://docs.nvidia.com/nemotron/nightly/nemotron/lightning35/README.html).
- OpenRouter: the paid slug has **4 providers** (Darkbloom int4 $0.12/M out, Io Net $0.13, DeepInfra
  bf16 $0.16, CoreWeave bf16 $0.20) — all cap context at **262,144** with completions 32K–235K. The
  **`:free` slug is a single sponsored endpoint** (Nvidia, nvfp4, $0), 1,000,000 ctx / 65,536 max
  completion. The upside-down context story (free 1M vs paid 262K) is documented by OpenRouter itself:
  "OpenRouter standard model | 262,144-token context on every current provider… OpenRouter free model |
  1,000,000-token context, up to 65,536 completion tokens" and "**structured outputs are not listed
  for the free model**" (https://openrouter.ai/blog/insights/nemotron-3-5-lightning/).

### Benchmark standing
- **AA anchor said "no AA row" — the row exists** (see cross-cutting note 1): AA feed 2026-10-17 gives
  Intelligence **12.9** (displayed 13, #28/141 in its small-model class — "amongst the leading models
  in intelligence" *for its size*), Coding **26.8** (#93/140), Agentic **3.5** (#67/97)
  (feed via OpenRouter; https://artificialanalysis.ai/models/nemotron-3-5-lightning). Headline AA
  properties are speed and cost: **298.2 t/s (#1/64 — the fastest model on AA's speed board)**, TTFT
  0.57s, $0.06/$0.20 median across providers, **$0.09 per Intelligence-Index task**, verbosity 120M
  tokens ("somewhat verbose" for its class).
- NVIDIA's card numbers (BF16, https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b): MMLU
  Pro 81.94, GPQA Diamond 75.44, SciCode 32.60, HLE 11.72, AA-Omniscience 17.50 — with NVFP4 a
  consistent ~1 point lower. NVIDIA claims the "accuracy-speed Pareto frontier for small open models"
  on AA and PinchBench 86% accuracy at 10,000 tasks completed 30% faster than Qwen3.6 35B
  (developer.nvidia.com blog, above).
- **EQ-Bench Creative Writing v3: Elo 1280.3 (#96/140), rubric 14.39/20, slop 22.47** (NVFP4 row,
  board data 2026-10-17) — near the bottom of the writing board. Not a prose model by any measure;
  Nemotron 3 Ultra scores 1692.4 on the same board. LMArena standing: not found. Design Arena (per
  batch B's Nemotron 3 Ultra data) is weak across the family.

### Opinions
- Community consensus is "good **for what it is**": a r/LocalLLM thread on running the 8-bit quant
  concludes "decent model for agentic tasks with good speed on affordable hardware but **not
  specifically good at coding**" (https://www.reddit.com/r/LocalLLM/comments/1vmp4w6/).
- A detailed local-serving benchmark (Intel Arc, Q4_0 GGUF + first-party MTP draft head) reports 91.9
  tok/s decode at 99.5% MTP acceptance in 22 GiB VRAM, and values it as "the 30B-A3B-class model that
  actually fits" where a rival (Ornith 1.5) failed on drafter alignment
  (https://github.com/srmiles/local-llm-benchmarks/blob/main/models/tested/nemotron-3.5-lightning-30b-a3b.md).
  Unsloth ships quants with thinking toggles (https://hub.docker.com/r/ai/nemotron-3.5-lightning).
- OpenRouter's own blog frames the use case as "the high-volume part of the workflow… a candidate
  execution model for agents that would otherwise send every call to a much larger reasoning model",
  and recommends ":free to test the model before adding paid traffic"
  (https://openrouter.ai/blog/insights/nemotron-3.5-lightning/) — i.e. the free route is for
  evaluation, not production commitments.
- The Nemotron-family strategic read from batch B applies: "The Nemotron project isn't supposed to be
  SOTA. It's supposed to provide proven training recipes" (HN, via
  research/2026-10-top15-b-mimo-nemotron-misc.md). No HN launch thread with substantial discussion
  of Lightning specifically was found; reception is quieter than for Nemotron 3 Ultra.

### Known for
The ultra-fast cheap execution model for agent pipelines — 298 t/s and $0.09/task at AA-13
intelligence — whose free OpenRouter route makes high-volume mechanical steps (routing, classification,
tool-call grind) effectively free while it lasts.

### Caveats
**The free route is not stable.** At fetch (2026-10-18 11:19 UTC) the single Nvidia free endpoint
reported **36.7% uptime over the previous 24h (76.7% over 30m)**; free endpoints are rate-limited by
OpenRouter, and the family precedent is that free routes end without warning (nemotron-3-ultra:free's
traffic collapsed 2026-10-16; see policy.json entry). The free route also lacks structured outputs and
caps completions at 65K; the paid routes cap context at 262K despite the 1M claim. Quality ceiling:
AA intelligence 12.9 and coding 26.8 — it is a distilled executor ("not specifically good at
coding", "not a design/frontend model" family-wide), EQ-Bench Elo 1280 with slop 22.47; anything
requiring real reasoning or prose should not land here. Serving note: the release ships NVFP4 as the
performance quant (int4 route exists on Darkbloom); verbose for its class (120M tokens per AA index
run). OpenMDW-1.1 is commercial-friendly.

---

## 4. nace-ai/drex-v1.5-20261009 — investigated; NOT selectable

### What it is (light-touch investigation, sources found)
- **Drex is a decision model, not a chat model.** Built by **Nace.AI** (a startup founded summer 2024
  selling "small models for professional work" — audit, accounting, billing — SOC 2 Type II;
  https://www.nace.ai/about): it reads a state (text/JSON) and named typed questions (choice / noul /
  ordinal score) and returns a **calibrated probability per option in one forward pass — nothing is
  ever generated** (https://www.nace.ai/drex.md;
  https://www.nace.ai/blog/introducing-drex, 2026-09-24). Vendor framing: "a chat model is System 2…
  A decision model is System 1" (https://www.nace.ai/drex).
- **The drex lineage**: hosted Drex 1.0 (2026-09-24) → 1.1 → **1.5 (2026-09-28)** → 2.0 (2026-10-06, a
  35B MoE with 3B active, `drex-latest` since 2026-10-12)
  (https://console.nace.ai/docs/drex/reference/models). The open weights for v1.5 (the
  `-20261009` permaslug ≈ the HF release, last modified 2026-10-10) are a ~9B model fine-tuned from
  **XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B** with a "Kev" pointer head, bf16 ≈18 GB + Q8_0 GGUF; it
  serves the TypeSafe-compatible `POST /v1/systemone` contract — "the same request and response format
  as the hosted Drex API and the open Drex DLM" (https://huggingface.co/nace-ai/drex-v1.5;
  https://github.com/nace-ai/drex-decision-models/blob/main/models/drex-v1.5/README.md). The
  TypeSafe/Jev connection matters for cross-referencing batch B's `typesafe/jev-1.13`: Jev is the
  decision model the Decision Index is named after, and Drex answers the same request shape.
- **Why it "ranks on the research boards"**: the **Decision Index** (a public leaderboard of
  decision-scoring benchmarks, chance-corrected; https://huggingface.co/spaces/multimodalart/jev-decision-index).
  Drex v1.5 scores **58.08 on Decision Index 0.3.1 (public), #1 under 10B parameters**, marginally
  ahead of Jev 1.13.0 (57.96 — inside the board's 0.9-point tie band); Drex 2.0 now leads at 61.25
  (https://huggingface.co/nace-ai/drex-v1.5; https://www.nace.ai/developers). Nace.AI's own runs of
  the official kit; other rows from the leaderboard. Hosted price $0.05/1M input tokens, output not
  billed (https://console.nace.ai/docs/drex/reference/models).

### Why it cannot be selected (the part the policy must record)
- Verified 2026-10-18: `nace-ai/drex-v1.5-20261009` is **absent from OpenRouter's `/api/v1/models`
  catalog** — the selection surface for the skill. A model page does exist
  (https://openrouter.ai/nace-ai/drex-v1.5) with one endpoint (DeepInfra, $0.04/M input, completion
  $0, 131,072 ctx) served over **OpenRouter's Decisions API**: "chat completions SDKs will not work
  with it"; its modality is literally `text->decisions`
  (https://openrouter.ai/api/v1/models/nace-ai/drex-v1.5/endpoints). Even if selectable, it cannot
  serve a chat/completion request — it returns probabilities over caller-supplied options and
  generates no text. OpenRouter also runs a decisions rankings board
  (https://openrouter.ai/rankings/decisions, JS-gated — standings not machine-readable from here).
- Secondary gaps, stated plainly: no community/press reviews found beyond Nace.AI's own curated
  testimonials (X/Discord quotes on https://www.nace.ai/developers); the HF model is deployed by **no
  inference provider** ("This model isn't deployed by any Inference Provider",
  https://huggingface.co/nace-ai/drex-v1.5); and the license was **changed from MIT to "Nace AI Open
  RAIL-M (Modified)"** around 2026-10-12 (HF file history,
  https://huggingface.co/nace-ai/drex-v1.5/tree/main) — RAIL-style use restrictions apply to the
  weights.

### Known for
The best-regarded small "System 1" decision/routing model — calibrated option probabilities in one
pass, #1 under 10B on the Decision Index ahead of TypeSafe's Jev — used for routing, classification
and step-selection inside agent loops.

### Caveats
Not on the chat surface at all (see above). Self-reported leaderboard numbers (Nace.AI ran the kit);
Drex 2.0 supersedes it on both the board (61.25) and the hosted API. No independent evaluation
coverage found; weights recently relicensed to RAIL-M; the OpenRouter page's $0.04/M figure and the
hosted $0.05/M figure disagree — the hosted docs are authoritative for the hosted route.

---

## Policy summaries

**deepseek/deepseek-v3.2.** Legacy December-2025 flagship (685B/37B MoE, MIT, ~164K ctx): AA-21.5
reasoning / coding 44.2 (2026-10-17 feed, unchanged — no rescale movement) — mid-table and ~18 points
under the v4.1-flash 1017 checkpoint — at third-party bargain prices ($0.28 default; $0.31–4.50/M out
across 12 endpoints, 2026-10-18). Pick it only for cheap bulk reasoning, mechanical drafting or ops scripting
where $/token dominates; not for writing (EQ-Bench Elo 1515, slop 23) or long-context work (163K cap;
the $4.50/M rows shrink to 32K ctx/8K out), and it is gone from DeepSeek's own API — weights survive
on third-party routes only.

**moonshotai/kimi-k3.** The premium open-weight all-rounder (2.8T/104B, 1M ctx): AA-43.6 intelligence
(#4/120) with coding 76.2 (#10/140) and agentic 50 — and the top open model on EQ-Bench Creative
Writing v3 (Elo 2082, #5/140, above GLM-5.3 and claude-opus-5-5). Pick it when one model must cover
hard coding, long-horizon agentic work, research synthesis and flagship writing/roleplay — but it
prices like a frontier model ($3/$15 first-party; $8.10–22.50/M out on OpenRouter, 2026-10-18, cheap
routes fp4/mxfp4), runs slow and token-hungry (42 t/s, $2/task #40/42 on AA), its benchmarks are
max-effort ceilings and it trails the closed frontier by months; avoid for bulk drafting, ops volume
and cyber-sensitive work.

**nvidia/nemotron-3.5-lightning:free.** A distilled 30B-A3B execution model (AA-12.9 intelligence but
**298 t/s, #1/64 on AA speed**, $0.09/task) aimed at the high-volume step layer of agent pipelines —
routing, classification, tool-call grind, cheap ops tasks — where its free single-provider route
(1M ctx, 65K out, nvfp4) costs nothing. The catch: the free route is rate-limited and demonstrably
unstable (36.7% 24h uptime at 2026-10-18; nemotron-3-ultra:free precedent shows free ends without
warning), lacks structured outputs, and the model is a weak reasoner and worse prose writer (EQ-Bench
Elo 1280) — pin the paid route ($0.12–0.20/M out, 4 providers, 262K ctx) for anything that must run.

**nace-ai/drex-v1.5-20261009 (NOT SELECTABLE — exit documentation).** A ~9B non-generative decision
model from Nace.AI (MiMo-V2.6-Distill-Qwen-9B + pointer head) that returns calibrated probabilities
over caller-supplied options via `POST /v1/systemone` — #1 under 10B on the Decision Index 0.3.1
(58.08, ahead of Jev 1.13.0), which is why it ranks on the research boards. It cannot be selected: it
is absent from OpenRouter's `/api/v1/models` catalog, its modality is `text->decisions` on OpenRouter's
separate Decisions API (chat-completions SDKs "will not work with it"), and it generates no text at
all — keep this summary only to document the exclusion, and note the MIT→RAIL-M relicensing and the
superseding Drex 2.0 (61.25 on the same board) if the topic returns.
