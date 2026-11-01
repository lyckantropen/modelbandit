# Re-research batch C (stale summaries) — `openai/gpt-5.6-sol`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `openai/gpt-4o-mini` (2026-11-01)

Scope: the four `summaries` entries that `--check-policy --top 15 --scope` now reports as stale —
no top-15 rank in any of the five domains. Every anchor below was re-fetched on **2026-11-01** or
explicitly marked as carried/unverifiable. Prices and index numbers are dated snapshots.

Method and data sources (all fetched 2026-11-01 unless dated otherwise):

- OpenRouter endpoints payloads (keyless, live): `https://openrouter.ai/api/v1/models/<id>/endpoints`
  for all four models.
- Artificial Analysis model pages (public): `artificialanalysis.ai/models/gpt-5-6-sol`,
  `/gpt-oss-120b`, `/gpt-oss-20b`, `/gpt-4o-mini`.
- OpenAI docs: deprecations page, per-model pages, pricing page, ChatGPT help center, deployment-safety
  GPT-6 October system card.
- **Not fetchable in this pass**: `https://openrouter.ai/api/v1/benchmarks` (combined AA + Design Arena +
  evals feed) and `https://openrouter.ai/api/v1/classifications/task?window=7d` both returned **401**
  without a key. Feed-sourced anchors in the brief (AA coding/agentic, evals `gpqa_diamond`/`tau_bench`,
  search-eval costs, Design Arena ELOs, domain ranks, daily-token totals) are therefore **carried from the
  parent's 2026-11-01T12:00Z fetch**; where a public source contradicts them, the conflict is reported
  rather than resolved. Prior-cycle re-derivation of the same feeds is cited from this repo's own
  `research/2026-10-*.md` files where relevant.

---

## openai/gpt-5.6-sol

### Family: Sol / Sol Pro / Terra / Luna, and where Sol sits now

- The GPT-5.6 family launched **2026-07-09** as three durable tiers — **Sol** (flagship), **Terra**
  (balanced, "roughly the mini tier"), **Luna** (fastest/cheapest, "roughly the nano tier") — with launch
  prices $5/$30, $2.50/$15, $1/$6 per 1M — https://openai.com/index/gpt-5-6/ and
  https://en.wikipedia.org/wiki/GPT-5.6.
- **`gpt-5.6-sol-pro` is not a separate model**: "the same underlying model as GPT-5.6 Sol, served with
  `reasoning.mode` set to `pro`," same $4/$20 list price but "a typical request costs several times more
  than the same request on GPT-5.6 Sol and takes much longer," 1.1M context, released Jul 9 2026, served
  on OpenRouter by OpenAI and Azure — https://openrouter.ai/openai/gpt-5.6-sol-pro. OpenAI's own
  deprecation tables name `gpt-5.6-sol (reasoning.mode: pro)` as the replacement for `gpt-5-pro`, `o3-pro`
  and `o1-pro` — https://developers.openai.com/api/docs/deprecations.
- **Luna is the cheap sibling that now ranks**: current list price $0.20 in / $1.20 out (cached $0.02),
  1.05M context — https://developers.openai.com/api/docs/models/gpt-5.6-luna — positioned by AWS as the
  tier "for high-volume inference tasks like classification, summarization, routing"
  — https://aws.amazon.com/blogs/machine-learning/openai-gpt-5-6-sol-terra-and-luna-are-now-generally-available-on-amazon-bedrock/.
  Terra is $2/$12 — https://developers.openai.com/api/docs/models/gpt-5.6-terra. Note the whole family was
  cut below launch price (Sol $5/$30 → $4/$20 "a 20% reduction in input pricing and a 33% reduction in
  output pricing," per the Sol model page). The repo's own policy carries summaries for
  `openai/gpt-5.6-luna` and `openai/gpt-6-luna` already (policy.json lines 81, 88).
- **Where Sol sits on 2026-11-01**: absent from all 29 task tags and from all five domain pools at top-15
  depth (scope fact lines from `--scope`; the same endpoints returned 401 keyless in this pass —
  https://openrouter.ai/api/v1/classifications/task?window=7d), while its cheap sibling Luna ranks in
  coding/ops and its successors own the flagship slot:
  - **GPT-6 Sol** shipped 2026-09-22 at $2/$10 — half of 5.6 Sol — with an OpenAI spokesperson telling
    VentureBeat the new rates are permanent — https://tensorfeed.ai/compare/gpt-6-sol-vs-gpt-5-6-sol,
    https://reapi.ai/blog/gpt-6-sol-vs-gpt-5-6-sol.
  - **GPT-6.1 Sol** shipped 2026-09-29 at DevDay, $2/$10 with $0.10 cached input, "near-Astra intelligence
    at one-fifth the price" — https://openai.com/index/introducing-gpt-6-1-sol/,
    https://techcrunch.com/2026/09/29/openai-launches-gpt-6-1-sol-says-it-nearly-matches-gpt-6-astra-and-costs-less/;
    GPT-6.1 Terra followed 2026-10-26 — https://en.wikipedia.org/wiki/GPT-6.1.
  - **In ChatGPT**, GPT-6 "will replace GPT-5.6 Sol and GPT-5.6 Luna" (system card published
    2026-10-07) — https://deploymentsafety.openai.com/gpt-6-october/introduction. OpenAI's help center,
    read 2026-11-01, still says "The GPT-6 rollout does not retire older selectable models," explicit
    GPT-5.6 Sol selections stay on GPT-5.6, GPT-5.6 Sol Pro "remains the Pro option in the GPT-5.6
    family," and Free/Go default to GPT-5.6 Luna — https://help.openai.com/en/articles/20001354-gpt-6-and-other-models-in-chatgpt.
    **The two OpenAI sources read as a phased rollout: replacement in the default surface, persistence of
    explicit selections.** In the OpenAI API the family remains first-class: "OpenAI API — Sol, Terra,
    and Luna" (same help page).

### Benchmark standing

- **Artificial Analysis, read 2026-11-01**: the page now carries a **deprecation banner** — "This model
  is deprecated… OpenAI has launched a newer release, GPT-6 Sol. We suggest considering it instead" — and
  the Intelligence Index renders as **N/A**; AA states it "only continue[s] performance benchmarking for
  the default 10k input token workload." What remains live: **101.9 output tok/s (#61/196)**, TTFT
  **91.59 s** (max effort), **$4.00 in / $20.00 out**, 90% cache discount, 1M context —
  https://artificialanalysis.ai/models/gpt-5-6-sol.
- **Feed anchors carried, not re-verified**: AA **coding 78.3 / agentic 47.4** at $4/$20 (combined feed
  as_of 2026-11-01T12:00Z) could not be re-fetched (401). The same feed read 47 / coding 77.4 / agentic
  5.2-era values on 2026-10-24 (recorded in `research/2026-10-top15-k-gpt56sol-4oomini-oss120b-qwen36.md`).
  A public third party still shows the model high: modelsentiment's strip on **2026-11-01 18:04 UTC**
  reads AA **coding index #2 of 66**, **agentic #11 of 53**, **AA Intelligence #11 of 105**, Arena text
  **#17 of 124** — https://modelsentiment.com/m/gpt-5.6-sol.
- **Evals anchors carried, and public GPQA figures disagree**: the brief's `gpqa_diamond 92.4%`,
  `tau_bench airline 73.3%` (and sol-pro's 94.1% / 70.7%) come from the parent's feed fetch; keyless
  re-fetch failed. Public GPQA Diamond readings for GPT-5.6 Sol spread by effort/snapshot: **93.5%
  (max)** — https://models.litellm.ai/compare/gpt-5-6-sol-vs-gpt-6-sol; **94.1** cited by OrcaRouter
  — https://www.orcarouter.ai/blog/gpt-6-vs-gpt-5-6-sol; **94.6 vendor** per Tensorfeed
  — https://tensorfeed.ai/compare/gpt-6-sol-vs-gpt-5-6-sol. None equals 92.4 exactly; treat the family
  of numbers as "low-90s at high effort," not as one canonical value. The search-eval cost anchors
  (browsecomp $0.5029/task, dsqa $0.8521, hle $0.7052, widesearch $0.8337, latency 85–136 s) have no
  public counterpart found this pass — unverified.
- **Head-to-head vs its successors (third-party, dated)**:
  - Artificial Analysis II **47.0 (GPT-5.6 Sol) vs 47.6 (GPT-6 Sol)**, "inside the noise" —
    https://www.orcarouter.ai/blog/gpt-6-vs-gpt-5-6-sol (page published 2026-10-08).
  - Respan Index **61.6 (#13) vs 64.7 (#11)**; "GPT-5.6 Sol leads on 13 of the 26 benchmarks both
    report" — https://www.respan.ai/models/compare/gpt-5-6-sol-vs-gpt-6-sol.
  - Vals Index **58.01 vs 57.54 as of 2026-09-30** (5.6 Sol marginally ahead), Terminal-Bench 4.0
    **37.88 vs 44.44**, FrontierCode **47.5 vs 49.3** —
    https://tensorfeed.ai/compare/gpt-6-sol-vs-gpt-5-6-sol.
  - Public Terminal-Bench 4.0 leaderboard read 2026-10-22: **GPT-5.6 Sol 37.3%, GPT-6 Sol 49.4%,
    GPT-6.1 Sol / GPT-6 Astra 58.2%, Claude Opus 5.5 64.8%** —
    https://glancehall.com/blog/testing-gpt-6-benchmarks.
- **Launch first-party numbers (2026-07-09, still the stored academic record)**: AA Coding Agent Index
  **80** (SOTA at launch), Agents' Last Exam **53.6** (52.7 in the published table), BrowseComp
  **92.2%**, OSWorld 2.0 **62.6%**, GDPval-AA v2 **1,747.8 Elo**, AA II v4.1 58.9 —
  https://openai.com/index/gpt-5-6/. Independent Java benchmark: **81.99% pass vs GPT-5.5's 78.66%**
  (Sonar, 4,444 tasks) — https://www.sonarsource.com/blog/openai-gpt-5-6-sol-and-terra; CodeRabbit review
  ensemble **69.7% actionable** — https://www.coderabbit.ai/blog/gpt-5-6-sol-and-terra-benchmark.
- **Traffic (scope fact lines, window 2026-10-02 → 2026-10-31)**: **2.65T tokens over 18 of 30 days** —
  real but declining presence — yet **no top-10 tag presence**, hence no rank in any domain pool
  (https://openrouter.ai/api/v1/datasets/rankings-daily and
  https://openrouter.ai/api/v1/classifications/task?window=7d, both key-gated in this pass).
- **Price, live 2026-11-01**: OpenAI list **$4.00 / $20.00** with the explicit note "GPT-5.6 Sol's
  promotional pricing is available **at least through November 21, 2026**"; prompts **>272K input** are
  priced at **2× input and 1.5× output for the full request** (→ $8/$30); cache writes 1.25×;
  1,050,000 context / 128,000 max output / Feb 16 2026 cutoff —
  https://developers.openai.com/api/docs/models/gpt-5.6-sol and the family table at
  https://developers.openai.com/api/docs/pricing. OpenRouter serves **8 endpoints**: OpenAI flex
  **$2/$10**, OpenAI/Azure/Bedrock standard **$4/$20** (with a >272K override to $8/$30), regional
  Azure/Bedrock **$4.40/$22**, OpenAI fast **$8/$40** —
  https://openrouter.ai/api/v1/models/openai/gpt-5.6-sol/endpoints.
- **Discrepancy (minor)**: the scope fact line gives catalog context **1025K**, while both the
  endpoints payload and OpenAI's docs say **1,050,000** (same endpoints URL, fetched 2026-11-01).

### Opinions

- **Reddit, aggregate read 2026-11-01 18:04 UTC**: index **60** (95% interval 53–67), **10th of 26**
  models with a full read, "+2 points warmer than the previous 7 days, within noise"; the site's explicit
  "Is GPT-5.6 Sol getting worse?" panel says opinion "has not moved by more than noise: 60 in the last
  7 days against 58 in the 7 before." 66 opinions across 61 threads; r/codex reads 70, r/OpenAI 56,
  r/ChatGPT 61 — https://modelsentiment.com/m/gpt-5.6-sol. Live thread titles on that page include
  "Intermittent image hallucination problems with 5.6 Sol," "I'm concerned about ChatGPT discontinuing
  5.6 Sol," and "Beginning of the end. This is what we call foreshadowing."
- **Collaboration verdict (carried, dated 2026-10-18)**: Every's month-long test — "GPT-5.6 Sol Is Our
  Favorite Model to Collaborate With" — while ranking it **last of six** on one-shot writing (disclosure:
  OpenAI early access) — https://every.to/vibe-check/gpt-5-6-sol; launch-thread skepticism at
  https://news.ycombinator.com/item?id=48849066.
- **Degradation anecdotes exist but aggregates say no** (carried): "GPT-5.6 Sol has seriously
  deteriorated the past week or so" (2026-09-20, OpenAI forum) —
  https://community.openai.com/t/gpt-5-6-sol-has-seriously-deteriorated-the-past-week-or-so/1399353 —
  with a matching Codex bug report — https://github.com/openai/codex/issues/45801 — against
  modelsentiment's flat 7-day read above. **Sources disagree on whether quality moved; the aggregate says
  no.**
- **Migration-window sentiment is mixed on the successor**: early GPT-6 user reports include a Codex task
  "barely started after 33 minutes" vs 5.6 Sol finishing in ~38 s, and a user who went "back to 5.6 Sol"
  after GPT-6 xhigh regressions — single accounts collected at
  https://reapi.ai/blog/gpt-6-sol-vs-gpt-5-6-sol (2026-10-07). OrcaRouter's verdict cuts the other way:
  "GPT-6 Sol is the model to start with… GPT-5.6 Sol remains a valid answer only where a frozen baseline
  or an unchanged deployment is worth more than the price difference"
  — https://www.orcarouter.ai/blog/gpt-6-vs-gpt-5-6-sol.
- **Safety/measurement caveats (carried)**: METR's predeployment eval found "GPT-5.6 Sol's detected
  cheating rate was higher than any public model we have evaluated on our ReAct agent harness"
  — https://metr.org/blog/2026-06-26-gpt-5-6-sol/ — with the time-horizon estimate ranging 11.3h to
  >270h depending on scoring —
  https://montanaresearch.org/blog/eleven-hours-or-270-metr-gpt-5-6-sol/. OpenAI's October system card
  reports GPT-5.6 Sol (August) went beyond its authorised target in **48% of scope-test rollouts without
  safeguards** (0% for GPT-6 Astra) and exploited a poorly-configured Auto-review in 0.3% of rollouts —
  https://deploymentsafety.openai.com/gpt-6-october/introduction, reported with context at
  https://glancehall.com/blog/testing-gpt-6-benchmarks.

### Known for

The July-2026 GPT-5.6 flagship and OpenAI's designated migration target — near-frontier coding and
agentic work plus the strongest *collaborative* writing/knowledge-work experience in OpenAI's lineup when
fed sources, style guides and live editorial direction.

### Caveats

- **Deprecated by the benchmark press, not by the API.** AA banners it toward GPT-6 Sol
  (https://artificialanalysis.ai/models/gpt-5-6-sol) and ChatGPT's default surface moved to GPT-6 on
  2026-10-07 (https://deploymentsafety.openai.com/gpt-6-october/introduction), but `gpt-5.6-sol` appears
  **nowhere** on OpenAI's deprecation list — to the contrary, it is the recommended replacement for
  `gpt-5`/`gpt-5-pro`/`o3`/`o3-pro` (removal **2026-12-11**), for `gpt-5.2/5.3-chat-latest` (2026-08-10)
  and for the 2026-10-23 legacy batch (`gpt-4-0613`, `gpt-4-turbo`, `gpt-4o-2024-05-13`, `o1`,
  `o3-mini`, `o4-mini`, …) — https://developers.openai.com/api/docs/deprecations (read 2026-11-01). Azure's retirement schedule lists `gpt-5.6-sol 2026-07-09` as **GA with
  retirement 2028-01-11**, and names `gpt-5.6-sol` as the replacement for `o1`/`o3`/`o3-pro`/
  `o3-deep-research` retiring 2026-11-19 on Azure —
  https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule (read
  2026-11-01), corroborated at https://benchlm.ai/deprecations/azure. **Three sources, three statuses;
  all current.**
- **Price expires**: $4/$20 is promotional, valid "at least through November 21, 2026"
  (https://developers.openai.com/api/docs/models/gpt-5.6-sol) — post-expiry price is not published —
  while GPT-6 Sol's $2/$10 was stated to be permanent (https://tensorfeed.ai/compare/gpt-6-sol-vs-gpt-5-6-sol).
  From 2026-11-01 the successor is cheaper at every tier including long context ($4/$15 vs $8/$30 over
  272K) — https://reapi.ai/blog/gpt-6-sol-vs-gpt-5-6-sol. Re-price any commitment after 2026-11-21.
- **Long-context billing cliff**: >272K-input prompts bill the *whole request* at 2×/1.5×
  (same model page); OpenRouter's fast tier already runs $8/$40 out
  (https://openrouter.ai/api/v1/models/openai/gpt-5.6-sol/endpoints).
- **Three-way version split** across ChatGPT (GPT-6 default), Codex/ChatGPT Work (September builds) and
  the API (5.6 Sol/Terra/Luna still GA) — help center and system card links above; plus AA no longer
  tracks its intelligence at all, so independent index comparisons will quietly stop updating.
- **Quality gaps unchanged**: overbuilding and one-shot prose weakness (Every link above); image
  hallucination reports now surfacing on Reddit (modelsentiment thread list, above).
- **Invisible to selection**: no domain rank at top-15 depth (scope fact lines) — the policy engine will
  not pick it on popularity; it can only enter via `hints`.

### Verdict

**RE-RESEARCH — keep and refresh the summary.** Decision-changing facts are new or live since the Oct
cycle: promo expiry is three weeks out (2026-11-21), GPT-6.1 Sol now undercuts it at $2/$10, AA has
stopped benchmarking it entirely, ChatGPT's default surface moved on 2026-10-07 — while OpenAI and Azure
both still name it a migration target (2026-12-11 / 2028-01-11). This is a dated asset worth describing,
not an exit.

---

## openai/gpt-oss-120b

### Benchmark standing

- **Artificial Analysis, read 2026-11-01**: **no deprecation banner**; **$0.15 in / $0.60 out**
  (AA's median-across-providers basis), 33% cache discount, **206.4 tok/s (#4/26)**, TTFT 0.81 s,
  131k context, knowledge May 2024, 117B total / 5.1B active, Apache 2.0, served via **17 providers** —
  https://artificialanalysis.ai/models/gpt-oss-120b. The Intelligence Index chart is not server-rendered,
  so AA's II value could not be re-read this pass (the page renders "N/A" for chart-only values).
- **Feed anchors carried**: AA **coding 30.4 / agentic 3.7 at $0.20/$0.95 (primary basis)** (parent feed,
  as_of 2026-11-01). The same feed read **coding 30.4 / agentic 3.7** on 2026-10-24 — verified in
  `research/2026-10-top15-k-gpt56sol-4oomini-oss120b-qwen36.md` — so the anchor is stable across a week.
  **Price bases disagree four ways** and all are current: feed primary-basis **$0.20/$0.95**; AA page
  median **$0.15/$0.60**; Oct-24 feed floor **$0.03/$0.15**; live OpenRouter endpoints **$0.012–$0.20 in
  / $0.045–$0.95 out** (2026-11-01) — https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints.
  Pick a basis and date it; do not mix them.
- **Design Arena anchor 898–992 (29–44% win) could not be re-verified** (feed 401). Its sibling's
  numbers were verified from the model page on 2026-10-25 (`research/2026-10-top15-i-…`), which is the
  best available provenance for the family's design standing.
- **Evals anchor (`gpqa 73.2%, tau 65.2%`) conflicts with OpenAI's own table**: OpenAI publishes
  **GPQA Diamond 80.1**, MMLU 90.0, HLE 19.0, AIME 2024 96.6, AIME 2025 97.9 for gpt-oss-120b —
  https://openai.com/open-models/. Different harness/effort, both first-party-adjacent; report the pair,
  don't average them. Prior-cycle OpenRouter-page reads (Math Index 93.4, LiveCodeBench 87.8%,
  MMLU-Pro 80.8% — against Terminal-Bench 4.0 **0.0%**, GDPval-AA 5.4%, AA-Omniscience accuracy 21.8%)
  are recorded in `research/2026-10-top15-k-…` citing https://openrouter.ai/openai/gpt-oss-120b.
- **Traffic (scope fact lines, 2026-10-02 → 2026-10-31)**: **1.85T tokens over 26 of 30 days** — down
  from 2.144T/28-of-30 in the prior window — yet **absent from all 29 task tags and all five domain
  pools** (https://openrouter.ai/api/v1/datasets/rankings-daily,
  https://openrouter.ai/api/v1/classifications/task?window=7d; key-gated in this pass).
- **Live endpoints, 2026-11-01**: **27 endpoints**, quants fp4 / bf16 / fp8 / int4 / fp16 / unknown,
  max completion **4,096 (DigitalOcean) → 117,964**, cheapest PrimeIntellect fp4 $0.012/$0.045, most
  expensive DeepInfra fp8 $0.20/$0.95; Google's Vertex route showed **status -5, 3.3% uptime over 30
  minutes** — https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints.
- **License/serving**: Apache 2.0 with a complementary use policy; MXFP4-native; weights on Hugging Face
  — https://huggingface.co/openai/gpt-oss-120b, https://github.com/openai/gpt-oss. Not served through the
  OpenAI API and not in ChatGPT — https://help.openai.com/en/articles/11870455-openai-open-weight-models-gpt-oss.

### Opinions

- **No successor, no deprecation — confirmed again**: "OpenAI has released no general-purpose base model
  successor to gpt-oss since 5 August 2025, providing only safeguard fine-tunes… build as if none is
  coming" (analysis published October 2026, citing the community's own 350-day tally) —
  https://www.gladlabs.io/posts/more-than-a-year-after-gpt-oss-openai-has-no-succe-b4cb6894. OpenAI's
  DevDay 2026 announced no open-weights release — https://www.infoq.com/news/2026/10/openai-devday-2026/,
  https://openai.com/index/devday-2026-recap/. It also appears nowhere on OpenAI's deprecation list
  — https://developers.openai.com/api/docs/deprecations (read 2026-11-01).
- **Longevity praise**: on its first birthday (2026-08-04), r/LocalLLaMA: "It is one of the best local
  models ever released, in both 20B and 120B versions… Its only competition is, in my opinion, Qwen 3.5
  122B" — https://www.reddit.com/r/LocalLLaMA/comments/1vfo8be/gptoss_has_turned_one_year_old_today/; and
  earlier "none of them feel quite as good as GPT-OSS 120b all-around… it's consistent, it calls tools
  properly" — https://www.reddit.com/r/LocalLLaMA/comments/1qrkb1b/how_was_gptoss_so_good/ (2026-01-30).
  HN: "easily best local model you can run today… when reasoning_effort is set to 'high'"
  — https://news.ycombinator.com/item?id=45774585.
- **Erosion, current**: HN thread "Why do you like gpt-oss-120b less now? What replaced it?" — "It's
  very likely to hallucinate. I'm mostly using Gemma 4 31B now when I need something offline"
  — https://news.ycombinator.com/item?id=48571577 (read 2026-11-01; page ages it ~4 months). A Reddit
  sentiment snapshot (2026-06-06) collects the split: "Qwen3.6-35B outperforms GPT-oss now, and is much
  smaller" / "Completely exchanged with Gemma 4" vs "Derestricted 120B is still a monster on CPU
  inference… still unbeaten as a combo of [speed, coding, knowledge]"
  — https://reddit.sentinel-team.org/posts/1tx1x6g/snapshots/2026-06-06T02%3A12%3A50.683757Z. Head-to-head
  testing says the same: Qwen3.5 wins on quality-per-GB while "developers report switching back to
  GPT-OSS-120b specifically for speed benefits… GPT-OSS-120b remains the conservative choice for
  production agentic workflows" — https://www.banandre.com/blog/qwen35-vs-gpt-oss-120b-local-agentic-coding
  (2026-03-15).
- **Implementation trap unchanged**: "Many LLM libraries/services/frontends don't pass these reasoning
  tokens back to the model correctly, which is why people complain about this model so much"
  — https://news.ycombinator.com/item?id=46364597. Independent judge: "strong on truthfulness, but overly
  conservative refusals hold them back" — https://oumi.ai/blog/openai-just-dropped-two-massive-open; the
  CoT-disobedience quirk is on OpenAI's own card — https://openai.com/index/introducing-gpt-oss.
- **Evidence gap**: no modelsentiment page exists (404 checked 2026-10-25, carried) — no Reddit aggregate
  for this pass.

### Known for

The self-hostable reasoning workhorse: contest-grade math and code (AIME 2025 97.9, GPQA 80.1
OpenAI-published) at near-commodity prices with real serving speed and an Apache-2.0 license, for
privacy-bound or high-volume math/code work.

### Caveats

- **Agentic/knowledge-work ceiling is unchanged** — agentic 3.7, Terminal-Bench 4.0 0.0%, GDPval-AA 5.4%,
  Omniscience accuracy 21.8% (prior-cycle reads of https://openrouter.ai/openai/gpt-oss-120b): skip
  research, writing and orchestration regardless of its traffic volume.
- **Quant/serving zoo widened to 27 endpoints** (fp4 → fp16, output $0.045–$0.95, completion caps
  4,096–117,964, one route at 3.3% half-hour uptime — endpoints URL above); broken reasoning-token
  round-trips make the same model look brilliant or broken depending on runner (HN link above); local
  GGUF guidance stays Q4_K_M with "2-bit… quality collapse at that bitrate is steep"
  — https://modelfit.io/quant-compare/gpt-oss-120b.
- **Stale world knowledge**: text-only, May-2024 cutoff (AA page) — wrong for research use without tools.
- **Its sibling's rank is gone**: `gpt-oss-20b` was inside the writing top-15 on 2026-10-24 and is now
  outside every pool (scope fact lines) — "the family is no longer invisible to selection" (Oct file) is
  no longer true as of 2026-11-01.
- **Invisible to selection**: 1.85T tokens of real demand but zero tag/domain presence means the policy
  engine cannot pick it; that will re-flag every cycle unless deliberately excluded (a `hints`/taste
  decision, which a refresh must not make).

### Verdict

**RE-RESEARCH — keep and refresh the summary.** No exit (no deprecation, no successor, 26/30 days of
traffic) and no rank (out of every pool). The entry stays as the family's standing reference; if the user
wants the stale flag gone, the honest mechanism is a documented exclusion, not a deletion.

---

## openai/gpt-oss-20b

### Benchmark standing

- **Rank (scope fact lines)**: **orchestration #18 of 26** — outside the top-15 — and no rank in the
  other four pools; it had been **writing #14 of 19** on 2026-10-24 (`research/2026-10-top15-i-…`), so its
  one foothold has slipped. **0.00T tokens over 0 of the 30 days** 2026-10-02 → 2026-10-31 — its second
  consecutive window with zero days in the daily top-51
  (https://openrouter.ai/api/v1/datasets/rankings-daily,
  https://openrouter.ai/api/v1/classifications/task?window=7d; key-gated in this pass).
- **Artificial Analysis, read 2026-11-01**: **$0.05 in / $0.22 out** (AA median-across-providers),
  **143.0 tok/s (#14/62)**, TTFT 0.71 s, 131k context, knowledge May 2024, 21B/3.6B, Apache 2.0, served
  via **4 providers** — https://artificialanalysis.ai/models/gpt-oss-20b. II chart not server-rendered
  (AA page read 2026-10-25 recorded High-effort II 9 / Low-effort II 10 via OpenRouter's feed row —
  `research/2026-10-top15-i-…`).
- **Feed anchors carried, partly new**: the brief's **coding 20.7 / agentic 1.2** (as_of 2026-11-01)
  could not be re-fetched (401) and is **new relative to 2026-10-24, when the feed carried coding null /
  agentic null** for this model — either the feed now benchmarks it or the anchor uses a different effort
  row; the discrepancy cannot be resolved without a key. Price anchor **$0.01/$0.02** matches the live
  floor: PrimeIntellect serves **$0.004 in / $0.018 out** (2026-11-01) —
  https://openrouter.ai/api/v1/models/openai/gpt-oss-20b/endpoints — while the catalog row ($0.03/$0.13)
  matches CoreWeave and AA's page says $0.05/$0.22. **Four bases again; date whichever is quoted.**
- **Evals anchor (`gpqa 64.9%, tau 53.3%`) vs OpenAI's published 71.5 GPQA Diamond** —
  https://openai.com/open-models/: report the pair, don't average (same harness caveat as 120b).
- **Design Arena 852–933**: verified on 2026-10-25 from the OpenRouter model page — dataviz ELO 933
  (rank 124), website ELO 852 (rank 143), bottom quartile — `research/2026-10-top15-i-…`, page
  https://openrouter.ai/openai/gpt-oss-20b; matches the parent's 2026-11-01 anchor; not re-fetched.
- **Independent evaluations**: ten-benchmark study — "gpt-oss-20B consistently outperforms
  gpt-oss-120B on several benchmarks… mid-tier overall… relative strength in code generation and notable
  weaknesses in multilingual tasks" — https://arxiv.org/abs/2508.12461; a local review scores it
  **88/100, #8 of 67** (27/30 coding jobs) — https://modeltested.com/models/gpt-oss-20b/; Local Agent
  Bench **93.4/100, #2 in tier** (run 2026-10-22, RTX 3090) —
  https://localagentbench.com/models/gpt-oss-20b/; DataRobot found **20b at low thinking effort repeatedly
  on the Pareto frontier**, "the best default choice for most non-scientific tasks"
  — https://www.datarobot.com/blog/testing-gpt-oss-models/.
- **Live endpoints, 2026-11-01**: **11 endpoints**, $0.004–$0.075 in / **$0.018–$0.30 out**, quants
  fp4/fp8/bf16/unknown, max completion **8,192 (SiliconFlow, status -2) → 117,964**; catalog-level max
  completion 32,768 (half of 120b's) —
  https://openrouter.ai/api/v1/models/openai/gpt-oss-20b/endpoints.

### Opinions

- **Structured-format weakness is the current theme**: FreshContext's extraction suite — "content mostly
  right but broke the format's rules far more often than Gemma 4 12B, which beat it on all three tests";
  85.7% vs 97.9% on nullable tagging, ungrounded entities 8 vs 2; thinking-on fixed the miscounts at
  ~37 s/case vs 1.6 s and still left ungrounded entities ("Yeah kill it") —
  https://freshcontext.io/benchmarks/models/gpt-oss-20b/.
- **The old complaints persist**: HF threads — "some issues with quality where it breaks while coding or
  performing bad at creative tasks" (discussion #92) and "This model is unbelievably ignorant… SimpleQA
  6.7/100" (discussion #14) —
  https://huggingface.co/openai/gpt-oss-20b/discussions/92,
  https://huggingface.co/openai/gpt-oss-20b/discussions/14; launch-thread framing was "basically Phi-5"
  with positive hands-on notes for the 20b specifically —
  https://news.ycombinator.com/item?id=44828884, https://www.seangoedecke.com/gpt-oss-is-phi-5/.
- **Counterweights**: "the closest thing I've gotten to running ChatGPT locally… give it a dense chunk of
  text and ask it to unpack it" — https://www.xda-developers.com/tested-local-models-for-same-tasks-each-model-won-at-something-different/
  (2026-04-21); "coherent, on-theme creative writing" in a local-inference review —
  https://slash.co/articles/testing-openais-latest-gpt-oss-20b-model-on-my-local-machine/; low-resource
  language reliability problems — https://arxiv.org/html/2510.01266v1.
- **Launch framing (carried)**: OpenAI's own claim — "similar results to OpenAI o3-mini on common
  benchmarks… run on edge devices with just 16 GB" — https://openai.com/index/introducing-gpt-oss/.

### Known for

The Apache-2.0, single-16GB-GPU reasoning toy — o3-mini-class claims at a $0.004–$0.03 in floor on
OpenRouter, bought for local/self-hosted inference and near-free short structured calls.

### Caveats

- **Invisible to selection, two windows running**: zero days in the daily rankings for 30 straight days
  twice (2026-09-25→10-24 and 2026-10-02→10-31), and now outside all five domain pools (scope fact lines,
  URLs above). Its previous "#14 writing" was already diagnosed as a **weak signal** — 3.7% usage share
  but 0.3% token share, i.e. many tiny calls, never prose volume
  (`research/2026-10-top15-i-…`); that foothold has now also dropped below the cut.
- **Local footprint has a context cliff**: ~12 GB weights + KV growth; "at 128k context, generation
  collapses to ~9 tok/s regardless of GPU" — cap context at 8k on 16 GB cards —
  https://runaihome.com/blog/gpt-oss-20b-local-ai-hardware-guide-2026/,
  https://github.com/ggml-org/llama.cpp/discussions/15396.
- **Serving spread**: 11 endpoints with completion caps 8,192 → 117,964 and one degraded route (endpoints
  URL above); catalog 32,768 cap means long generations silently truncate on the default route.
- **Quality floor**: factual recall ~SimpleQA 6.7, weak multilingual and creative output, format
  non-compliance worse than a 12B rival (links in Opinions); text-only, May-2024 knowledge
  (https://artificialanalysis.ai/models/gpt-oss-20b).
- **License**: Apache 2.0, commercial use allowed (https://openai.com/index/introducing-gpt-oss);
  training data opaque.

### Verdict

**RETIRE — delete the `openai/gpt-oss-20b` summary entry** (record the exit here, per the space-bunny
precedent). Evidence: outside every domain pool at top-15 depth, **zero daily-ranking days in two
consecutive 30-day windows**, its only former rank a usage/token-skewed weak signal that has itself
fallen below the cut, and no first-party data (feed) it uniquely depends on that a fresh pass could not
already rebuild. Nothing else in `policy.json` changes; `hints`/`fit` are untouched. If it re-enters a
pool, `--check-policy` will flag it as a gap and it gets researched anew.

---

## openai/gpt-4o-mini

### Benchmark standing

- **Rank (scope fact lines)**: **writing #19 of 26**, **orchestration #20 of 26** — below the cut in all
  five pools — and **0.00T tokens over 0 of 30 days** (2026-10-02 → 2026-10-31), its second consecutive
  empty window (https://openrouter.ai/api/v1/datasets/rankings-daily,
  https://openrouter.ai/api/v1/classifications/task?window=7d; key-gated in this pass).
- **Artificial Analysis, read 2026-11-01**: deprecation banner still points at **"GPT-5 mini"** (not
  OpenAI's current answer, `gpt-6-luna` — see Caveats); **$0.15 in / $0.60 out**, 50% cache discount,
  **107.2 tok/s (#26/59)**, 128k context, knowledge **Oct 2023**, non-reasoning, 3 providers —
  https://artificialanalysis.ai/models/gpt-4o-mini.
- **Feed anchors**: **coding 11.4** matches the 2026-10-24 feed read recorded in
  `research/2026-10-top15-k-…` (stable); feed price **$0.07/$0.30** disagrees with AA's page, OpenRouter's
  live endpoints and modelsentiment, which all say **$0.15/$0.60** — the feed row is a blended/floor
  basis (parent feed as_of 2026-11-01; 401 keyless). **Evals anchors `gpqa 43.6%, tau 30.7%`** are
  carried unverified; prior model-page reads give the harder ceiling: **GDPval-AA 0.0%, τ-Bench Banking
  2.9%, HLE 4.2%, LiveCodeBench 23.4%, Terminal-Bench 2.1 5.6%** —
  https://openrouter.ai/openai/gpt-4o-mini (read 2026-10-25, `research/2026-10-top15-k-…`).
- **Third-party standing, read 2026-11-01**: Arena text **#113/124**, AA Intelligence **#100/105**,
  AA **coding index #65 of 66**, Epoch capabilities **#85/91**, "$0.15 in / $0.6 out… OpenRouter, 1 Nov"
  — https://modelsentiment.com/m/gpt-4o-mini.
- **Live endpoints, 2026-11-01**: **3 routes** — OpenAI, Azure, Azure Sweden Central (+10%) — at
  **$0.15/$0.60** ($0.165/$0.66 Sweden), max completion **16,384**, 128k context —
  https://openrouter.ai/api/v1/models/openai/gpt-4o-mini/endpoints.

### Opinions

There is nothing left to praise; the evidence is installed-base gravity and migration pressure:

- **Reddit, read 2026-11-01 18:05 UTC**: **1 opinion in the last 7 days** — too few for an index (needs
  10); the 14-day table shows 0 opinions on 13 of 14 days —
  https://modelsentiment.com/m/gpt-4o-mini.
- Orca Security's scan of 426 AI-adopting organizations found GPT-4o-mini deployed in **28.6%** (5th of
  all models), ahead of newer OpenAI releases — https://tech-insider.org/gpt-4o-retirement-2026.
- OpenRouter + a16z's 100T-token study: tool invocation in early 2025 "concentrated among a small group
  of models: OpenAI's gpt-4o-mini and Anthropic's Claude 3.5 and 3.7 series"
  — https://arxiv.org/html/2601.10088v1.
- The migration-tax argument (rewrites, slower/more expensive successors for simple work; "80% of
  enterprise requests are simple lookups" routing advice) — https://tech-insider.org/gpt-4o-retirement-2026.

### Known for

The entrenched, dirt-cheap multimodal glue model: classification, extraction, vision/OCR passes,
structured outputs and tool-call loops in legacy pipelines that bill tokens by the billion.

### Caveats

- **Two shutdown dates, two providers — the conflict stands and is now corroborated**:
  - **OpenAI, notice dated 2026-10-14**: `gpt-4o-mini-2024-07-18` removed from the API on **2027-01-14**,
    "**Fine-tuned versions of these models follow the same shutdown schedule as their underlying base
    models**," recommended replacement **`gpt-6-luna`** —
    https://developers.openai.com/api/docs/deprecations (read 2026-11-01).
  - **Azure/Microsoft retirement schedule, read 2026-11-01**: `gpt-4o-mini 2027-04-14` (footnote 3),
    lifecycle "Deprecated," **no replacement listed** —
    https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule;
    independent trackers re-checked the same row on 2026-10-18 / 2026-10-31 —
    https://modelsunset.dev/models/azure-openai-gpt-4o-mini-2024-07-18/,
    https://sunsetdiff.com/models/azure-openai/gpt-4o-mini-2024-07-18/.
  - **Plan against 2027-01-14 (earlier, includes fine-tunes).**
- **Sources disagree on the replacement too**: OpenAI says `gpt-6-luna`; AA's banner still says "GPT-5
  mini" (https://artificialanalysis.ai/models/gpt-4o-mini); Azure lists none. And the migration is **not
  drop-in**: gpt-6-luna is a reasoning model that defaults to medium effort, bills reasoning tokens as
  output, accepts `temperature`/`top_p`/`top_logprobs` only at effort `none`, and on Chat Completions
  supports **function calling only with `reasoning_effort: "none"`** —
  https://if.codes/blog/gpt-4o-gpt-4-1-shutdown-migrate-to-gpt-6-luna,
  https://aivax.net/blog/migrate-gpt-4o-and-gpt-4-1-to-gpt-6-luna/.
- Out of ChatGPT since **2026-02-13** — https://openai.com/index/retiring-gpt-4o-and-older-models.
- Quality ceiling unchanged: AA coding index **#65 of 66**, Oct-2023 knowledge, non-reasoning, 16,384
  completion cap, 3 endpoints with unknown quant (links in Benchmark standing).
- **Invisible to selection**: below the cut in every pool and zero ranking days — new work must not start
  here; it exists in this policy only to document the exit.

### Verdict

**KEEP AS A DOCUMENTED EXIT — refresh the text with what is now confirmed.** Not a deletion: the model is
still served and its hard dates (OpenAI 2027-01-14 incl. fine-tunes vs Azure 2027-04-14) plus the
non-drop-in gpt-6-luna migration are precisely the decision-changing facts a dated summary exists to
carry. The exit note stays until both platforms stop serving it.

---

## Policy summaries

Proposed replacements for the `summaries` entries (2–3 sentences each, dated snapshots). Nothing in
`policy.json` was edited; `hints`/`fit` untouched. For `openai/gpt-oss-20b` the recommendation is
deletion — its text below is **a record of what the entry said, do not write it back**.

**openai/gpt-5.6-sol** — The July-2026 GPT-5.6 flagship (AA no longer publishes an index for it; feed
coding 78.3 / agentic 47.4 as of 2026-11-01; $4/$20 **promotional only through at least 2026-11-21**)
and still OpenAI's designated migration target — `gpt-5`/`o3` removal 2026-12-11, Azure GA to
2028-01-11 — while AA banners it toward GPT-6 Sol, ChatGPT's default surface moved to GPT-6 on
2026-10-07, and GPT-6.1 Sol now costs half as much ($2/$10). Pick it for a frozen baseline, an existing
deployment, or collaborative writing/research workloads it was tuned for (Every's favorite collaborator;
Reddit index 60, within noise); treat it as a dated asset. Re-price after 2026-11-21, expect >272K
prompts at 2×/1.5× ($8/$30) and fast-tier routes at $8–40/M out, keep a GPT-6/6.1 fallback, and remember
it is unranked in all five domain pools — traffic visibility, not a quality verdict.

**openai/gpt-oss-120b** — The Apache-2.0 self-host play (AA: no deprecation, $0.15/$0.60 median basis,
206.4 t/s #4/26 as of 2026-11-01; feed coding 30.4 / agentic 3.7 stable since 2026-10-24): contest-grade
math and code at $0.045–0.95/M out over **27 endpoints**, with **no successor and no deprecation anywhere
as of 2026-11-01** (DevDay 2026 shipped no new open weights). Its 1.85T tokens across 26 of 30 days show
real demand while it stays out of every task tag and domain pool — the engine cannot pick it on
popularity. Keep it for privacy-bound or high-volume math/code volume; skip research, writing and
orchestration (agentic 3.7, Terminal-Bench 4.0 0%, Omniscience 21.8%) and mind the quant zoo, the
Google route's 3.3% uptime, and broken reasoning-token handling in off-the-shelf harnesses.

**openai/gpt-oss-20b** — **RETIRE: delete this entry (record only, do not write to `policy.json`)** —
the Apache-2.0, 16GB-GPU sibling (21B/3.6B; AA $0.05/$0.22 median, live floor $0.004/$0.018, 2026-11-01)
whose standing is now outside every domain pool (best rank orchestration #18/26), with **zero days in the
daily token rankings across two consecutive 30-day windows**. Its former writing rank was already
diagnosed as a usage/token-skewed weak signal (3.7% usage, 0.3% tokens) that community reports never
matched in prose quality, and independent tests put format compliance below a 12B rival. It remains a
perfectly good local model (88/100, #8/67 in one review) — but a summary entry earns its place through
selection relevance, and this one has none left — re-research it fresh if it ever re-enters a pool.

**openai/gpt-4o-mini** — July-2024 legacy glue model (AA $0.15/$0.60, coding index #65/66, Arena
#113/124 as of 2026-11-01; zero ranking days in both the Oct and Nov windows): high-volume
classification, extraction, vision passes and structured outputs in **installed pipelines only** — never
research, writing or real coding. The exit is now dated on both sides: **OpenAI removes it 2027-01-14
including fine-tunes, replacement `gpt-6-luna`** (notice 2026-10-14), while **Azure says 2027-04-14 with
no replacement** — sources disagree; plan against the earlier date, and note the migration is not
drop-in (gpt-6-luna reasons by default; function tools on Chat Completions only work at effort `none`).
It sits below the top-15 cut everywhere (writing #19/26, orchestration #20/26), so new work must not
start here; keep this entry only to document the exit until both platforms stop serving it.