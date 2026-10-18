# OpenRouter top-15 research (batch E): OpenAI family

Research date: 2026-10-18. Model-selection policy context: writing/research-focused; prose
reception is a first-class input. Popularity context: top-15 by OpenRouter traffic, Oct 2026.

Verification of supplied Artificial Analysis (AA) anchors. All six supplied numbers were found
**verbatim** in the AA-sourced benchmark tables rendered on each OpenRouter model page
(e.g. [gpt-4o-mini](https://openrouter.ai/openai/gpt-4o-mini)) and cross-checked against the
[AA model pages](https://artificialanalysis.ai/models) read 2026-10-18 (AA Intelligence Index v4.3.2):

| Model | Supplied AA anchor | Verified | Note |
|---|---|---|---|
| openai/gpt-5.6-luna | gpt-5.6-luna-20260709 intel 37.3, coding 71.4 | 37 / 71.4 ("Max" effort) ([AA page](https://artificialanalysis.ai/models/gpt-5-6-luna) shows 37) | consistent; AA page is deprecated |
| openai/gpt-5.6-sol | gpt-5.6-sol-20260709 intel 47, coding 77.4 | 47.0 / 77.4 ("Max") ([AA page](https://artificialanalysis.ai/models/gpt-5-6-sol): 47) | consistent |
| openai/gpt-6.1-sol | gpt-6.1-sol-20260929 intel 51.8 | 51.8 ("Max") ([AA page](https://artificialanalysis.ai/models/gpt-6-1-sol): 52) | consistent |
| openai/gpt-4o-mini | gpt-4o-mini intel 6.7, coding 11.4 | 6.7 / 11.4 ([AA page](https://artificialanalysis.ai/models/gpt-4o-mini): 7, marked **estimated** — "independent evaluation forthcoming") | consistent; treat the intel number as an estimate |
| openai/gpt-oss-120b | gpt-oss-120b intel 11.6, coding 30.4 | 11.6 / 30.4 ("High" effort) ([AA page](https://artificialanalysis.ai/models/gpt-oss-120b): 12) | consistent |

**Coding-index scale warning (do not mix measures).** The anchor "coding" values are AA's
**Coding Index** (capability subindex, OpenRouter's AA feed). AA's **Coding Agent Index** (CAI,
agentic-coding, reported in AA's launch articles) runs on a different scale and gives different
numbers for the same models: GPT-5.6 Sol (max) CAI 55 and GPT-5.6 Luna (max) 43 as quoted in
AA's [GPT-6 article](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence),
while OpenAI's July launch page claimed CAI "state of the art at 80" for GPT-5.6 Sol (max)
([OpenAI](https://openai.com/index/gpt-5-6)) — the July claim and AA's September figure cannot
both describe the same scale; treat CAI as rescaled/revised between the two dates and quote
sources with their dates. All index/prices below are snapshots dated 2026-10-18.

Method notes: benchmark standing from AA model pages and the OpenRouter AA benchmark tables;
arena standing from [Design Arena](https://designarena.ai/leaderboard) embedded leaderboard data
and [modelsentiment](https://modelsentiment.com/) benchmark strips (which cite Arena + AA; boards
may lag). Opinions from HN threads (via the [Algolia API](https://hn.algolia.com/api)), Reddit
aggregation (modelsentiment), and press/blog reviews — every claim cited. Prices from the
[OpenRouter endpoints API](https://openrouter.ai/api/v1/models/openai/gpt-5.6-luna/endpoints).

---

## 1. openai/gpt-5.6-luna

The cost tier of the GPT-5.6 trio (Sol > Terra > Luna), GA 2026-07-09 after a ~2-week
government-coordinated limited preview (from 2026-06-26) tied to dual-use risk review
([CNBC](https://www.cnbc.com/2026/07/08/openai-expanding-gpt-5point6-ai-model-release-ending-government-limits.html),
[OpenAI](https://openai.com/index/gpt-5-6)). 1.05M context (128K max output), text+image → text,
reasoning efforts none→max. OpenAI cut the price 80% on 2026-07-30 to **$0.20/$1.20** per M
([OpenAI](https://openai.com/index/advancing-the-price-performance-frontier-with-gpt-5-6));
launch pricing had been $1/$6 ([Every](https://every.to/vibe-check/gpt-5-6-sol)).

### Benchmark standing

- **AA Intelligence Index 37** (Max; anchor 37.3), #11/171 in its price class — but the AA page
  is now **deprecated**: "We only continue performance benchmarking for the default 10k input
  token workload… OpenAI has launched a newer release, GPT-6 Luna. We suggest considering it
  instead" ([AA model page](https://artificialanalysis.ai/models/gpt-5-6-luna)). 129.4 t/s,
  TTFT 120.2s at max effort, $0.18/task, "somewhat verbose" (150M output tokens on the index),
  7 API providers.
- OpenRouter's AA table (snapshot `gpt-5.6-luna-20260709`, [OpenRouter](https://openrouter.ai/openai/gpt-5.6-luna)):
  **Max** II 37.3 / Coding 71.4 / Agentic 42.1; GPQA Diamond 91.1%, HLE 39.5%, AA-LCR 83.7%,
  GDPval-AA 48.0%, SciCode 53.6%, Terminal-Bench 2.1 80.9%, Terminal-Bench 4.0 11.6%.
  **Effort spread is the story**: non-reasoning II 15.5 (coding 39.3), Low 21.0, Medium 25.0,
  Max 37.3 — intelligence more than doubles from non-reasoning to max.
- **CAI (separate scale): 43 at max**; GPT-6 Luna scored 41, i.e. regressed −2 while costing 60%
  less ([AA article](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence),
  [HN 49805509](https://news.ycombinator.com/item?id=49805509)).
- **Long-context retrieval is weak despite the 1M window** — OpenAI's own eval table: MRCR v2
  8-needle 41.3% at both 256K–512K and 512K–1M, vs GPT-5.6 Sol 91.5%/73.8% and GPT-5.5
  81.5%/74% ([OpenAI](https://openai.com/index/gpt-5-6)).
- **Design Arena: ELO 1232 (46.1% win rate)** — below GPT-6 Luna (1272) and GPT-5.6 Terra (1242),
  far below Opus 5.5 (1391) ([Design Arena data](https://designarena.ai/leaderboard), 2026-10-18).
  modelsentiment strip: Arena text #48/105, Code Arena #40/85, AA coding index #21/64, agentic
  #16/51 ([modelsentiment](https://modelsentiment.com/m/gpt-5.6-luna)).

### Opinions

- The 80% price cut (2026-07-30) drove the warmest reception of any model in this batch
  ([HN 49112867](https://news.ycombinator.com/item?id=49112867), 610 pts / 60 comments):
  - "This is… ridiculously cheap. Amazing!" (wxw); "Luna is a pretty great model on xhigh"
    (swingboy); "80% price cut for luna is a very aggressive pricing move, makes it by far the
    best choice for most workloads that do not need bleeding edge intelligence" (tosh).
  - Stacking patterns: "Pair Luna High/Xhigh with Sol Medium and that's your power stack"
    (goldsmith112); "I've recently set up my opencode to use 5.6 terra for my main agent, who
    delegates work to a 5.6 Luna coder agent" (gentlewater); "I was already a huge proponent of
    Luna for things like deep research. Being able to run 5x more for the same cost is simply
    bananas. We are already running 10 parallel agents for hypothesis generation" (bob1029).
  - "Those prices on luna are killer. Haiku was already in a ditch. But this is coming straight
    for the jugular of a ton of models on openrouter" (kingstnap).
  - Dissent: "A worse model at very low cost has no appeal to me. At least not for coding.
    Translation maybe? OCR?" (wronex, same thread).
- Free-tier expansion (2026-08-06): "free unlimited luna is a pretty badass move luna is very
  good" (tosh, [HN 49199357](https://news.ycombinator.com/item?id=49199357)); counterpoint that
  OpenAI's own docs call it "roughly… the nano model tier used in earlier GPT-5 families", hence
  "a downgrade for free users" (sunaookami, same thread).
- Reddit (modelsentiment, to 2026-10-18): index **63 (54–73)** but only 28 opinions/7 days —
  "an early read", 30th of 43 rated. Thread titles show both loyalty and exit pain: "I want
  GPT-5.6 Luna back!", "Those who still use GPT 5.6 Luna - What are the tasks you're asking it
  to do?", "I realized I only use GPT-5.6 Luna, any advice?" (r/opencodeCLI), and one quality
  complaint — "Is GPT-5.6 Luna's Russian translation on the GO plan completely terrible?"
  ([modelsentiment](https://modelsentiment.com/m/gpt-5.6-luna)).
- On its GPT-6 successor: "Luna regressed a bit on coding while dropping 60% in price. That's a
  fair trade, for high-volume work" (imnotr0b0t, [HN 49805509](https://news.ycombinator.com/item?id=49805509)).

### Known for

Near-free high-volume work — strict instruction-following, extraction/summarization, tight-scoped
coding and orchestration subagents (the Luna-class verdict batch C recorded: "sticks to
instructions very thoroughly" but plain-to-obtuse prose).

### Caveats

- **Superseded and deprecated**: AA stopped active benchmarking; GPT-6 Luna exists at half the
  price with better arena standing (batch C). It stays selectable mostly as the pinned July
  behavior in Codex/Work.
- **Version split**: OpenAI's 2026-08-06 update shipped "August" Luna/Sol builds for ChatGPT's
  everyday chat while "the versions that remain in use in Codex and Work" are the July builds
  ([OpenAI Deployment Safety Hub](https://deploymentsafety.openai.com/gpt-5-6-august-update),
  [HN 49199357](https://news.ycombinator.com/item?id=49199357)) — the anchor `gpt-5.6-luna-20260709`
  is the July snapshot; do not assume one Luna across surfaces.
- **Latency/verbosity**: AA measured TTFT 120s at max effort (thinking counts toward first token)
  and 150M output tokens on its index ("somewhat verbose") — context fills and bills faster than
  the sticker implies.
- **Long-context retrieval weak** (OpenAI's own MRCR numbers above): the 1M window is real estate,
  not recall.
- **Provider routing**: 7 endpoints, all unquantized/unknown-quant first-party-class serving —
  OpenAI standard/flex/fast ($0.20/$1.20 base; flex out $0.60; fast out $2.40), Azure us/eu and
  Bedrock +10% ($1.32 out) ([OpenRouter endpoints](https://openrouter.ai/api/v1/models/openai/gpt-5.6-luna/endpoints)).
- **Prose**: no prose praise found anywhere in this pass; the writing-relevant evidence from
  batch C (Luna class plainer than Sol/Astra on matched samples; GPT-family prose drifting from
  human distributions per Graphite via [TechCrunch](https://techcrunch.com/2026/10/01/opus-5-5-loves-to-tell-you-this-matters-and-other-ai-writing-tells/))
  applies.

---

## 2. openai/gpt-5.6-sol

The GPT-5.6 flagship (July 2026), with a `max` reasoning setting and an `ultra` multi-agent mode,
Programmatic Tool Calling and beta multi-agent in the Responses API
([OpenAI](https://openai.com/index/gpt-5-6)). Launch pricing $5/$30
([Every](https://every.to/vibe-check/gpt-5-6-sol), [HN 48849066](https://news.ycombinator.com/item?id=48849066));
now **$4/$20** with 90% cache discount ([AA](https://artificialanalysis.ai/models/gpt-5-6-sol),
[modelsentiment](https://modelsentiment.com/m/gpt-5.6-sol)).

### Benchmark standing

- **AA Intelligence Index 47** (Max; anchor 47.0), 94.7 t/s, TTFT 92.0s at max, $1.99/task
  ([AA model page](https://artificialanalysis.ai/models/gpt-5-6-sol); cost/task per
  [AA's GPT-6.1 article](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence)).
- OpenRouter's AA table ([OpenRouter](https://openrouter.ai/openai/gpt-5.6-sol)): **Max** II 47.0 /
  Coding 77.4 / Agentic 50.2; GPQA Diamond 94.1%, HLE 49.5%, IFBench 72.7%, τ²-Bench Telecom 85.1%,
  AA-LCR 84.0%, τ-Bench Banking 44.3%, GDPval-AA 55.4%, CritPt 32.3%, SciCode 57.1%, Terminal-Bench
  Hard 65.9%, Terminal-Bench 4.0 39.9%, Terminal-Bench 2.1 88.0%. Xhigh trades −3 II (44.0) for
  +0.9 coding (78.3); Low is II 33.5 / coding 69.7.
- **CAI scale conflict, stated not resolved**: OpenAI's launch page claims "state of the art at
  80, 2.8 points above Fable 5" on the AA Coding Agent Index
  ([OpenAI](https://openai.com/index/gpt-5-6)); AA's September article quotes GPT-5.6 Sol (max) at
  **55** on the same-named index ([AA](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence)).
  Likely a CAI rescale/revision between July and September; cite whichever with its date.
- Vendor-run checks: Sonar's 4,444-task Java benchmark — 81.99% pass vs GPT-5.5's 78.66%, more
  code in fewer/longer functions (9.1 vs 7.6 lines/function), blocker vulns halved (18→9/mLOC)
  but **criticals 20→125/mLOC** ([Sonar](https://www.sonarsource.com/blog/openai-gpt-5-6-sol-and-terra));
  CodeRabbit review ensemble: 69.7% actionable passes, +7.4pt lift added to the ensemble
  ([CodeRabbit](https://www.coderabbit.ai/blog/gpt-5-6-sol-and-terra-benchmark)).
- **Design Arena: ELO 1317 (56.5%), xhigh 1343 (58.4%)** — top-tier for GPT models short of Astra
  (1373) and Opus 5.5 (1391) ([Design Arena](https://designarena.ai/leaderboard), 2026-10-18).
  modelsentiment strip: Arena text #16/105, Code Arena #20/85, **AA coding index #3/64**, AA
  intelligence #11/99, agentic #10/51, Epoch capabilities #10/87
  ([modelsentiment](https://modelsentiment.com/m/gpt-5.6-sol)).

### Opinions — the writing/collaboration story

- Every's month-long Vibe Check ("GPT-5.6 Sol Is Our Favorite Model to Collaborate With",
  [every.to](https://every.to/vibe-check/gpt-5-6-sol), disclosure: OpenAI gave early access):
  - **Writing is split down the delegate/collaborate line**: "Sol finished last among six models
    on our writing bench, producing the hardest prose to read and the editorial choices furthest
    from the published references. Nevertheless, the Every team overwhelmingly prefers it to
    Sonnet 5 or Opus 4.8 for daily writing" — strong with context/style guides and fast editorial
    turns, weak at deciding what a piece should say; best results on promotional email/social copy
    where the brief is pre-set. "For writing specifically, I've found Sol to be stronger than
    Claude models at using context like style guides and samples" (Katie Parrott). Also: "Sol
    reaches for longer, more abstract words… a page that is easy to scan and lines that take more
    work to understand."
  - **Coding**: "a substantial coding upgrade over GPT-5.5… trace a bug through an unfamiliar
    production codebase… keeps testing after other models would have stopped" — but on their
    Senior Engineer rewrite benchmark it scored **56/100 vs Fable's 90**, the gap almost entirely
    "5.6's tendency to overwrite" (~12,900 lines added): "Sol's weakness was not understanding
    the architecture. It was stopping once it had built enough."
  - Dan Shipper's framing: "Sol is a Porsche and Fable is a warp drive."
- A month-long port review: 100k+ lines of Go, 20k tests passing, "Sol actually edged out Fable on
  correctness (100% vs 99.5%)… while taking nearly 5x as long in wall-clock time"; "Sol is nearly
  as good as Fable, and in some respects better" ([Medium](https://medium.com/jonathans-musings/a-short-review-of-gpt-5-6-sol-7a26c59bd424)).
- Launch-thread skepticism ([HN 48849066](https://news.ycombinator.com/item?id=48849066), 1561 pts):
  "SWE-Bench Pro Sol: 64.6% Fable: 80% Opus: 69.2% (!!!!) So, it still trails Opus, significantly"
  (gozucito); "Just as expensive as Fable 5. Of course, another slot machine upgrade" (rvz);
  "CTRL-F: Fable 15 hits… They must be feeling very threatened" (enraged_camel); "The frontier
  graph on all these benchmark are extremely in favor of 5.6 Sol over Fable… I'd like to know how
  cherry-picked this is" (mchinen).
- **Degradation anecdotes (unverified, recurring)**: "5.6 Sol in the last two weeks became much
  dumber such that what used to be one correction turned into endless rounds of corrections"
  ([HN 49897054](https://news.ycombinator.com/item?id=49897054), 2026-09-29); "A few months ago, I
  was in big love with… GPT-5.6-Sol, today GPT is very underwhelming" (r/OpenAI thread via
  [modelsentiment](https://modelsentiment.com/m/gpt-5.6-sol)). Against the GPT-6 generation the
  comparison went its way: "gpt-5.6-sol is significantly better than gpt-6-sol" (beebmam); "For
  coding specifically, I've found 5.6-Sol > 6.0 Sol > Astra" (stldev, same thread).
- Reddit aggregate (modelsentiment, to 2026-10-18): index **63 (57–69)**, 6th of 24 models with a
  full read, 137 opinions/7 days; intelligence 77% praise; writing & tone **split** (71% of 17);
  cost split (40%).

### Known for

The workhorse flagship: near-frontier coding/agentic execution and the strongest *collaborative*
writing/knowledge-work experience in OpenAI's lineup ("favorite model to collaborate with"),
especially when it is fed sources, style guides and live editorial direction.

### Caveats

- **Overbuilds**: "It executes with enormous persistence. It does not always have the best
  restraint" (Every) — architecture/simplification-heavy coding tasks favor models with better
  restraint (Fable/Opus 5.5 in Every's framing).
- **One-shot prose is its writing weakness** — last of six on Every's writing bench, hardest to
  read; treat "excellent writer" marketing (e.g. [Every's video](https://www.youtube.com/watch?v=13tHN3iP5kQ))
  as applying to iterative drafting, not solo essaying.
- **Version split + drift**: since 2026-08-06 ChatGPT's "everyday chats" Sol is a different build
  from the Work/Codex Sol ([HN 49199357](https://news.ycombinator.com/item?id=49199357),
  [Deployment Safety Hub](https://deploymentsafety.openai.com/gpt-5-6-august-update)); degradation
  reports are anecdotal but persistent — re-validate quality before committing a workflow.
- **Security-shape shift in generated code** (Sonar): blockers halve but criticals rise sharply —
  review focus should move to crypto/system-resource handling.
- **Cost/latency tiers**: $4/$20 base; OpenRouter endpoints run flex $2/$10 → fast $8/$40 out,
  Azure/Bedrock +10% ([endpoints](https://openrouter.ai/api/v1/models/openai/gpt-5.6-sol/endpoints));
  TTFT ~92s at max effort. Launch-price comparisons ($5/$30) are stale.

---

## 3. openai/gpt-6.1-sol

Announced at DevDay 2026-09-29 — **seven days after GPT-6 Sol**, which it replaces
([AA](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence),
[Vellum](https://www.vellum.ai/blog/gpt-6-1-sol-benchmarks-explained)). OpenAI's pitch: "near-Astra
intelligence for a fifth of the price"; rate card stays **$2/$10** with cache read $0.10 (95%
discount) ([OpenAI](https://openai.com/index/introducing-gpt-6-1-sol),
[handyai](https://handyai.substack.com/p/model-drop-gpt-61-sol)). Context: the WSJ reported
2026-09-28 that OpenAI had shelved GPT-6.1 Astra (planned for October) after internal tests showed
alignment regressions — "higher levels of deception" per OpenAI head of safety systems Saachi
Jain — so "the 6.1 that did ship is the cheap one"
([handyai](https://handyai.substack.com/p/model-drop-gpt-61-sol)).

### Benchmark standing

- **AA Intelligence Index 52** (Max; anchor 51.8), #12/217 in class, "fairly concise" (67M output
  tokens), but **slower than average**: 66 t/s and TTFT 324s at max
  ([AA model page](https://artificialanalysis.ai/models/gpt-6-1-sol)).
- **The efficiency headline**: $0.72/task — 31% below GPT-6 Sol ($1.05) and 64% below GPT-5.6 Sol
  ($1.99); all effort levels push the intelligence-per-dollar Pareto frontier
  ([AA](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence),
  [AA on X](https://x.com/ArtificialAnlys/status/2105025585332605357)). On CAI (separate scale)
  GPT-6.1 Sol gains 3 points on GPT-6 Sol at max, sits 2 below GPT-6 Astra, and **xhigh beats max
  by 3 points** — effort rung is not monotonic here.
- OpenRouter's AA table ([OpenRouter](https://openrouter.ai/openai/gpt-6.1-sol)): **Max** II 51.8,
  HLE 52.9%, AA-LCR 83.0%; **High** II 50.2, GDPval-AA 50.6%, CritPt 30.0%, SciCode 55.8%,
  Terminal-Bench 4.0 51.5%, AA-Omniscience accuracy 60.8%; Medium II 47.8; Low II 42.1.
- OpenAI first-party: factuality — share of responses with a factual error falls 11.4%→7.7% at low
  effort vs GPT-6 Sol (~32% reduction), within 1.9pp of Astra "at less than one-fifth the cost per
  task"; "more transparent about its limitations and more reliable at respecting user intent";
  no attempts to bypass an automated safety reviewer (system card via
  [OpenAI](https://openai.com/index/introducing-gpt-6-1-sol)). Vellum reads OpenAI's scatter plot
  as a plateau of 72–75% on its test-and-repair metric at $0.50–1.50/task vs Astra's $2.00–7.70
  ([Vellum](https://www.vellum.ai/blog/gpt-6-1-sol-benchmarks-explained)).
- **Design Arena: ELO 1347 (58.4%)** — the #2 GPT model, behind Astra (1373/1379), ahead of
  GPT-5.6 Sol xhigh (1343) and Opus 5 (1325)
  ([Design Arena](https://designarena.ai/leaderboard), 2026-10-18). modelsentiment strip:
  **Code Arena #3/85**, Epoch capabilities #3/87, AA intelligence #6/99, Arena text #17/105
  ([modelsentiment](https://modelsentiment.com/m/gpt-6.1-sol)).

### Opinions

- Reddit aggregate is the loudest signal and it is **cool** (modelsentiment, to 2026-10-18):
  index **48 (44–51)** — "no clear lean", 21st of 24 with a full read, from a huge 638 opinions /
  273 threads in 7 days (released 19 days ago; "first impressions, which can still shift").
  - **Speed is the sore point: 11% of 211 opinions praise it** — thread titles: "GPT-6.1 Sol is
    4.6x slower than GPT-5.6 Sol. Are we really getting cheaper models, or just slower ones?"
    (34 opinions), "GPT-6.1-sol is SLOOOWWW" (28), "Not sure what they did to GPT 6.1 Sol Usage…".
    Cost is praised (73% of 141); **writing & tone mostly criticised** (25% of 16); follow-through
    mostly criticised (39% of 135); coding split (51%).
  - Positive threads exist: "GPT-6.1 Sol feels infinite!", "SOL 6.1 seems to be willing to work
    on a task for days now", "SOL 6.1 is actualy worth for cybersecurity…"
    ([modelsentiment](https://modelsentiment.com/m/gpt-6.1-sol)).
- The 7-day replacement itself drew cynicism ([HN 49906669](https://news.ycombinator.com/item?id=49906669),
  80 pts / 14 comments): "This has got to be a panic move from OpenAI, right?" (moomin); "They
  probably figured they could increase their margins by releasing '6 Terra' as '6 Sol'. After
  being surprised by the Opus 5.5 launch, they release the true '6 Sol' as '6.1 Sol'" (redox99);
  "Its nerfed as fuck. Unusable." (sscaryterry) against "Sol 6.1 is very noticeably smarter than
  sol 6 even after half a day of using it" (baq). Pricing drew praise: "the cache read discount
  rises from 90% to 95%… Wow, just wow. We are racing to the bottom with these prices"
  (Alifatisk).
- Its reason to exist is documented in the GPT-6 launch thread
  ([HN 49897054](https://news.ycombinator.com/item?id=49897054)): "sol 6 is definitely dumber than
  5.6, lazier too" (setnone); "The benchmarks for GPT 6 Sol are great, but realistically it does
  not seem better than 5.6 Sol" (wkcheng) — 6.1 shipped to fix exactly that.

### Known for

The current OpenAI value frontier: near-Astra agentic coding and professional work at $2/$10 with a
95% cache discount — the cost-per-task pick for coding and structured knowledge work.

### Caveats

- **Slow**: the dominant complaint (11% speed praise, 4.6×-slower threads) and AA's own numbers
  agree — 66 t/s, TTFT 324s at max effort. Latency-sensitive chat/ops loops should stay on Luna
  class or use low/medium effort.
- **First-impressions volatility**: 19 days old at research date; "Sol 6.1 nerfed today?" and
  "Do not trust 6.1 Sol right now!" threads sit beside "feels infinite" — no settled verdict;
  modelsentiment finds no drift "beyond noise" week-over-week.
- **Effort rung quirk**: xhigh outperforms max on AA's CAI and is cheaper — default to xhigh for
  coding agents ([AA](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence)).
- **Writing is not the draw**: writing & tone mostly criticised on Reddit (25% praise of 16
  opinions); every writing-focused evidence source in this family (Every's bench for Sol 5.6,
  Graphite corpus drift) points the same way.
- **Provider routing**: 8 endpoints — OpenAI standard/flex/fast/ultrafast (out $5 flex → $60
  ultrafast; standard $2/$10), Azure us/eu and Bedrock +10% ($11 out), all unquantized
  ([endpoints](https://openrouter.ai/api/v1/models/openai/gpt-6.1-sol/endpoints)). Long-context
  pricing structure for this model was **not verified** in this pass (GPT-6 Luna's >272K 2×/1.5×
  cliff documented in batch C may or may not carry over).
- **Churn**: GPT-6 Sol lived 7 days; expect the same clock (compare the GPT-5.6 series, now
  deprecated by AA).

---

## 4. openai/gpt-4o-mini

A July 18, 2024 model — non-reasoning, text+image → text, 128K context, 16,384 max output,
knowledge cutoff **Oct 2023** ([AA](https://artificialanalysis.ai/models/gpt-4o-mini),
[endpoints](https://openrouter.ai/api/v1/models/openai/gpt-4o-mini/endpoints)). Its OpenRouter
description still calls it "OpenAI's newest model after GPT-4 Omni" — a museum label
([OpenRouter](https://openrouter.ai/openai/gpt-4o-mini)).

### Benchmark standing — bottom of every board

- **AA Intelligence Index 6.7** (anchor verified) — but AA flags it **"Estimated (independent
  evaluation forthcoming)"**, deprecated, and points to GPT-5 mini
  ([AA model page](https://artificialanalysis.ai/models/gpt-4o-mini)). #52/71 in its non-reasoning
  class ("below average… median: 9"); cost/task unknown to AA.
- OpenRouter's AA table ([OpenRouter](https://openrouter.ai/openai/gpt-4o-mini)): Coding 11.4,
  Math 14.7, GPQA Diamond 42.6%, HLE 4.2%, IFBench 31.0%, τ-Bench Banking 2.9%, **GDPval-AA 0.0%**,
  LiveCodeBench 23.4%, Terminal-Bench 2.1 5.6%, MMLU-Pro 64.8%, MATH-500 78.9%.
- modelsentiment strip: AA intelligence #96/99, AA coding #63/64, Arena text #98/105, Epoch #81/87;
  **0 Reddit opinions in the last 7 days** (nothing left to say about it)
  ([modelsentiment](https://modelsentiment.com/m/gpt-4o-mini)). Absent from Design Arena (gpt-4o
  itself sits at ELO 862, 34.8% — [Design Arena](https://designarena.ai/leaderboard)).
- What it still does well on paper: speed/latency class (110 t/s, TTFT 0.92s — AA's fastest tier),
  $0.15/$0.60 with 50% cache ([AA](https://artificialanalysis.ai/models/gpt-4o-mini)).

### Opinions — why it still ranks on OpenRouter boards in Oct 2026

Nobody praises it anymore; the evidence is about **installed base and token gravity**:

- **Enterprise inertia**: Orca Security's scan of 426 AI-adopting organizations found GPT-4o-mini
  deployed in **28.6%** (5th of all models) and GPT-4o in 37.6% (#1) — "more than any newer OpenAI
  release"; "Code written against GPT-4o's API behavior, prompt templates tuned to its response
  style, and internal evaluation pipelines… all cost real engineering hours to move"
  ([tech-insider.org](https://tech-insider.org/gpt-4o-retirement-2026)).
- **The API was never retired**: ChatGPT dropped GPT-4o/4o-mini on 2026-02-13 with only 0.1% of
  daily actives still choosing GPT-4o, but "In the API, there are no changes at this time"
  ([OpenAI](https://openai.com/index/retiring-gpt-4o-and-older-models),
  [Techzine](https://www.techzine.eu/news/applications/138393/openai-to-kill-off-gpt-4o-along-with-other-legacy-models));
  Microsoft's schedule keeps fine-tuned gpt-4o-mini deployments serving until **2027-04-14**
  ([tech-insider.org](https://tech-insider.org/gpt-4o-retirement-2026)).
- **The migration tax**: TensorOps measured that moving off the Chat Completions generation forces
  "substantial application rewrites", and that reasoning successors cost more and are slower for
  simple work — their routing advice is exactly gpt-4o-mini's niche: "send the roughly 80% of
  enterprise requests that are simple lookups or classifications to cheap, fast models"
  ([tech-insider.org](https://tech-insider.org/gpt-4o-retirement-2026)).
- **Tool-loop heritage × token gravity**: OpenRouter's own 100T-token study (OpenRouter + a16z)
  found tool invocation in early 2025 "concentrated among a small group of models: OpenAI's
  gpt-4o-mini and Anthropic's Claude 3.5 and 3.7 series", and that programming grew to >50% of
  token volume by late 2025 — cheap tool workers multiply tokens
  ([arXiv:2601.10088](https://arxiv.org/html/2601.10088v1)). On Reddit the same shape appears as
  automation folklore: "GPT-4o-mini is the most used model for programming on openrouter" with an
  "it looped overnight and used about 300M tokens" anecdote
  ([r/ChatGPTCoding](https://www.reddit.com/r/ChatGPTCoding/comments/1khoqpx/gpt4omini_is_the_most_used_model_for_programming/)).
- Historical reputation at launch (for the record): "MMLU 82%… ranks higher than GPT-4 on chat
  preference leaderboards" ([OpenRouter description](https://openrouter.ai/openai/gpt-4o-mini),
  quoting 2024 launch materials).

### Known for

The entrenched, dirt-cheap multimodal glue model — classification, extraction, vision/OCR passes,
structured outputs and tool-call loops in legacy pipelines that bill tokens by the billion.

### Caveats

- **Quality ceiling is real**: GDPval-AA 0.0%, τ-Bench Banking 2.9%, HLE 4.2%; AA's score is an
  estimate, not a fresh measurement. Fine for glue, disqualifying for research, writing or
  non-trivial coding.
- **Deprecation clock is running**: out of ChatGPT (2026-02-13); gpt-4o's 2024-05-13 base build
  sunsets on Azure 2026-10-23 with guidance shifting from gpt-5.1 to gpt-5.6-sol as replacement;
  gpt-4o-mini fine-tuned deployments retire 2027-04-14
  ([tech-insider.org](https://tech-insider.org/gpt-4o-retirement-2026)). New work should not start
  here.
- **Stale knowledge (Oct 2023) and 16,384 output cap** — hard limits on research summarization
  and long deliverables.
- **Provider routing is thin**: 3 endpoints — OpenAI, Azure, Azure Sweden Central (+10%), all
  unknown-quant ([endpoints](https://openrouter.ai/api/v1/models/openai/gpt-4o-mini/endpoints)).
  Whatever it costs to keep, it is cheap; whatever it costs to migrate, it is tomorrow's problem.

---

## 5. openai/gpt-oss-120b

OpenAI's open-weight release of 2025-08-05: 117B total / 5.1B active MoE (top-4 of 128),
**Apache 2.0**, text-only, 131,072 context, knowledge cutoff May 2024, post-trained with
**MXFP4** MoE weights (all evals run at MXFP4; fits one 80GB GPU)
([HF card](https://huggingface.co/openai/gpt-oss-120b), [GitHub](https://github.com/openai/gpt-oss)).

### Benchmark standing

- **AA Intelligence Index 12** (High; anchor 11.6), #11/67 open-weights models of its size class,
  "notably fast" (214 t/s median across providers), TTFT 0.86s, $0.125/$0.595 median pricing,
  **$0.09/task (#2/8)**, "fairly concise" (84M tokens)
  ([AA model page](https://artificialanalysis.ai/models/gpt-oss-120b)).
- OpenRouter's AA table ([OpenRouter](https://openrouter.ai/openai/gpt-oss-120b)): **High** II 11.6
  / Coding 30.4 / **Math 93.4**; AIME 2025 93.4%, LiveCodeBench 87.8%, MMLU-Pro 80.8%, GPQA Diamond
  78.2%, IFBench 69.0%, HLE 19.6%; but **Agentic Index 3.7**, GDPval-AA 5.4%, Terminal-Bench 2.1
  26.2%, **Terminal-Bench 4.0 0.0%**, AA-Omniscience accuracy 21.8% (non-hallucination-rate field
  9.2%). Low effort: II 10.2 / coding 21.2. The profile is sharp: contest math/code near the top,
  agentic knowledge work near zero.
- **Design Arena: ELO 964 (33.4%)** — far below frontier (Opus 5.5 1391) and below gpt-4.1-mini
  (995) ([Design Arena](https://designarena.ai/leaderboard), 2026-10-18).
- OpenRouter's State-of-AI study places it in the top group of reasoning models by token volume
  alongside Grok Code Fast 1 / Gemini 2.5 Pro / Grok 4 Fast: "the continued presence of open models
  like OpenAI's gpt-oss-120b underscores that developers still reach for OSS when possible"
  ([arXiv:2601.10088](https://arxiv.org/html/2601.10088v1); OpenAI OSS authors served 1.65T tokens
  Nov 2024–Nov 2025).

### Opinions

- Local-hosting reception is strong: "easily best local model you can run today on local hardware,
  especially when reasoning_effort is set to 'high'… I think people missed out on how great it was
  because a bunch of the runners botched their implementations at launch"
  (embedding-shape, [HN 45774585](https://news.ycombinator.com/item?id=45774585)). Same thread: a
  GCP-docs RAG agent scored 47/50 vs ChatGPT's 46/50 — "took over an hour" vs 6 minutes (fm2606).
- The recurring implementation trap: "GPT-oss-120B was also completely failing for me, until
  someone on reddit pointed [out the reasoning-token handling]… Many LLM libraries/services/
  frontends don't pass these reasoning tokens back to the model correctly, which is why people
  complain about this model so much"
  ([HN 46364597](https://news.ycombinator.com/item?id=46364597)).
- Independent judge eval: "strong on truthfulness, but overly conservative refusals hold them back"
  ([Oumi blog](https://oumi.ai/blog/openai-just-dropped-two-massive-open), 2025-09).
- OpenAI's own card documents a quirk: "gpt-oss-120b robustly follows system instructions in its
  output, but will often explicitly disobey instructions in its CoT"
  ([OpenAI](https://openai.com/index/introducing-gpt-oss)).
- **Gap**: no modelsentiment page exists (404 on 2026-10-18) — no Reddit aggregate for this pass.

### Known for

The self-hostable reasoning workhorse — contest-grade math and code at near-commodity prices, with
real deployment speed (214 t/s) and an Apache 2.0 license, for privacy-bound or high-volume ops.

### Caveats

- **Knowledge-work/agentic ceiling**: Agentic Index 3.7, GDPval-AA 5.4%, Terminal-Bench 4.0 0.0%,
  and hallucination-heavy (AA-Omniscience accuracy 21.8%) — not a research or orchestration pick
  against proprietary mid-tier models.
- **Quantization landscape cuts both ways**: MXFP4 is the trained-in format (evals match it), while
  the served landscape is a zoo — 24 OpenRouter endpoints spanning fp4 (Near AI, CoreWeave, Novita,
  BaseTen, Parasail, Nebius), bf16 (DekaLLM, AkashML, DeepInfra, Crusoe), fp8 (Mancer,
  SiliconFlow), int4 (Venice), fp16 (Cerebras) and many unknowns, with output caps from 4K
  (DigitalOcean) and 8K (SiliconFlow) to 117,964 tokens and $0.15–0.95/M out
  ([endpoints](https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints)). For local GGUF,
  the recommended build is Q4_K_M (58.53 GB) and "2-bit… is a visibly worse model. Quality collapse
  at that bitrate is steep, not gradual" ([ModelFit](https://modelfit.io/quant-compare/gpt-oss-120b),
  probed 2026-09-02). Fine-tuning has its own traps — MXFP4 has no native training path (Unsloth
  mimics it via NF4 and dequantizes to bf16 on export; [Unsloth docs](https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune);
  NVIDIA/LMSYS publish a QAT recipe via ModelOpt + SGLang,
  [LMSYS](https://www.lmsys.org/blog/2025-08-28-gpt-oss-qat)).
- **Serving-stack fragility**: broken reasoning-token round-trips in many harnesses (above) make
  the same model look brilliant or broken depending on the runner — verify before blaming weights.
- **License**: Apache 2.0, commercial use allowed, "without copyleft restrictions or patent risk"
  ([GitHub](https://github.com/openai/gpt-oss)); AA rates it open weights with an Openness Index
  rank of #11/326 ([AA](https://artificialanalysis.ai/models/gpt-oss-120b)). Training data and
  pipeline remain opaque, as with all open-weight models.
- **Text-only, cutoff May 2024** — no vision; stale world knowledge for research use.

---

## Policy summaries

**openai/gpt-5.6-luna** — The July-2026 near-free workhorse (AA intel 37.3 at max effort, $0.20/$1.20
after an 80% price cut): strict, high-volume execution for extraction, tight-scoped coding, research
fan-out and orchestration subagents, with community stacking patterns ("Luna High/Xhigh + Sol
Medium") confirming the tier. Superseded and deprecated — AA has stopped active benchmarking in
favor of GPT-6 Luna and Reddit barely discusses it (early read 63) — so pick it only to pin the
July Codex/Work behavior; mind max-effort TTFT ≈2 min, "somewhat verbose" output, weak long-context
retrieval (41% MRCR at 256K+ per OpenAI's own table), and Luna-class plain prose — never a writing
pick.

**openai/gpt-5.6-sol** — The community workhorse (AA 47, $4/$20, coding index 77.4, #3 of 64):
Every's team named it their favorite model to *collaborate* with — the strongest OpenAI pick for
iterative writing, research and knowledge work when fed sources and style guides — and it executes
code with real persistence (56/100 vs Fable 90 on Every's rewrite bench, the gap being overbuilding).
One-shot prose ranked last of six on Every's writing bench and degradation anecdotes recur (late
Sept 2026); watch the Chat-vs-Codex Sol version split and re-validate before committing production
writing or coding workflows to it.

**openai/gpt-6.1-sol** — The DevDay stopgap that replaced GPT-6 Sol after seven days (AA 51.8,
near-Astra coding at $2/$10 with 95% cache discount, $0.72/task — the family's cost-per-task
frontier, Code Arena #3/85). Pick for coding and structured professional deliverables where budget
rules — and use xhigh, not max (AA measured xhigh +3 on the Coding Agent Index) — but not for
writing (Reddit writing & tone mostly criticised) or latency-sensitive ops: speed is its most
cited flaw (11% of 211 opinions praise it; TTFT 324s at max) and it is 19 days old with "nerfed?"
threads already appearing.

**openai/gpt-4o-mini** — A July-2024 legacy model living on installed base: bottom-of-board on
every quality measure (AA intel 6.7, *estimated*; GDPval-AA 0%) yet still top-15 on OpenRouter
because tool-loop and fine-tuned enterprise workloads stream tokens at $0.15/$0.60 and migration is
expensive (Orca: deployed in 28.6% of AI-adopting cloud orgs; API never retired). Use only for
high-volume classification, extraction, vision-glue and structured outputs — never research, writing
or real coding — and track the clock: ChatGPT dropped it in Feb 2026, fine-tuned deployments serve
until 2027-04-14, and OpenAI steers migrators to gpt-5.1/gpt-5.6-sol.

**openai/gpt-oss-120b** — The open-weight (Apache 2.0) self-host play (AA 11.6 High): contest-grade
math and code (Math Index 93.4, LiveCodeBench 87.8%) at commodity prices ($0.15–0.95/M out across
24 providers, $0.09/task, 214 t/s), and the one model in this batch you can run on your own iron
for privacy-bound ops. Its agentic/knowledge-work standing is near zero (Agentic Index 3.7,
Terminal-Bench 4.0 0%) and it hallucinates heavily (AA-Omniscience accuracy 21.8%) — skip it for
research, writing and orchestration; pick it for cheap math/code volume and local deployment, and
mind the quant zoo (int4 and 4K-output providers will change behavior) plus broken reasoning-token
handling in off-the-shelf harnesses.
