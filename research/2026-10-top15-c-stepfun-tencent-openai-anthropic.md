# OpenRouter top-15 research (batch C): StepFun, Tencent, OpenAI Luna, Anthropic

Research date: 2026-10-17. Model-selection policy context: writing/research-focused; prose
reception is a first-class input. Popularity context: top-15 by OpenRouter traffic, Oct 2026.

Verification of supplied Artificial Analysis (AA) figures (AA Intelligence Index v4.3.2):

| Model | Supplied AA intel | Verified on AA | Note |
|---|---|---|---|
| stepfun/step-5-preview | 43.7 | 44 ([AA model page](https://artificialanalysis.ai/models/step-5), rounded display; #3 open-weights per [AA FAQ](https://artificialanalysis.ai/models)) | consistent |
| tencent/hy4-preview | — | **no AA page found** (slugs `hy4`, `hy4-preview`, `tencent-hy4` all 404 on 2026-10-17) | AA coverage unavailable; stated below |
| tencent/hy3 | — | 25 ([AA model page](https://artificialanalysis.ai/models/hy3)) | extends supplied data |
| openai/gpt-6-luna | 38.1 | 38 for "Max" ([AA model page](https://artificialanalysis.ai/models/gpt-6-luna)) | consistent |
| anthropic/claude-opus-5.5 | 57.6 | 58 for "Max, Default Fallback" ([AA model page](https://artificialanalysis.ai/models/claude-opus-5-5)) | consistent; #1 of 134 evaluated per [AA](https://artificialanalysis.ai/models) |

Method notes: benchmark standing from AA / LMArena (via the [BenchLeader mirror](https://www.benchleader.com/benchmarks/lmarena_text) of the CC BY 4.0 lmarena dataset) / [Design Arena](https://designarena.ai/leaderboard) embedded leaderboard data / vendor model cards. Opinions from Hacker News threads (via Algolia API), Reddit aggregation (modelsentiment), and press/blog reviews. Where sources disagree, both readings are shown. LMArena and arena.ai are Cloudflare-gated to direct fetches; Design Arena and LMArena Text figures were read from mirrors/embedded data and may lag the live boards.

---

## 1. stepfun/step-5-preview

First-party: StepFun's "flagship model for agentic work", previewed 2026-09-18 ([AA FAQ](https://artificialanalysis.ai/models/step-5)); 600B total / 27B active sparse MoE, 1M context, text+image+**video** input ([StepFun docs](https://platform.stepfun.ai/docs/en/guides/models/step-5-preview)). Open weights landed 2026-10-15 (FP8 + BF16 checkpoints, [HF card](https://huggingface.co/stepfun-ai/Step-5-Preview)). StepFun is the Shanghai lab founded 2023 by ex-Microsoft researchers ([Kompozy review](https://kompozy.io/reviews/stepfun-step-5-preview)).

### Benchmark standing

- **AA Intelligence Index 44**, #3 among open-weights models overall (behind MiMo-V2.6-Pro 46 and GLM-5.3 Max 45) and #3/120 in its class ([AA model page](https://artificialanalysis.ai/models/step-5), [AA models page](https://artificialanalysis.ai/models)). Speed 91.1 t/s (StepFun API), TTFT 2.19s, cost $1.03/task, 160M output tokens across the index ("somewhat verbose"). AA's summary: "amongst the leading models in intelligence, but somewhat expensive when comparing to other open weight models of similar size… faster than average, however somewhat verbose" ([AA](https://artificialanalysis.ai/models/step-5)).
- First-party positioning: "frontier-level performance across software engineering and professional knowledge work, with particular strength in finance" ([HF card](https://huggingface.co/stepfun-ai/Step-5-Preview)). The card's benchmark numbers ship as an **image**, not text — individual scores could not be extracted; the card notes results use the **High** reasoning setting and that GDPval-AA figures are lifted from AA as of 2026-09-20.
- HN submission framing: "On AA Pareto frontier" (the AA model page, [HN item 49763660](https://news.ycombinator.com/item?id=49763660)).
- **Not found:** LMArena Text standing (absent from the visible top 60 of [BenchLeader's lmarena_text mirror](https://www.benchleader.com/benchmarks/lmarena_text), 2026-10-17); Design Arena (only `step-3.7-flash` appears there, ELO 1183, rank 83/190). Treat arena standing as unknown.

### Opinions

- The OpenRouter arrival thread ([HN 50007764](https://news.ycombinator.com/item?id=50007764), 149 pts / 39 comments, 2026-10-08) is sharply split:
  - Negative: "It's a pile of rust… broken prompt responses, garbled repo state, derailed trajectories, hallunies, you name it… Terribly slow… benchmarks are obviously benchmaxxed" (sqvaard).
  - Positive/cautious: "according to Artificial Analysis… it's smarter and slightly cheaper than Gemini 3.8 Flash… I'll give it a try on OpenCode for the week" (robertlane0); "Step 3.5/3.7 Flash were easily my favourite local models… its benchmarks look promising" (girvo).
  - Enthusiasm is tempered by size: "600B-A27B. No way to run that on 228GB" (syntaxing).
- [Kompozy review](https://kompozy.io/reviews/stepfun-step-5-preview) (4.1/5, 2026-09-19): strong value near the top of its price tier, 1M context, but "notably verbose so your real bill runs higher than the sticker output rate implies", and "as a preview… a weak fit for anyone who needs a stable, benchmarked model to standardize a production workflow on today."
- StepFun ran a free week through OpenCode, Cline and Kilo Code ([StepFun tweet via HN](https://news.ycombinator.com/item?id=50007811)) — early OpenRouter traffic partly reflects promotion.

### Known for

Repository-scale software engineering and finance-flavored professional knowledge work over 1M-token contexts (including video/chart sources), at mid-tier pricing — StepFun's intelligence-per-dollar Pareto play.

### Caveats

- **Preview**: the vendor label and OpenRouter snapshot (-20261008) mean numbers and behavior will move; one user reports bench-maxed scores vs real-world failures (above).
- **Quantization/provider routing**: all four OpenRouter endpoints serve **fp4 or fp8 only** — InferenceNet (fp4), Featherless (fp4, but context capped at 262K / max output 32K), DeepInfra (fp8), StepFun (fp8) ([OpenRouter endpoints API](https://openrouter.ai/api/v1/models/stepfun/step-5-preview/endpoints)). BF16 weights exist on HF but no bf16 endpoint is offered; Featherless 1-day uptime ~95.7% vs 100% for StepFun/InferenceNet.
- **Verbosity** inflates output cost (AA: 160M tokens on its index; Kompozy concurring).
- **Spec disagreement**: StepFun docs say video input and max output 64K ([docs](https://platform.stepfun.ai/docs/en/guides/models/step-5-preview)); the HF card's spec table says input "Text, image" and "Maximum Output: Up to 1M tokens" ([HF card](https://huggingface.co/stepfun-ai/Step-5-Preview)). OpenRouter advertises text+image+video → text. Trust the docs' 64K cap in practice; OpenRouter endpoints cap output at 64K–131K.
- **License**: "StepFun Model License 1.0", not a standard OSS license; AA reads it as "commercial use allowed with restrictions" ([AA](https://artificialanalysis.ai/models/step-5)).

---

## 2. tencent/hy4-preview

**Identity confirmed**: Hy4 preview = Tencent's **Hunyuan 4** (preview). "Hy" is the brand of the Hunyuan program — HF tags list `hunyuan, hy4`, the GitHub org is `Tencent-Hunyuan`, and Tencent's release speaks of "Hunyuan… deep co-design with products" ([Tencent release](https://www.tencent.com/tencent-releases-and-open-sources-tencent-hy4-preview/), [HF card](https://huggingface.co/tencent/Hy4-preview), [MindStudio](https://www.mindstudio.ai/blog/tencent-hy4-preview-benchmarks): "released under the Hunyuan (Hy) program"). Released/open-sourced 2026-08-28. 770B total / 49B active MoE (256 routed + 1 shared expert, top-8), native MTP layer, Gated DeepSeek Sparse Attention + IndexCache, 1M context, text→text ([HF card](https://huggingface.co/tencent/Hy4-preview)).

### Benchmark standing

- **AA: no page found** (checked `hy4`, `hy4-preview`, `tencent-hy4` — 404 on 2026-10-17). First-party AA Intelligence Index number for this model is **unavailable**; do not guess one.
- Tencent's headline evidence is a **vendor-run blind eval**: 163 internal experts, 203 engineering tasks — Hy4 preview 2.99/4.00 vs GLM-5.3 2.92 (46.8% wins / 12.8% ties / 40.4% losses) and Kimi K3 2.94 (51.2% / 7.9% / 40.9%) ([Tencent release](https://www.tencent.com/tencent-releases-and-open-sources-tencent-hy4-preview/), [HF card](https://huggingface.co/tencent/Hy4-preview)). MindStudio's read: "wins more often than it loses… margins are narrow, and loss rates sit around 40% in both matchups. This isn't a blowout" ([MindStudio](https://www.mindstudio.ai/blog/tencent-hy4-preview-benchmarks)).
- HF-verified scores cited by reviewers: GPQA Diamond 92.3, SWE-bench Multilingual 82.9% ([eesel review](https://www.eesel.ai/blog/tencent-hy4-review)).
- Independent non-English check (German-language eval index, maintainer in HN thread): "Hy4 is a big improvement over h3 but still below DeepSeek pro and significantly below GLM 5.3 Flash. hy4 ranks ~14th overall" ([dach.peerbench.ai via HN 49492632](https://news.ycombinator.com/item?id=49492632)).
- **Not found**: LMArena Text / Design Arena standing (not listed in [BenchLeader top 60](https://www.benchleader.com/benchmarks/lmarena_text) or the [Design Arena](https://designarena.ai/leaderboard) board, 2026-10-17).

### Opinions

- Launch thread ([HN 49492632](https://news.ycombinator.com/item?id=49492632), 387 pts / 259 comments):
  - Traction: "Hy4 apparently has ludicrous traction on OpenRouter already… trillions of tokens processed in a couple days: more than GLM 5.3 in a week. That said, it's relatively cheap with a 5% cache cost when everyone is still doing 10%/20%" (minimaxir).
  - Anecdote on predecessor: "I experimented with Hy3… surprised with how good it was… as a general purpose agentic model, it was only beaten by deepseek4-flash in our tests. It was so close to deepseek behaviour I kept thinking it must have been forked from it" (jorl17).
  - Skepticism toward the self-improvement claim ("Hy4 preview also contributed to its own development process… early-stage recursive self-improvement loop") — codethief notes it echoes AI-2027 predictions; eesel calls it "marketing framing on top of a real result" (a claimed 31.8% self-optimized inference throughput gain).
  - Amusement at terse reasoning traces: "Seeing the model use 'caveman speak' in its thoughts to save tokens is hilarious" (zyralab).
  - A recurring speed concern for the line: "my one concern over Hy3 was speed… relatively slow everywhere I could get it (including from Tencent directly)" (vcryan).
- Press coverage is thin outside vendor channels; Simon Willison posted a brief pelican test ([simonwillison.net](https://simonwillison.net/2026/Aug/29/hy4/)). No modelsentiment Reddit read exists (page absent).

### Known for

Open-weight (Apache 2.0) flagship for coding agents, tool-use workflows and office/productivity artifacts — designed to trade blows with GLM-5.3 and Kimi K3 at lower price, with first-class long-context (1M) document work.

### Caveats

- **Preview with declared flaws**: Tencent lists "spending longer than necessary reasoning through complex tasks, and a tendency to over-verify its own work" as known issues, and says "we would rather ship early and hear what breaks" ([HF card](https://huggingface.co/tencent/Hy4-preview)).
- **Vendor-run benchmarking**: the headline comparison (GLM-5.3, Kimi K3) is Tencent's own blind eval with internal experts; no AA page and no arena standing were found — third-party verification is limited to HF-surfaced scores and one German eval.
- **Quantization/provider routing**: OpenRouter endpoints are fp8 (Tencent, Novita, SiliconFlow) or fp4 (DeepInfra) — no bf16 endpoint ([OpenRouter endpoints API](https://openrouter.ai/api/v1/models/tencent/hy4-preview/endpoints)); Tencent ships official FP8 weights alongside BF16 ([HF card](https://huggingface.co/tencent/Hy4-preview)). Tencent runs time-of-day pricing (cheaper 16:00–00:00 UTC). Max completion tokens vary wildly by provider (64K on Tencent/Novita vs 262K on SiliconFlow).
- **Not open source**: weights are open (Apache 2.0) but, as HN commenters note, the training data/pipeline remain opaque ([HN 49492632](https://news.ycombinator.com/item?id=49492632)).
- **Text-only** on OpenRouter (no image input, unlike Step 5 / Opus / Luna) ([OpenRouter models API](https://openrouter.ai/api/v1/models)).
- Price is mid-tier ($0.75–0.83/M in, $2.25–2.50/M out) — 5–6× Hy3's cost ([eesel](https://www.eesel.ai/blog/tencent-hy4-review), [OpenRouter](https://openrouter.ai/tencent/hy4-preview)).

---

## 3. tencent/hy3

**Identity confirmed**: Hy3 = Tencent's **Hunyuan 3** (HF tags `hunyuan, hy3`; "developed by the Tencent Hy Team"; GitHub `Tencent-Hunyuan/Hy3`). Released 2026-07-06 ([AA FAQ](https://artificialanalysis.ai/models/hy3)) after a "Hy3 Preview" in late April 2026 ([HF card](https://huggingface.co/tencent/Hy3)). 295B MoE / 21B active + 3.8B MTP layer, 192 experts top-8, 256K context, Apache 2.0 ([HF card](https://huggingface.co/tencent/Hy3)). NOTE: AA's page says 299B total ([AA](https://artificialanalysis.ai/models/hy3)); the model card says 295B — small disagreement, card is the primary source.

### Benchmark standing

- **AA Intelligence Index 25** (well above its class median 19), 84.4 t/s, TTFT 2.80s, $0.07/task, $0.14/$0.55 median-across-providers pricing, "somewhat verbose" at 170M output tokens ([AA model page](https://artificialanalysis.ai/models/hy3)).
- First-party: "outperforms similar-size models and rivals flagship open-source models with 2-5x parameters"; blind eval with 270 experts on real work tasks: 2.67/4 vs GLM-5.1 2.51/4; internal hallucination rate 12.5%→5.4% vs preview; multi-turn issue rate 17.4%→7.9%; SWE-Bench Verified variance across CodeBuddy/Cline/KiloCode scaffolds within 4% ([HF card](https://huggingface.co/tencent/Hy3)).
- Independent spot checks are mixed: lechmazur benchmarks — 10/36 buyout_game, 14/25 pact, 60/81 nyt-connections, 16/29 debate (zone411 in [HN 48317294](https://news.ycombinator.com/item?id=48317294)).
- **Design Arena: below average** — `hy3-direct` ELO 1228 (rank 69/190) and `hy3` ELO 1178 (rank 89/190), vs Claude Opus 5.5's 1390 ([Design Arena leaderboard data](https://designarena.ai/leaderboard), read 2026-10-17). Not found in the [BenchLeader lmarena_text top 60](https://www.benchleader.com/benchmarks/lmarena_text).

### Opinions

- Launch thread ([HN 48847552](https://news.ycombinator.com/item?id=48847552), 561 pts / 120 comments):
  - "It's pretty great, better than gpt-5.4-mini… close enough to sonnet 5 in performance that I didn't notice much of a gap… exceedingly cheap so there is no reason not to use it" (minraws).
  - "This model is shockingly small for how capable it is… around as capable if not more on some benchmarks than V4 pro" (nshotton).
  - "I like the speed of Hy3. Also seems very happy to follow instructions" (james2doyle) — though he still ranks MiMo v2 Pro higher for instruction-following.
  - **Prose**: "Writes pretty engaging prose, finetunes well… very good world knowledge for the size: better than DS4 Flash" (BoorishBears). Same commenter says "MIT licensed" — **wrong**, the card says Apache 2.0 ([HF card](https://huggingface.co/tencent/Hy3)).
  - Dissent: "I feel like I'm taking crazy pills with hy3, it's either benchmaxxed to hell and back or skill issue on my part but I'd rather use dense gemma. I don't think there's a single model that's wasted more of my time in recent memory" (thot_experiment).
- **Provenance story**: Hy3 preview topped OpenRouter's token rankings in May 2026 while unknown publicly ("The mysterious Hy3 LLM is topping OpenRouter Model Rankings by a large margin", [minimaxir.com](https://minimaxir.com/2026/05/openrouter-hy3/), [HN 48317294](https://news.ycombinator.com/item?id=48317294) 150 pts / 112 comments). minimaxir's verdict at the time: "the model quality is indeed on par with the other Chinese models indicated and not close to models such as Claude Opus 4.7 and GPT 5.5. It's not a magic overlooked diamond-in-the-rough" — usage was organic (not app-driven), 98% input tokens, single provider (SiliconFlow), and survived the free→paid transition. By July he wrote "it has fallen to 8/9th on the rankings. I don't see a reason where you would use this model over competitors" ([HN 48847552](https://news.ycombinator.com/item?id=48847552)).
- Simon Willison's pelican test: "First model I've tried that gave me back HTML with a 'Change Pelican Color' button" ([simonwillison.net](https://simonwillison.net/2026/Jul/6/hy3/)) — a hint of playfulness in its generations.
- Caveat from simonw on the ranking itself: OpenRouter shows tokens, not unique users — "we can never be sure if it was because a single whale user" ([HN 48317294](https://news.ycombinator.com/item?id=48317294)).

### Known for

The budget open-weight workhorse — 21B active parameters delivering "good enough" agentic and reasoning performance at commodity prices ($0.33–0.80/M out depending on provider), with solid tool-call reliability and surprisingly decent prose for the price.

### Caveats

- **Quality ceiling**: praised as cheap/competent, but minimaxir found no reason to pick it over competitors once the free tier ended, and one heavy user calls it bench-maxed; treat it as a volume/cost play, not a frontier substitute.
- **Quantization/provider routing**: Tencent first-party is cheapest by far (fp8, $0.083/$0.33 per [OpenRouter endpoints API](https://openrouter.ai/api/v1/models/tencent/hy3/endpoints)); other providers (Novita, GMICloud bf16, Phala, AtlasCloud) charge 1.7–2.4× more with mixed/unknown quantization. Provider choice dominates cost here more than for any other model in this batch. Time-of-day pricing applies (Tencent/Novita cheaper 16:00–00:00 UTC).
- **Context 256K** and text-only — the smallest context in this batch (vs 1M for the others).
- **Licensing noise**: Apache 2.0 per the model card; an HN commenter claimed MIT — don't propagate that.
- **Ranking opacity**: its OpenRouter popularity originated in a free-tier + single-provider period (minimaxir), so its traffic rank carries less signal than a mature multi-provider model's.
- AA notes it is "somewhat verbose" (170M tokens on its index) and TTFT 2.80s is "at the higher end" for its class ([AA](https://artificialanalysis.ai/models/hy3)).

---

## 4. openai/gpt-6-luna

OpenAI's "most efficient model for focused, high-volume tasks", the small tier of the GPT-6 generation (Luna < Sol < Astra, per HN commenters; "Number is generation, Name is the size (Luna smallest to Astra largest)", [HN 49805509](https://news.ycombinator.com/item?id=49805509)). Released 2026-09-22 alongside GPT-6 Sol, successor to GPT-5.6 Luna (July 2026) at half the price ([OpenAI docs](https://developers.openai.com/api/docs/models/gpt-6-luna), [simonwillison.net](https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/)). 1.05M context (922K max input, 128K max output), knowledge cutoff 2026-05-18, reasoning effort none→max ([OpenAI docs](https://developers.openai.com/api/docs/models/gpt-6-luna)).

### Benchmark standing

- **AA Intelligence Index 38** ("Max" reasoning), #8/171 in its price class, 120.4 t/s, $0.07/task, "somewhat verbose" (140M output tokens) ([AA model page](https://artificialanalysis.ai/models/gpt-6-luna)).
- AA's release analysis ([AA article, 2026-09-22](https://artificialanalysis.ai/articles/gpt-6-sol-and-luna-push-the-cost-efficiency-frontier)): Intelligence is level with GPT-5.6 at ~60% lower cost/task — but **mixed per-eval**: Coding Agent Index **regressed** 41 (−2 vs GPT-5.6 Luna; SWE-Atlas-QnA 44% vs 49%, DeepSWE 64% vs 66%); GDPval-AA −75 Elo and AA-Briefcase −45 Elo, where "the regressions tend to be driven by reduced presentation quality and deliverables that omit rubric elements". Hallucination improved (AA-Omniscience 93%→77% hallucination rate; index −10→1). AutomationBench-AA up 53% (vs 50%).
- OpenAI-reported (not independently verified): +5.4pp AutomationBench 1.0.6 at high effort vs GPT-5.6 Luna at −58% cost/task; at high effort, factuality matching the larger GPT-5.6 Sol ([layer3labs review](https://www.layer3labs.io/guides/gpt-6-luna-review)).
- **LMArena Text (style control): rank 57/105** — mid-pack, far below Opus 5.5 (#2) ([modelsentiment benchmark strip](https://modelsentiment.com/m/gpt-6-luna), citing Arena + AA). Code Arena #26/83; Epoch Capabilities #24/87 (same source).
- **Design Arena: ELO 1272, rank 40/190** (win rate 48.4%), vs GPT-5.6 Luna 1232 and Claude Opus 5.5 1390 ([Design Arena data](https://designarena.ai/leaderboard), 2026-10-17).
- A small structured writing test (llmwise, 5 rubric-graded prompts incl. 2 hard constrained-writing tasks, grader = Opus 5.5 cross-checked by GPT-6 Astra): Luna **passed 5/5** at ~$0.0001/reply — but the sample output graded 4.0/5 vs Astra/Sol's 4.3: fact-complete and rule-compliant yet noticeably plainer ([llmwise](https://llmwise.ai/gpt-5-for-writing)).

### Opinions — the "Luna class" question (instruction-following vs prose)

Community reception **corroborates the user-validated verdict** ("obtuse, awful prose… sticks to instructions very thoroughly: good for orchestration" — policy.json) more than it contradicts it:

- Instruction-literalism is the recurring praise: "I tell exactly how I want it done and what files to modify, in those conditions sometimes a model that does not try to read between the lines works better" (jwrallie, [HN 49805509](https://news.ycombinator.com/item?id=49805509)). "Luna is cheap and smart enough to do many agentic tasks" (whazor, same thread). "If you've got an easy, but tedious workflow, Luna can be quite good at that" (thimabi, same thread).
- Orchestration use is common: "a Luna orchestrator spawning Sol/Astra subagents to do the 'big brain' work… (Luna is also really good…)" (booty, [HN 49803892](https://news.ycombinator.com/item?id=49803892)). layer3labs concurs: "tuned for smaller, discrete steps rather than orchestrating an entire 50-step sequence alone"; good for deterministic parsing, schemas, triage; "prone to logic drift on software engineering tasks spanning multiple repositories" ([layer3labs](https://www.layer3labs.io/guides/gpt-6-luna-review)).
- Prose quality gets **no praise anywhere found**; the only first-party style claim is OpenAI's Sol/Luna release wording — "more clarity, less jargon, [and] fewer odd turns of phrase" (quoted in [TechCrunch](https://techcrunch.com/2026/10/01/opus-5-5-loves-to-tell-you-this-matters-and-other-ai-writing-tells/)) — and the independent measurements run against it: AA found GPT-6 Luna's knowledge-work deliverables show "reduced presentation quality" vs GPT-5.6 Luna ([AA article](https://artificialanalysis.ai/articles/gpt-6-sol-and-luna-push-the-cost-efficiency-frontier)); Graphite's corpus study finds GPT-family prose is drifting *further* from human word distributions over time ([TechCrunch](https://techcrunch.com/2026/10/01/opus-5-5-loves-to-tell-you-this-matters-and-other-ai-writing-tells/)); Willison's SVG test found the 6 family "a lot more muted" in its generations ([simonwillison.net](https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/)).
- Verbosity complaint despite small-model status: "Luna uses way more tokens and fills the context up way too fast" (o_m, [HN 49805509](https://news.ycombinator.com/item?id=49805509)) — consistent with AA's 51k output tokens/task vs 41k for GPT-5.6 Luna.
- Value reception is strong: "positively insane" pricing (Cu3PO42), "Luna is fine. It's not Claude Sonnet 3.5" (minimaxir), "the dollar per work is insane value" (Someone1234, [HN 49804316](https://news.ycombinator.com/item?id=49804316)).
- **Quality-instability reports** (relevant caveat): "2-3 weeks ago Luna turned into drivel in essentially the same complexity of task… does feel like it's being manipulated" (seabass-salmon, [HN 49804316](https://news.ycombinator.com/item?id=49804316)); a code-review harness saw Sol regress to Luna level (breckenedge, same thread); r/codex thread "Got 6 Luna max so stupid today?" ([modelsentiment thread list](https://modelsentiment.com/m/gpt-6-luna)). Reddit sentiment overall: **no clear lean**, index 56 (95% interval 47–64), 15th of 26 models; cost praised (94% of 33 opinions), intelligence "split" (33% praise) ([modelsentiment](https://modelsentiment.com/m/gpt-6-luna)).

### Known for

Near-free high-volume work: strict instruction-following, extraction/summarization, tool-loop orchestration and other tightly-scoped agentic steps where compliance and cost matter more than voice.

### Caveats

- **Writing/presentation is the documented weakness**: AA-measured presentation-quality regression vs its own predecessor, no community prose praise, plainer output than siblings on head-to-head writing samples. For a writing/research policy this is the disqualifier.
- **Model churn**: launched 2026-09-22; OpenAI replaced GPT-6 Sol with GPT-6.1 Sol after just 7 days ([AA article](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence)) — expect Luna-class churn too. Anecdotal reports of post-launch quality drift (above) are unverified but recurring.
- **Latency at max effort**: AA measured TTFT 117.9s for Luna (max) — extended thinking counts toward first-token time ([AA](https://artificialanalysis.ai/models/gpt-6-luna)). For chat/latency-sensitive use, keep effort low/medium.
- **Long-context price cliff**: prompts >272K tokens bill at 2× input and 1.5× output ([OpenAI docs](https://developers.openai.com/api/docs/models/gpt-6-luna)); also Luna fills context fast (verbosity) — the two compound.
- **Provider routing**: served by OpenAI (standard/flex/fast tiers with different prices — flex $0.05/$0.25), Azure (US/EU +10% regional), Amazon Bedrock — all unquantized/unknown quant, uniform quality expectations ([OpenRouter endpoints API](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints)). Chat Completions supports function calling only with `reasoning_effort: none` ([OpenAI docs](https://developers.openai.com/api/docs/models/gpt-6-luna)) — a real routing/compatibility caveat for agentic harnesses.
- Moderated (OpenRouter marks it `is_moderated: true`), and OpenAI ships safety refusals Luna-class models are not exempt from.

---

## 5. anthropic/claude-opus-5.5

Anthropic's flagship, first of the Claude 5.5 family (Sonnet 5.5 / Haiku 5.5 "in the coming weeks"), released 2026-09-22. "Performs at the level of Claude Fable 5.1 on most work and costs 40% less to run than Opus 5" ([Anthropic](https://www.anthropic.com/claude-opus-5-5)). $4/$20 per M (cache reads $0.20, 60% cheaper than Opus 5), 1M context, 128K max output. First release since Anthropic's "pacing the frontier" call; pre-tested by Frontier Design and METR.

### Benchmark standing

- **AA Intelligence Index 58 — #1 of 217** ("Max, Default Fallback"; matches the supplied 57.6), ahead of Claude Sonnet 5.5 (56), Opus 5.5 xhigh (56), Muse Wonder Full (56) ([AA model page](https://artificialanalysis.ai/models/claude-opus-5-5), [AA](https://artificialanalysis.ai/models)). Cost per task $5.98 (#112/114 — near the top of the price range); **very verbose** (260M output tokens, #114/116); 97.5 t/s.
- Anthropic first-party table (vs Fable 5.1 / Opus 5 / GPT-6 Astra / GPT-5.6 Sol): Terminal-Bench 4.0 **66.4%**, FrontierCode v1.1 54.4%, CursorBench 4.0 57.8%, GDPval-AA 1846, AutomationBench 40.0% (Astra 41.4% leads), HLE w/tools 67.7%, Terminal-Bench-Science 58.7% (Astra 64.6% leads), OSWorld 2.1 81.8%, Chartography 89.0% ([Anthropic](https://www.anthropic.com/claude-opus-5-5)). Anthropic itself warns "benchmark margins have become a less reliable guide to real-world differences" and that safeguard fallbacks (cyber/bio tasks completed by Opus 4.8/Opus 5 instead) likely lower some scores.
- **LMArena Text (style control): ELO 1508, rank 3/381 configs** (behind Gemini 4 Argon 1524, Muse Wonder 1509) as of 2026-10-17 ([BenchLeader mirror of lmarena data](https://www.benchleader.com/benchmarks/lmarena_text), CC BY 4.0). modelsentiment renders the same data as "#2 of 105" — different denominators, same top-tier conclusion.
- **Design Arena: ELO 1390, rank 1/190** (63.8% win rate), ahead of GPT-6 Astra (1379) — the strongest design/UI-generation standing of any model checked ([Design Arena data](https://designarena.ai/leaderboard), 2026-10-17).

### Opinions — prose is the story

- Anthropic claims writing improvement: "Opus 5.5 communicates more naturally than prior models. Early testers found its writing clearer and easier to follow, which addresses some of the common feedback we heard about Opus 5… As one early tester put it, 'it writes the way I do'" ([Anthropic](https://www.anthropic.com/claude-opus-5-5)).
- Independent measurement mostly agrees on direction, less on completeness:
  - Writing-pattern analysis (Arena via BleepingComputer): em dashes 15.2→0.8 per 1,000 words (−95%), semicolons 6.10→1.64, sentences 12.14→10.03 words — but answers got longer (453→481 words avg, the longest-writing Opus) ([bleepingcomputer.com](https://www.bleepingcomputer.com/news/artificial-intelligence/claude-opus-55-uses-95-percent-fewer-em-dashes-but-its-answers-are-getting-longer/)).
  - Graphite corpus study: fewer classic tells, but new ones — "this matters" 116× human rate, "why X matters" 92×, "dependable" 23×; Claude families are drifting *closer* to human word distributions over time while GPT drifts away ([TechCrunch](https://techcrunch.com/2026/10/01/opus-5-5-loves-to-tell-you-this-matters-and-other-ai-writing-tells/); similar framing at [VentureBeat](https://venturebeat.com/data/claude-opus-5-5-uses-em-dashes-99-less-often-and-sounds-more-human-but-still-exhibits-2-548-ai-writing-tells/) — note the two outlets report −99% vs −95% em-dash figures from overlapping analyses).
  - Every's Vibe Check (via OrcaRouter): most readable of five frontier models — Flesch-Kincaid 6.95 / Reading Ease 68.4 (vs Opus 5's 7.97/61.35, Fable 5.1 7.43/66.09, GPT-6 Astra 7.52/64.55, GPT-5.6 Sol 8.74/56.62) — **but** "still buries the point" (37–39 sentences for what the reviewer said in 21), and "as an editor it fared worse than as a writer" ([orcarouter.ai](https://www.orcarouter.ai/blog/claude-opus-5-5-creative-writing)).
- HN launch thread ([HN 49803892](https://news.ycombinator.com/item?id=49803892), 1806 pts / 1134 comments): "I hope this actually fixes the terrible writing style of Opus 5" → "It's not a 100% fix, but with concise output style on, it's much better"; counterpoint: "Explicit instructions, memories and even skills have not been able to keep Claude from saying 'genuinely' every two sentences". AA-thread: "The output style and verbosity with Opus 5.5 is a very big improvement over Opus 5" ([HN 49804316](https://news.ycombinator.com/item?id=49804316)).
- **Overthinking failure**: Willison's pelican-SVG test at "max" effort **failed to return any response twice** — it burned the full 128K output budget while still reasoning ($2.56 and ~20 min per attempt): "I'm now suspecting that 'max' is effectively useless" ([simonwillison.net](https://simonwillison.net/2026/Sep/22/opus-and-sol-and-luna/)). AA's 728s TTFT (max) and 260M-token verbosity corroborate.
- Reddit sentiment (modelsentiment, 2,089 opinions / 777 threads / 7 days to 2026-10-17): index **65** (62–67), 2nd of 26; coding praised 83%; **writing & tone only 39% praise (mostly criticised)**; refusals 24% praise. Nerf/degradation threads recurring ("Are They Nerfing Opus 5.5? Livenerf Day 20", "Theory on Opus 5.5 Language Degradation") — unverified ([modelsentiment](https://modelsentiment.com/m/claude-opus-5.5)).
- Coding/agentic reception is strong ("Opus 5.5 is INSANE at decompilation/ports", "crushes the tickets assigned to me", "on a completely different level" — thread list at [modelsentiment](https://modelsentiment.com/m/claude-opus-5.5); Willison uses it as default in Claude Code).

### Known for

The intelligence-and-craft ceiling of the current moment: #1 AA intelligence, #1 Design Arena, top-3 LMArena Text, with measurably improved (simpler, more human-timed) prose — the default pick for hard coding, long-horizon work, and the best starting point in this batch for serious writing, if you can pay.

### Caveats

- **Cost/verbosity**: $4/$20 (blended $2.94/M per AA), $5.98/task at Max effort — AA ranks it #112/114 on cost; very verbose (#114/116 on output tokens) and answers lengthened vs Opus 5. Effort rung is a real cost/behavior lever (AA release data cited on HN: Opus 5.5 Medium $1.34/task vs Max $5.98 — [HN 49803892](https://news.ycombinator.com/item?id=49803892)).
- **"Max" effort can break**: reasoning can exhaust the 128K output cap before answering (Willison, twice). Use xhigh or lower for anything deliverable-shaped.
- **Prose still imperfect**: "buries the point"; recurring AI tells ("this matters"); Reddit's writing & tone topic is net-negative (39% praise); known to keep over-explaining despite style fixes ([orcarouter](https://www.orcarouter.ai/blog/claude-opus-5-5-creative-writing), [TechCrunch](https://techcrunch.com/2026/10/01/opus-5-5-loves-to-tell-you-this-matters-and-other-ai-writing-tells/), [modelsentiment](https://modelsentiment.com/m/claude-opus-5.5)).
- **Safeguards/fallback behavior**: first Opus with Fable-class cyber/bio/LLM-dev safeguards; tripping them transparently routes the task to older models (Opus 4.8/Opus 5), which changes mid-workflow behavior and lowers benchmark scores on affected tasks; verified-access programs gate some use ([Anthropic](https://www.anthropic.com/claude-opus-5-5)).
- **Provider routing**: uniform $4/$20 on Anthropic, Bedrock (global), Azure (global), Vertex (global), Claude-on-AWS; regional (US/EU) endpoints +10% ($4.40/$22); an `anthropic/fast` tier at 2× ($8/$40) ([OpenRouter endpoints API](https://openrouter.ai/api/v1/models/anthropic/claude-opus-5.5/endpoints)). All unquantized/unknown-quant first-party-class serving — no quantization spread to worry about.
- **Perceived degradation**: multiple Reddit threads suspect post-launch nerfing; no evidence either way ([modelsentiment](https://modelsentiment.com/m/claude-opus-5.5)).

---

## Policy summaries

**stepfun/step-5-preview** — Strong agentic/knowledge-work intelligence per dollar (AA 44, #3 open weights) with 1M context and unique video input, positioned for repo-scale engineering and finance-flavored analysis. Community reception is split: promising on paper ("on the AA Pareto frontier") but with a harsh "pile of rust / bench-maxed" report and no independent prose evaluation. Treat as an agentic/research candidate to trial, not a writing pick; mind fp4/fp8-only serving, preview volatility, and a restrictive custom license.

**tencent/hy4-preview** — Confirmed as Hunyuan 4 preview: Tencent's open-weight flagship for coding agents and productivity artifacts, trading narrow wins with GLM-5.3/Kimi K3 on the vendor's own blind eval (GPQA Diamond 92.3, SWE-bench Multilingual 82.9% on HF-verified scores). Caveats are substantial: self-declared preview flaws (over-verification, over-long reasoning), no AA/arena coverage, text-only, fp8/fp4 serving, and mid-tier pricing at 5–6× Hy3. Reasonable orchestration/agentic candidate; prose quality untested — do not assign writing on current evidence.

**tencent/hy3** — The budget workhorse (AA 25 at $0.33–0.80/M out): surprisingly capable for 21B active parameters, praised for instruction-following, tool reliability, and "engaging prose" for its price class, and the cheapest route to competent agentic output. Reception is genuinely mixed — its OpenRouter dominance traces to a free-tier/whale-prone period and heavy users report bench-maxed behavior and thought loops. Use for high-volume, cost-capped summarization/extraction/agentic loops; verify prose fit per use case, and pin a provider (Tencent first-party is half the price of the rest).

**openai/gpt-6-luna** — The instruction-following specialist: near-free ($0.10/$0.50), literal, and reliable for tightly-scoped tasks, extraction, and orchestration — community and the user-validated verdict agree it is "effective and sticks to instructions very thoroughly" while its prose is plain-to-obtuse (AA measured presentation-quality regressions vs GPT-5.6 Luna; LMArena Text mid-pack; zero prose praise found). For a writing/research policy: exclude from authoring roles, allow as an orchestration/extraction layer; mind context-fill verbosity, the >272K price cliff, Chat-Completions tool-calling limits, and fast model churn.

**anthropic/claude-opus-5.5** — The quality ceiling: #1 AA intelligence (58), #1 Design Arena (1390), #3 LMArena Text, and the only model in this batch with independently measured prose improvement (simpler sentences, −95% em dashes, best Flesch readability) — the default pick for hard writing/research and demanding code. Buy with eyes open: $4/$20 and very verbose, "max" effort can over-think itself to death (128K cap), prose still "buries the point" with new AI tells, and safeguard fallbacks silently swap in older models on sensitive tasks. For writing specifically, prefer xhigh-or-lower effort with explicit concision instructions.
