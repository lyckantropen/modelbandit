# Stale-summary group D (Google: 2.5 / 3-preview / 3.1 lite lines) — research pass (2026-11-01)

Scope: the three stale summaries flagged by `--check-policy --top 15 --scope` — all Google
lite/preview-tier models that now hold no top-15 rank in any of the five domains — plus a
stacking clarification against `google/gemini-3.5-flash-lite`. All facts dated. Sources pulled
this pass: OpenRouter `/api/v1/models/<id>/endpoints` (live fetch 2026-11-01), Google's Gemini
API deprecations page (page footer: "Last updated 2026-10-22 UTC"), Google Cloud Agent Platform
lifecycle docs (fetched 2026-11-01), Artificial Analysis model pages (fetched 2026-11-01),
Design Arena model pages and boards (boards stamped Oct 30–31, 2026), vendor blogs, HN/forum
threads. Benchmark anchors in the brief come from the first-party combined feed as of
2026-11-01T12:00Z; each is verified, extended, or flagged below. Brief-supplied daily-token
windows (1.63T / 3.41T / 2.21T) are carried as given — this pass had no key to re-derive them.

## Cross-cutting notes

- **AA changed scale between research passes.** The 2026-10-18 Google research ran against AA
  Intelligence Index **v4.3.2**; AA's pages now describe **v5.0** — "Artificial Analysis
  Intelligence Index v5.0 incorporates 9 evaluations: AA-Briefcase v1.1, AutomationBench-AA,
  Terminal-Bench 4.0, FrontierCode 2.0, AA-Omniscience v1.1, GDP.pdf, HLE-Diamond, CritPt v2
  (Hard Subset), Terminal-Bench-Science 0.1"
  (https://artificialanalysis.ai/models/gemini-3-flash, same banner on all three pages, fetched
  2026-11-01). October's "AA-16" for 3.1 Flash-Lite and the "7–9 estimated" for 2.5 Flash-Lite
  are therefore not comparable to anything on today's pages. Treat both as historical.
- **All three models now carry AA's deprecation banner**: "This model is deprecated. We only
  continue performance benchmarking for the default 10k input token workload" — on
  https://artificialanalysis.ai/models/gemini-2-5-flash-lite,
  https://artificialanalysis.ai/models/gemini-3-flash, and
  https://artificialanalysis.ai/models/releases/gemini-3-1-flash-lite (the old
  `/models/gemini-3-1-flash-lite` URL now 404s; AA moved it to a release slug). Intelligence on
  all three now renders "N/A / Unknown" publicly, so the brief's feed-side **AA coding 34.7 /
  agentic 1.6 for 3.1-flash-lite could not be independently verified** — public category charts
  are JS-gated and the entry is deprecated; carried as given-first-party, not confirmed.
  Successor banners: 2.5 page → "Gemini 2.5 Flash-Lite Preview (Sep '25)" (**stale banner** —
  that preview shut down 2026-03-31 per Google, below), 3-flash → Gemini 3.5 Flash, 3.1 →
  Gemini 3.5 Flash-Lite.
- **Google's two lifecycle surfaces disagree on 2.5 Flash-Lite, and the split is real.**
  Gemini API deprecations (updated 2026-10-22): `gemini-2.5-flash-lite` | July 22, 2025 |
  **No shutdown date announced**, under a note — "we are limiting access to the 2.5 models to
  users who have actively used them in the past. These models are not deprecated and will
  continue to be served until further notice through the API. For any new projects, use our
  latest models: 3.5 Flash-Lite or 3.8 Flash"
  (https://ai.google.dev/gemini-api/docs/deprecations). Google Cloud Agent Platform lifecycle
  table: `gemini-2.5-flash-lite` | July 22, 2025 | **Retirement date October 20, 2026** |
  replacements 3.8-flash / 3.5-flash-lite / Gemma 4
  (https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions, header
  note: "retirement timelines may be extended, they won't be moved to an earlier date";
  Vertex AI release notes had earlier moved the 2.5 dates to October 16, 2026,
  https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes). Third parties call
  the conflict out explicitly: "On Vertex AI, yes: … retire on October 20, 2026. The Gemini API
  lists no shutdown" (https://www.developersdigest.tech/blog/ai-model-shutdowns-2026-2027); a
  Google forum thread is literally titled "Conflicting information"
  (https://discuss.ai.google.dev/t/deprecation-shutdown-date-for-gemini-2-5-pro-conflicting-information/183251);
  Firebase docs warn "limited to projects that actively used it" (https://firebase.google.com/docs/ai-logic/models).
  **Observable consequence:** OpenRouter's 2.5-flash-lite endpoint set went from 5 first-party
  endpoints incl. Vertex (2026-10-18, per the October research file) to **3, all Google AI
  Studio** at the 2026-11-01 fetch — Vertex routes are gone, consistent with the Vertex
  retirement date having passed.
- **Anchor "price discrepancies" are tier mismatches, not errors.** The brief's
  `gemini-3-flash-preview-20251217: $0.90/$5.40` and `3.1-flash-lite AA $0.45/$2.70` are exactly
  the live **priority** tiers in today's OpenRouter endpoints (Vertex/AI Studio priority for
  both), while catalog $0.50/$3.00 and $0.25/$1.50 are the **standard** tiers and AA's public
  pages quote standard. All four numbers verified live 2026-11-01; no overwrite needed, just
  tier-label them.
- **Design Arena spot-checks.** 2.5: anchor 963–1099 (36–48% win) — public model page shows
  **Overall Win Rate 43%** and the Website board shows **1,095** Elo
  (https://designarena.ai/models/gemini-2.5-flash-lite-preview-09-2025;
  https://www.designarena.ai/leaderboard/website, updated Oct 31 2026) → consistent.
  3.1: anchor 1029–1164 (34–51%) — public page **Overall Win Rate 36%**
  (https://www.designarena.ai/models/gemini-3.1-flash-lite-preview) → consistent.
  3-flash: anchor 1166–1194 (57–63%) — Website board **1,194** Elo matches the top of the range
  (https://benchlm.ai/benchmarks/designarenawebsite, updated Oct 29 2026), Agentic Web Dev
  **1,161 / 49.6%** (#30, https://www.linkedin.com/posts/your-llm-radar_ai-llm-ainews-activity-7494699479959445504-IMJs),
  but the model page's **Overall Win Rate is 48%**
  (https://www.designarena.ai/models/gemini-3-flash-preview) and the OpenRouter model page's
  displayed boards read 1,161/50.6% and 1,090/46.6%
  (https://openrouter.ai/google/gemini-3-flash-preview). **The anchor's 57–63% win rates are not
  reproducible on the public boards I could reach** — flagged, not overwritten; Elo range checks
  out, win rates don't.
- OpenRouter evals anchors (gpqa/tau rows) are first-party feed values this pass could not
  re-derive without a key; carried as given and cross-checked against vendor claims where they
  exist (noted per model).

---

## google/gemini-2.5-flash-lite

### Status & identity (OpenRouter API fetch 2026-11-01)
- OpenRouter model created 2025-07-22 (created ts 1753200276; matches catalog). Still served:
  **3 endpoints, all Google AI Studio** — flex **$0.05/$0.20**, standard **$0.10/$0.40**,
  priority **$0.18/$0.72** per M (prices as of 2026-11-01), 1,048,576 context, max completion
  65,535, cache read $0.01/M (90% discount), native web_search tool at $0.014/query, uptimes
  100%/100%/97% (flex/std/priority 1-day) —
  https://openrouter.ai/api/v1/models/google/gemini-2.5-flash-lite/endpoints.
- GA on the Gemini API 2025-07-22; **no shutdown date announced on the Gemini API**, but access
  is limited to accounts that actively used it (Google's own note, deprecations page updated
  2026-10-22, https://ai.google.dev/gemini-api/docs/deprecations). The dated preview sibling
  `gemini-2.5-flash-lite-preview-09-2025` **did shut down 2026-03-31** (changelog announcement
  2026-03-09, https://ai.google.dev/gemini-api/docs/changelog; deprecations table, replacement
  `gemini-3.1-flash-lite`).
- Vertex/Agent Platform **retirement date October 20, 2026** (has passed as of today; table
  fetched 2026-11-01 still lists it un-extended,
  https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions);
  OpenRouter's Vertex endpoints for the model disappeared between 2026-10-18 and 2026-11-01
  (see cross-cutting note). Google steers new projects to **3.5 Flash-Lite or 3.8 Flash**
  (deprecations page note).
- Brief usage fact: **1.63T tokens over 2026-10-02..10-31, but only 19 of 30 days nonzero** —
  thinning traffic consistent with mid-October access/retirement churn (carried as given).

### Benchmark standing
- **Feed anchor: no AA row** for the dated preview slug — consistent with what AA shows today:
  the base model's page is deprecated with Intelligence **N/A** (it had shown *estimated* 9/7 on
  v4.3.2 as of 2026-10-18; AA has since dropped even the estimate, and the index itself moved to
  v5.0). AA still measures speed: **309.4 t/s (#3/59 non-reasoning), TTFT 0.31s**, $0.10/$0.40,
  1M context, knowledge cutoff Jan 2025 (https://artificialanalysis.ai/models/gemini-2-5-flash-lite,
  fetched 2026-11-01).
- **Feed evals (carried as given, unverifiable without the feed key):** gpqa_diamond **55.2%**
  ($0.0178/task), tau_bench airline **53.4%** ($0.0116) under `google/gemini-2.5-flash-lite`.
- **Design Arena (verified):** anchor 963–1099 (36–48%) vs public overall win **43%**, Website
  board **1,095** Elo (https://designarena.ai/models/gemini-2.5-flash-lite-preview-09-2025;
  https://www.designarena.ai/leaderboard/website, Oct 31 2026). No EQ-Bench Creative Writing or
  meaningful prose leaderboard presence (October tracker:
  https://evy.so/compare/best-llms-for-writing/).

### Opinions
- Still defended as a cheap workhorse even after the access clamp: "I still use 2.5 Flash Lite
  for a lot of my non-coding jobs, super cheap but great performance"
  (https://news.ycombinator.com/item?id=47235312); "I eventually settled on Gemini 2.5 Flash
  Lite as my workhorse … It was cheap, good enough, and most importantly, fast — but it's now
  being sunset and I'm not sure where to go" (https://news.ycombinator.com/item?id=49121047).
- Real deployments leaned on it for near-free extraction: Asxiv.org chat over arXiv papers
  (https://news.ycombinator.com/item?id=45212535); a self-hosted memory MCP reports 85.4%
  entity-extraction accuracy routing to it (https://news.ycombinator.com/item?id=47053534).
- The squeeze drew pushback: "there is a whole world of tasks for which Flash 2.5-lite was
  sufficiently intelligent. Given Google's deprecation policy, there will soon be no way to get
  that intelligence at that price" (https://news.ycombinator.com/item?id=47236092).
- Press/wiki trackers framed the access limit as existing-users-only months ago: "Gemini 2.5
  Flash-Lite (existing users only), $0.10, $0.40 … The 2.5 models are limited to accounts that
  have actively used them" (https://cloudinsight.cc/en/blog/gemini-vs-openai-api, Mar 21 2026);
  a Sep 18 2026 source ledger quotes Google's limiting-access notice verbatim
  (https://hugin.studio/sources).
- Stylometric reputation, not measured writing quality: "Gemini 2.5 Flash Lite writes 78% like
  Claude 3 Opus. Costs 185× less" (https://rival.tips/research/model-similarity).

### Known for
The near-free, near-instant multimodal volume tier of mid-2025 — translation, moderation,
classification and extraction at ~300–366 t/s for $0.10/$0.40 — now a legacy, access-limited
line Google points away from.

### Caveats
- **Split-brain lifecycle:** Gemini API keeps it alive for past users (no shutdown announced),
  Vertex/Agent Platform's retirement date of 2026-10-20 has passed and its Vertex endpoints are
  gone from OpenRouter — availability depends on which surface you call; third parties document
  the conflicting dates (https://www.developersdigest.tech/blog/ai-model-shutdowns-2026-2027;
  https://discuss.ai.google.dev/t/deprecation-shutdown-date-for-gemini-2-5-pro-conflicting-information/183251).
- Google explicitly says **not for new projects** (use 3.5 Flash-Lite or 3.8 Flash); AA has
  stopped indexing it entirely (Intelligence N/A, deprecated banner — which, note, wrongly
  suggests the already-shutdown Sep-25 preview as successor). Quality ceiling is 2025-era:
  knowledge cutoff Jan 2025, no thinking-effort control, 65,535-token output cap, no measured
  creative-writing score.
- Token traffic is thinning (19/30 active days in October, brief-supplied) — treat as borrowed
  capacity, not a going concern.

### Refresh decision: **RE-RESEARCH (keep, rewrite as legacy/access-limited)**
Not a retire (still served, still 1.63T tokens/month) and not an exit-documentation (hasn't left
the models list). The current summary already says "limits rather than deprecates"; the rewrite
should add: Vertex retirement date passed (2026-10-20) with Vertex endpoints removed from
OpenRouter between 2026-10-18 and 2026-11-01, AI Studio-only routing now, AA index dropped to
N/A on v5.0, and Google's explicit new-project steering to 3.5 Flash-Lite.

---

## google/gemini-3-flash-preview

### Status & identity (OpenRouter API fetch 2026-11-01)
- Created 2025-12-17 (ts 1765987078; matches catalog); every endpoint serves the dated permaslug
  **`google/gemini-3-flash-preview-20251217`**. Six first-party endpoints: flex
  **$0.25/$1.50**, standard **$0.50/$3.00**, priority **$0.90/$5.40** (Vertex global + AI
  Studio each), 1,048,576 context, max completion 65,536, `reasoning_effort` supported, native
  Google-Search tool ($0.014/query) —
  https://openrouter.ai/api/v1/models/google/gemini-3-flash-preview/endpoints. Health caveat at
  snapshot: the **Vertex global flex endpoint was status −5 (35% uptime 30m, 24.4% 1-day)**;
  all other tiers 100%.
- **Still in preview as of today — not renamed, not GA'd, not shut down.** Google's
  deprecations page (updated 2026-10-22) lists it under *Preview models*: `gemini-3-flash-preview`
  | December 17, 2025 | **No shutdown date announced** | recommended replacement
  **`gemini-3.6-flash`** (https://ai.google.dev/gemini-api/docs/deprecations). A prediction
  market on GA-before-Aug-21-2026 **resolved NO** on 2026-08-21
  (https://predictsixapp.com/resolutions/llyhtzgqT7JI5pPYqnCN/); third-party trackers still read
  "preview" on the 2026-10-01 models page (https://www.thirdbrain.tech/KB-AI/ai-models/language-models/gemini-3-dot-0)
  and "labeled legacy with gemini-3.6-flash as [replacement]" (https://blog.laozhang.ai/en/posts/gemini-3-1-pro-preview-free-api).
- **Succeeded, not replaced in place.** Google shipped 3.5-flash (2026-05-19; its endpoint now
  auto-routes to 3.6-flash), 3.6-flash and 3.5-flash-lite (2026-07-21), 3.7-flash (2026-08-13;
  auto-routes to 3.8), 3.8-flash (2026-09-02) — all in the deprecations table — while
  3-flash-preview keeps serving with **no shutdown date**, and traffic stays maximal (brief:
  **3.41T tokens, 30/30 days**, 2026-10-02..10-31).

### Benchmark standing
- **Feed anchor: no AA row for the dated slug** — but AA does carry a (now deprecated) page for
  the undated model: Intelligence **N/A**, speed **187 t/s (#2/46 non-reasoning)**, TTFT 0.90s,
  $0.50/$3.00 standard, 1M ctx, knowledge Jan 2025, 2 providers; banner suggests Gemini 3.5
  Flash (https://artificialanalysis.ai/models/gemini-3-flash, fetched 2026-11-01). So AA no
  longer publishes an intelligence number for it at all.
- **Vendor first-party (launch post, Dec 17 2025):** GPQA Diamond **90.4%**, HLE 33.7%
  (no tools), MMMU Pro **81.2%**, SWE-bench Verified **78%**, "30% fewer tokens [than 2.5 Pro]
  on average", priced $0.50/$3.00 (https://blog.google/products/gemini/gemini-3-flash/).
  **Discrepancy to record:** the existing policy summary's "GPQA 81.2" conflicts with this
  vendor text — 81.2% is Google's **MMMU Pro** number; the vendor GPQA Diamond figure is 90.4%.
  (MMLU Pro 88.2 / LiveCodeBench 79.7 in the old summary sit in the post's benchmark image and
  were not re-verifiable as text this pass.)
- **Feed evals (carried as given):** gpqa **88.5%**, tau_bench **73.3%** for
  `gemini-3-flash-preview-20251217` — sits between vendor GPQA Diamond 90.4% and the mistaken
  81.2; plausible for a different GPQA variant/harness, but not independently confirmable here.
- **Design Arena:** Elo range of the anchor verified (Website 1,194, #64-ish of 103,
  https://benchlm.ai/benchmarks/designarenawebsite, Oct 29 2026; Agentic Web Dev 1,161/49.6%
  per https://www.linkedin.com/posts/your-llm-radar_ai-llm-ainews-activity-7494699479959445504-IMJs);
  anchor win rates 57–63% not reproducible — public overall is **48%**
  (https://www.designarena.ai/models/gemini-3-flash-preview), other boards 46.6–50.6%
  (https://openrouter.ai/google/gemini-3-flash-preview). Flagged as a discrepancy.

### Opinions
- Launch was a hit: the HN thread scored **1,102 points / 580 comments**
  (https://news.ycombinator.com/item?id=46301851); "Don't let the 'flash' name fool you, this is
  an amazing model … so fast and it has such a vast world knowledge that it's more performant
  than Claude Opus 4.5 or GPT 5.2 extra high, for a fraction … of the inference time and price"
  (comment, same thread). Press: "Google launches Gemini 3 Flash, makes it the default model in
  the Gemini app" (https://techcrunch.com/2025/12/17/google-launches-gemini-3-flash-makes-it-the-default-model-in-the-gemini-app/);
  default for Search AI Mode (https://www.searchenginejournal.com/google-gemini-3-flash-becomes-default-in-gemini-app-ai-mode/563572/).
- **The search-grounding billing scandal is the defining controversy.** From mid-March through
  April 2026, developers reported bills spiking 4–15× on flat traffic with
  `gemini-3-flash-preview` + GoogleSearch grounding: one measured "~114 internal Google searches
  per single GenerateContent call"; another was billed ~20,000 grounding calls with the tool
  disabled over a weekend; Google's Ali Cevik confirmed on 2026-04-14 "due to a
  misconfiguration of the billing system of the Gemini API, users … were billed for a larger
  than consumed amount of searches. This is now fixed going forward" with corrections pending —
  https://discuss.ai.google.dev/t/sudden-cost-spike-with-gemini-3-flash-preview-despite-decreased-usage-april-2026/139138.
  Related threads: cost jump from 2026-03-16 (https://discuss.ai.google.dev/t/urgent-the-cost-of-api-access-has-increased-since-march-16-17-2026/134859),
  "enormous amount of search groundings" (https://discuss.ai.google.dev/t/gemini-search-grounding-billing-anomaly/139659),
  and spend caps failing outright — "$1,800 charged on a $100 cap"
  (https://www.reddit.com/r/googlecloud/comments/1szv8cr/warning_google_cloudgemini_api_spend_caps_do_not/).
  A follow-up complaint (2026-04-19) documents €290 of search-query charges against €10 of LLM
  queries and refunds framed as "one-time exceptions" (same forum thread).
- Preview-life complaints: model switching away from the selected model
  (https://github.com/orgs/community/discussions/187989) and recurring 503 overload errors
  (https://support.google.com/gemini/thread/421676491/facing-frequent-503-server-errors-for-gemini-3-flash-preview-model).
- Family-pricing cynicism dates to this era: "Flash 3 wasnt appropriately priced, it was priced
  to get you used to a certain level of spending, then they'll crank it up"
  (https://news.ycombinator.com/item?id=48196771).

### Known for
Google's Dec-2025 preview flash that became the Gemini app and Search AI Mode default —
Pro-grade agentic reasoning and coding at $0.50/$3.00, still serving after three newer Flash
generations shipped around it.

### Caveats
- **Still literally "preview"**: silent model swaps are possible by definition; Google names
  `gemini-3.6-flash` as the recommended replacement even though no shutdown is announced, and
  AA already banners it deprecated. Pin the dated permaslug (`-20251217`) on OpenRouter.
- Grounding/search-query billing burned users badly in Mar–Apr 2026 (acknowledged bug, since
  fixed, refunds uneven); Google's free tier is 5,000 search queries/month before per-query
  charges (Google rep, same thread). Meter grounding.
- Vertex flex tier was degraded at the 2026-11-01 snapshot (status −5, 24–35% uptime); knowledge
  cutoff Jan 2025 despite being the app's default; AA gives it no current intelligence score.

### Refresh decision: **RE-RESEARCH (keep, rewrite with current facts)**
The existing summary's core claims all verify (preview, grounding billing saga, supersession by
3.6/3.7 Flash). The rewrite should add: Google's deprecations table now names `gemini-3.6-flash`
as replacement *without* a shutdown date (2026-10-22); GA question publicly resolved NO
(2026-08-21); the billing bug was acknowledged and fixed 2026-04-14; AA is fully deprecated on
it (index N/A, v5.0); and correct the "GPQA 81.2" claim to MMMU Pro 81.2 / GPQA Diamond 90.4%.

---

## google/gemini-3.1-flash-lite

### Status & identity (OpenRouter API fetch 2026-11-01)
- OpenRouter model created 2026-05-07 (ts 1778168828 = GA date; matches catalog); all 8
  endpoints serve **`google/gemini-3.1-flash-lite-20260507`**. Tiers: flex **$0.125/$0.75**,
  standard **$0.25/$1.50**, EU/US **$0.275/$1.65**, priority **$0.45/$2.70** (Vertex global +
  AI Studio); 1,048,576 context, max completion 65,536, `reasoning_effort`, native
  Google-Search tool ($0.014/query), cache read $0.025/M (90% off) —
  https://openrouter.ai/api/v1/models/google/gemini-3.1-flash-lite/endpoints. Health at
  snapshot: **Vertex global flex status −5 (41.7% uptime 30m, 33% 1-day)**; other tiers 100%.
- Preview 2026-03-03, GA 2026-05-07. The **preview slug `gemini-3.1-flash-lite-preview` was
  shut down 2026-05-25** (deprecations table; replacement: the GA model,
  https://ai.google.dev/gemini-api/docs/deprecations).
- **Served with a dated floor:** Gemini API deprecations table gives `gemini-3.1-flash-lite` |
  May 7, 2026 | **Shutdown May 7, 2027** | replacement **`gemini-3.5-flash-lite`** (same page,
  updated 2026-10-22); Agent Platform lifecycle agrees: "May 7, 2027 or later"
  (https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions). A
  community reading of the table worries about exactly that date
  (https://www.reddit.com/r/GeminiAI/comments/1tupe9h/).
- Brief usage: **2.21T tokens, 30/30 days** (2026-10-02..10-31) — full-window traffic, i.e.
  still a live workhorse despite being nominally succeeded.

### Benchmark standing
- **AA anchor (coding 34.7, agentic 1.6): unverifiable this pass.** AA's page (now at
  https://artificialanalysis.ai/models/releases/gemini-3-1-flash-lite; the old URL 404s) is
  **deprecated**, Intelligence renders **N/A**, and it banners Gemini 3.5 Flash-Lite as the
  newer release (fetched 2026-11-01). What AA still publishes: speed **326.8 t/s (#6/144)**,
  **TTFT 4.75s** (high — thinking included), $0.25/$1.50 standard, reasoning model, 1M ctx,
  knowledge Jan 2025. October's "AA-16" was on v4.3.2 and predates the v5.0 rescale — do not
  carry it forward as current.
- **Vendor first-party (launch posts):** LMArena Elo 1,432, GPQA Diamond **86.9%**, MMMU Pro
  76.8%, "outperforms 2.5 Flash with a 2.5× faster Time to First Answer Token and 45% increase
  in output speed" (https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-lite/;
  GA: https://cloud.google.com/blog/products/ai-machine-learning/gemini-3-1-flash-lite-is-now-generally-available).
- **Feed evals (carried as given):** gpqa **82.1%**, tau_bench **71.3%** under
  `gemini-3.1-flash-lite-20260507` — below the vendor's 86.9% GPQA Diamond, plausibly a
  different harness/variant; not independently confirmable here.
- **Design Arena (verified):** anchor 1029–1164 (34–51%) vs public **Overall Win Rate 36%**
  (https://www.designarena.ai/models/gemini-3.1-flash-lite-preview); OpenRouter's model page
  also surfaces a Models Arena SVG Elo of 1,049
  (https://openrouter.ai/google/gemini-3.1-flash-lite-preview). No EQ-Bench Creative Writing row
  (October tracker, https://evy.so/compare/best-llms-for-writing/) — writing standing rests on
  LMArena Text 1,433, well below Gemini 3.6–3.8 Flash's EQ Elos of 1603–1748 (same tracker,
  updated 2026-10-12).

### Opinions
- Launch thread dominated by **price-hike backlash**: "$0.25 IN / $1.50 OUT vs. Gemini 2.5
  Flash-Lite $0.10 IN / $0.40 OUT" (https://news.ycombinator.com/item?id=47235369); "That's a
  150% increase in input costs and 275% increase on output costs over the same sized previous
  generation" (https://news.ycombinator.com/item?id=47236090); "What the fuck is this price
  hike? … Can we get flash lite lite please?"
  (https://news.ycombinator.com/item?id=47237891); launch thread
  (https://news.ycombinator.com/item?id=47234962).
- **The reasoning-cost trap** is the standing operational warning: "Do not use 3.1 Flash-Lite
  with HIGH reasoning, it reasons for almost max output size, you can quickly get to millions of
  tokens of reasoning in a few requests"
  (https://news.ycombinator.com/item?id=47239608; effort-level comparison:
  https://aibenchy.com/compare/google-gemini-3-1-flash-lite-preview-low/google-gemini-3-1-flash-lite-preview-medium/google-gemini-3-1-flash-lite-preview-high/google-gemini-3-flash-preview-low/).
  Counterpoint on total cost: AA found it used fewer than half the tokens of 2.5 Flash-Lite yet
  was "20% more expensive to run for their complete Intelligence index benchmark"
  (https://news.ycombinator.com/item?id=47236248).
- **Transcription is the praised niche**: "1.8× faster than Gemini 3 Flash … ~$0.50/mo for heavy
  users … 100+ languages" (https://news.ycombinator.com/item?id=47235912); "It's the best STT
  model in my experience … Flash Lite is much better [on latency] than Gemini 3 Flash"
  (https://news.ycombinator.com/item?id=47236467).
- Agentic substitution tests: "If 3.1-flash-lite can do the job, this solves basically all
  latency issues for agentic workflows" — with published workflow tests
  (https://news.ycombinator.com/item?id=47235401, https://upmaru.com/llm-tests/simple-tama-agentic-workflow-q1-2026);
  a hybrid on-device startup routes only 15–35% of queries to it as cloud fallback
  (https://news.ycombinator.com/item?id=49010782).
- It was also caught in the April 2026 billing bug: an operator reports "google billing counts
  EACH gemini-3-flash-preview and each gemini-3.1-flash-lite call as GoogleSearchGrounding"
  with grounding disabled, and switched back to 2.5 models as a workaround
  (https://discuss.ai.google.dev/t/sudden-cost-spike-with-gemini-3-flash-preview-despite-decreased-usage-april-2026/139138/9,
  2026-04-13).
- Successor-migration pull is explicit: Google names 3.5 Flash-Lite as the replacement
  (deprecations page), and comparison content is already aimed at converts —
  https://www.tryfriday.ai/blog/gemini-3-5-flash-lite-vs-gemini-3-1-flash-lite.

### Known for
Google's GA high-volume lite tier — full multimodal input, native search tool, ~327 t/s and 1M
context for transcription, moderation, extraction and light agentic sub-calls — shipped at a
lite-model-unfriendly price and already marked for succession.

### Caveats
- **Dated floor: earliest Gemini API shutdown 2027-05-07**, replacement
  `gemini-3.5-flash-lite`; AA independently banners it deprecated in favor of 3.5 Flash-Lite.
  Its own preview slug died 2026-05-25 — pin the `-20260507` permaslug.
- Price is 2.5–3.75× the 2.5 tier it replaced ($0.25/$1.50 standard; $0.45/$2.70 priority);
  pin `reasoning_effort` low/medium (high effort can burn millions of reasoning tokens across a
  few requests). Vertex flex tier was degraded at snapshot (status −5, 33% 1-day uptime); TTFT
  4.75s with thinking — not an interactive-streaming pick.
- No measured creative-writing score (absent from EQ-Bench tracker; LMArena Text 1,433 trails
  the 3.6–3.8 generation). Caught in the March–April 2026 grounding-billing bug. AA's public
  intelligence number is gone (N/A on v5.0).

### Refresh decision: **RE-RESEARCH (keep, rewrite with dated floor + successor)**
Still served and fully busy (30/30 days), so not a retire/exit — but the summary must now carry:
Gemini API shutdown floor 2027-05-07 with `gemini-3.5-flash-lite` named replacement (Google,
2026-10-22), AA deprecation banner + index removal on v5.0, preview-slug shutdown 2026-05-25,
price-tier labels (standard $0.25/$1.50 vs priority $0.45/$2.70), and the flex-endpoint health
warning.

---

## Family stacking as of 2026-11-01

How the four lite/preview lines actually sit, from Google's own pages (all cited above):

1. **`gemini-2.5-flash-lite` (GA 2025-07-22) — legacy, access-limited, surface-split.**
   Gemini API: no shutdown announced, but restricted to accounts that have used it; Google tells
   new projects to go to **3.5 Flash-Lite or 3.8 Flash**
   (https://ai.google.dev/gemini-api/docs/deprecations). Vertex/Agent Platform: retirement date
   2026-10-20, now passed; its Vertex endpoints are gone from OpenRouter (AI Studio-only as of
   2026-11-01). AA: deprecated, index N/A.
2. **`gemini-3-flash-preview` (2025-12-17) — a different lane, not part of the lite ladder.**
   This is the *non-lite* Flash tier (app/Search default). Still **preview** with **no shutdown
   date**; Google's table names `gemini-3.6-flash` as recommended replacement but keeps serving
   it (https://ai.google.dev/gemini-api/docs/deprecations, 2026-10-22). Successive Flash
   generations shipped around it — 3.5-flash (2026-05-19, now auto-routes to 3.6-flash),
   3.6-flash (2026-07-21), 3.7-flash (2026-08-13, auto-routes to 3.8), 3.8-flash (2026-09-02) —
   yet it remains OpenRouter's busiest of the three here (3.41T tokens, 30/30 days).
3. **`gemini-3.1-flash-lite` (preview 2026-03-03 → GA 2026-05-07) — current-but-succeeded lite.**
   Preview slug shut 2026-05-25; GA model guaranteed to **2027-05-07 (or later)** with
   `gemini-3.5-flash-lite` as Google's named replacement; AA also banners the successor. Still
   fully trafficked (2.21T tokens, 30/30 days).
4. **`gemini-3.5-flash-lite` (2026-07-21) — today's recommended lite.** OpenRouter: permaslug
   `google/gemini-3.5-flash-lite-20260721`, 8 endpoints, flex **$0.15/$1.25**, standard
   **$0.30/$2.50**, EU/US $0.33/$2.75, priority $0.54/$4.50 (fetch 2026-11-01), 1M ctx, 65,536
   max out, `reasoning_effort`, native search —
   https://openrouter.ai/api/v1/models/google/gemini-3.5-flash-lite/endpoints. No shutdown
   announced; Agent Platform floor "July 21, 2027 or later"
   (https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions).
   Launched together with 3.6-flash (https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/);
   DeepMind positions it as "the intelligence, speed, and cost efficiency" tier for agentic
   retrieval/tool use (https://deepmind.google/models/gemini/flash-lite/, model card at
   https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/). It already ranks
   (research #12, brief) with its own summary, so no new summary is proposed here.
   AA-side context: AA posted "Gemini 3.5 Flash costs ~$1.5k to run the [AA] Intelligence Index
   … over 5 times the cost of running Gemini 3 Flash"
   (https://x.com/ArtificialAnlys/status/2056795071572582675) — i.e. the *Flash-Lite* line
   stays the cheap rung even as 3.5 Flash went upmarket.

Net: **2.5 lite = legacy/limited (leave only), 3-flash-preview = busy preview in a parallel
non-lite lane (pin + meter), 3.1 lite = served with a 2027-05-07 floor (migrate planning),
3.5 lite = the current pick for new lite work.**

---

## Policy summaries

**google/gemini-2.5-flash-lite.** Google's June/July-2025 near-free multimodal volume tier
($0.10/$0.40 standard, ~309 t/s, 1M ctx, AI-Studio-only on OpenRouter as of 2026-11-01) — pick
it only for existing pipelines doing verifiably mechanical work: translation, moderation,
classification, bulk extraction, cheap orchestration sub-calls; never for judgment or new
projects. Its status is split: the Gemini API keeps it for past users with no shutdown announced,
but Vertex/Agent Platform's 2026-10-20 retirement date has passed, its Vertex endpoints are gone,
AA has dropped it from the index entirely, and Google explicitly points new work to 3.5
Flash-Lite — so treat availability as borrowed and migrate on sight.

**google/gemini-3-flash-preview.** Google's Dec-2025 preview flash — the Gemini-app/Search
default with vendor GPQA Diamond 90.4% / SWE-bench Verified 78% at $0.50/$3.00 standard
($0.90/$5.40 priority; pin `-20251217`) — still in preview with no shutdown date as of
2026-10-22, though Google names 3.6-flash as its replacement and AA banners it deprecated.
Pick it for high-volume agentic/coding work where its price/performance still beats newer Flash
tiers; caveats that change decisions: silent preview swaps are possible, the March–April 2026
search-grounding billing misconfiguration (acknowledged and fixed 2026-04-14, refunds uneven)
means meter grounding, spend caps failed users, and the Vertex flex route was flaky at the
2026-11-01 snapshot.

**google/gemini-3.1-flash-lite.** Google's GA lite tier (2026-05-07; $0.25/$1.50 standard,
$0.45/$2.70 priority, ~327 t/s, 1M ctx, audio/video in, native search) — the default cheap call
for transcription ("best STT model in my experience"), moderation, translation and light
tool-using orchestration. Pin `reasoning_effort` low/medium (high effort "reasons for almost max
output size"), mind flex-tier throttling and a 4.75s TTFT, and plan the exit: Google has already
named `gemini-3.5-flash-lite` as its replacement with an earliest shutdown of **2027-05-07**,
AA has deprecated it, and no measured creative-writing score exists (LMArena Text 1,433 trails
the 3.6–3.8 generation).