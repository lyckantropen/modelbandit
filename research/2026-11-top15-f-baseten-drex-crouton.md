# Group F — Baseten decision models, Drex Max, Crouton (2026-11 summaries refresh)

Research pass per `research/README.md` §2, dated **2026-11-15**. Rank/token/window facts come
from the parent's `--check-policy`/`--anchors` output (2026-11-15) and are labeled "repo check";
the anchors feed carries **no benchmark rows for any of the four models** (stated by the parent
for all four). Every web claim carries a URL; prices and index numbers are dated snapshots.
Slug date suffixes are OpenRouter snapshot dates, not necessarily vendor release dates — noted
per model where sources disagree.

A cross-cutting fact from the prior cycle applies here: the chat models catalog omits decision
models class-wide (group-e, verified 2026-11-01), so "not in the model list" for the three
decision models below is expected, not a delisting signal — while `stealth/crouton-alpha` is a
genuine exit (see its section).

---

## baseten/elephant-1-20261021

**What it is.** A 9B non-generative decision model from **Base Labs**, Baseten's research team:
a full fine-tune of Qwen3.5-9B (MIT weights) that takes a state (text or JSON, image input
supported) plus typed `noul`/`choice`/`score` questions and returns a calibrated probability per
option in one forward pass, TypeSafe System One compatible, 16,384-token context (requests
longer are refused, not truncated). Released 2026-10-21 alongside its 27B sibling mammoth-1
(https://www.baseten.co/blog/the-best-decision-models-in-the-world-mammoth-1-and-elephant-1/;
https://huggingface.co/baselabs/elephant-1; OpenRouter page "Released Oct 21, 2026",
https://openrouter.ai/baseten/elephant-1-20261021). On OpenRouter: **$0.035/M input, output
free, 16K context, single provider (Baseten)**, served via the alpha Decisions endpoint — chat
SDKs cannot call it (same page, snapshot 2026-11-15). The slug suffix `20261021` matches the
vendor release date. Baseten's free launch week ended 2026-10-27 23:59 PT; paid pricing
$0.035/M in / $0.10 for mammoth (changelog dated 2026-11-01:
https://www.baseten.co/resources/changelog/elephant-1-and-mammoth-1-pricing).

**Benchmark standing — no rows in the first-party anchor feed (confirmed: none, per the
parent's 2026-11-15 anchors), but third-party decision boards do score it:**

- **Jev Decision Index (community board).** Release claim: **62.65 Full, tied 7th (tech report)
  / 8th (blog) of 208, best model under 15B** on edition 0.4
  (https://www.baseten.co/blog/mammoth-1-and-elephant-1-frontier-decision-models). The board
  was revised to **0.4.1 on 2026-10-22** and elephant-1's Full score there is **60.26, with a
  public score of 72.24** — the release numbers are stale
  (https://systemonemodels.org/models/elephant-1, updated 2026-10-23;
  https://blog.mushroom.cv/blog/decision-models-comparison, board data 2026-10-22;
  https://github.com/OpenAgentsInc/openagents/blob/main/docs/research/baselabs-decision-models/README.md).
  Note the two secondary sources disagree on its 0.4.1 **rank** (systemonemodels: 40th of 229
  rows; OpenAgents' table: 8) — quote the score, not the rank.
- **Artificial Analysis Decision Index (a separate AA board from the anchor feed's chat
  boards).** Baseten worked with AA pre-release: **65, tied with Liquid AI's d1-ultra**
  (https://www.baseten.co/blog/mammoth-1-and-elephant-1-frontier-decision-models). The
  model card's own replica says 65.2 (HF card, above). The live AA board checked
  **2026-10-23 gave 64.69, 3rd of 17** behind d1-ultra (65.25) and SubQ Snap 1.1 (65.00), ECE
  0.038, $8.40 per 1M tasks, median 165 ms per task; weakest areas are knowledge —
  Omniscience accuracy 11.6, HLE-MultipleChoice 18.3
  (https://systemonemodels.org/models/elephant-1).
- **Contamination flag, from the board itself:** "elephant-1's training includes train splits of
  Decision Index benchmarks, as the author declared," and one private new-domain test was
  excluded from both Base Labs models because the board found training-data overlap signs;
  Baseten's report says it removed overlapping examples
  (https://github.com/OpenAgentsInc/openagents/blob/main/docs/research/baselabs-decision-models/README.md;
  https://systemonemodels.org/models/elephant-1).
- Repo check (2026-11-15): ranked research #8/19; **0 tokens in the 2026-10-16..2026-11-14
  window** — in tension with OpenRouter's own pages, which show production apps sending traffic
  (top app "The Lull", 282M tokens; availability panels dated Oct 31–Nov 3, 99.99%; snapshot
  2026-11-15, https://openrouter.ai/baseten/elephant-1). Both figures stand; the zero is most
  plausibly a chat-catalog window missing Decisions-API traffic (class-wide, group-e).

**Opinions:**
- Reception is positive but niche. The main community write-up is a detailed r/LocalLLaMA
  release thread (~18 comments, peak score 28; posted 2026-10-23) summarizing the AA tie,
  ~$8 vs ~$31 per 1M tasks against d1-ultra, and the abstention behavior: "93 non-hallucination
  rate but only 12 accuracy, so it says 'I don't know' a lot rather than guessing… Routing,
  guardrails, tool-call gating and LLM-as-judge at volume look like the sweet spot," ending by
  asking whether anyone has run it against their own evals
  (https://www.reddit.com/r/LocalLLaMA/comments/1xdirky/).
- Trade press repeated vendor claims with a caution flag: AiLookout (2026-10-22) noted "the
  scores are not yet independently checked" at publication and the report/blog rank discrepancy
  (7th vs 8th) (https://ailookout.news/blog/baseten-base-labs-releases-mammoth-1-and-elephant-1-open-decision-models);
  an aggregator's heat tracker rated the story "medium heat" as of 2026-11-05
  (https://ainews.leverageai.com.au/case/baseten-elephant-1-decision-model).
- A Chinese-language comparison piece (2026-10-24) specifically warns that Baseten's launch
  scores belong to board edition 0.4 and "current still world #1" does not hold on 0.4.1, and
  that elephant-1 leads Jev 1.14 by only 0.02 Full points — "cannot declare a stable business
  win" (https://blog.mushroom.cv/blog/decision-models-comparison).
- No negative press and no hands-on failure reports found; no independent test of the open
  weights against user task suites found beyond the boards above.

**Known for:** Baseten's 9B MIT-licensed decision model — calibrated probabilities over your
own options in one forward pass, tied for #1 on AA's Decision Index at launch and the best
sub-15B model on the Jev Decision Index.

**Caveats that change decisions:** never chat — Decisions/System One API only (chat SDKs will
not work); 16K context, longer requests refused; **single provider (Baseten)** on OpenRouter
(no routing redundancy); declared benchmark-train-split overlap and one excluded private test
inflate trust in board scores — test on your data; deliberately abstention-heavy (near-zero
obscure-fact accuracy); model card says text+image input but OpenRouter lists text-only for
this route (systemonemodels, 2026-10-23); release-recency — three weeks old at this check, and
the launch free week ended 2026-10-27.

---

## baseten/joey-1-20261029

**What it is.** The smallest of Base Labs' decision family: a **2B** full fine-tune of
Qwen3.5-2B (MIT weights), same single-pass probability output and System One API, 16,384-token
context, text + image in. Released **2026-10-29** (slug suffix matches), priced at
**$0.01/M input, output free** on Baseten Model APIs and OpenRouter
(https://www.baseten.co/blog/decisions-for-a-penny-introducing-joey-1/;
https://huggingface.co/baselabs/joey-1;
https://openrouter.ai/baseten/joey-1-20261029, snapshot 2026-11-15; Baseten changelog dated
2026-11-01: https://www.baseten.co/resources/changelog/joey-1-available-on-baseten). On
OpenRouter it is single-provider (Baseten), P50 latency 0.07–0.12 s across snapshots,
3-day availability 99.96% for Nov 9–12, 98.83% over the last 24 h at snapshot time
(https://openrouter.ai/baseten/joey-1, snapshot 2026-11-15).

**Benchmark standing — no rows in the first-party anchor feed (confirmed, per the parent's
2026-11-15 anchors), and what exists is almost entirely vendor-run:**

- Model card (Baseten-run): **Jev Decision Index 0.4 public split 63.30, #37 of 230, "best
  model under 4B"**; **62.9 on Baseten's own replica of the AA Decision Index** — this is
  explicitly a replica, not an Artificial Analysis measurement
  (https://huggingface.co/baselabs/joey-1).
- Baseten's headline claim — "strongest decision model with 3B or fewer parameters" — is from
  **internal testing with "details coming soon"** (https://www.baseten.co/blog/decisions-for-a-penny-introducing-joey-1/).
- Latency claims are Baseten's own production measurements: P50 20 ms for a 2,000-token
  request, ~2.5× faster than elephant-1 (49 ms), "5× faster than comparable decision models"
  with the comparators unnamed (same blog; MarkTechPost notes the unnamed comparison:
  https://www.marktechpost.com/2026/10/29/baseten-joey-1-2b-decision-model).
- One attached third-party harness result on the HF page is weak-looking: a
  `safeagents-judge-bench` eval-result row reports balanced accuracy 0.5 / AUROC 0.48
  (https://huggingface.co/baselabs/joey-1) — context/scale not documented on the page; treat
  as a flag to investigate, not a verdict.
- No independent AA run, no modeltested review, no press benchmark found. Repo check
  (2026-11-15): research #13/19, **0 tokens** in the 2026-10-16..2026-11-14 window — while
  OpenRouter's activity panel shows prompt tokens (528M in one undated crawl, 44.4M in
  another), same class-wide decision-traffic accounting caveat as elephant-1.

**Opinions:** release coverage only, no critical reviews found. MarkTechPost (2026-10-29)
relays the pricing/latency claims and notes the escalation pattern — uncertain answers go to
elephant-1/mammoth-1 — and records "No official GGUF/quantized builds listed yet"
(https://www.marktechpost.com/2026/10/29/baseten-joey-1-2b-decision-model). Unite.AI
(2026-10-29) and LLMs Blog (2026-10-29) are likewise straight release summaries
(https://www.unite.ai/baseten-releases-joey-1-a-2b-open-weights-decision-model/;
https://www.llms.blog/posts/baseten-joey-1-open-decision-model). No community thread with
hands-on testing found; OpenRouter's page notes Jev Lab has recorded recipes for it
(snapshot 2026-11-15).

**Known for:** Baseten's cheapest, fastest decision model — a 2B probability-a-router for
high-volume routing and guardrail checks at $0.01/M input.

**Caveats that change decisions:** Decisions API only, 16K context, **single provider
(Baseten)** on OpenRouter; every published number (index scores, "strongest ≤3B", 20 ms P50)
is Baseten-run — no independent evaluation exists yet; shares elephant-1's declared
benchmark-train-split training-data overlap caveat (same 6.21M-example mix, same technical
report: https://huggingface.co/baselabs/joey-1); tiny model — intended as a first-line filter
that escalates uncertain cases, not a standalone; three weeks old at this check.

---

## nace-ai/drex-max-20261016

**What it is.** Nace.AI's flagship decision model: a dense **27B multimodal** model (48
Gated-DeltaNet linear-attention + 16 non-causal full-attention layers, 255-way readout head)
that answers typed questions over text, JSON and **images** in one pass — built for
computer-use/browser agents deciding from screenshots. API-only at the hosted routes
(Console + OpenRouter), Nace.AI Open RAIL-M license with v1 weights open on Hugging Face
(https://www.nace.ai/drex; https://huggingface.co/nace-ai/drex-max-v1;
https://github.com/nace-ai/drex-decision-models). **Date spread — do not treat the suffix as
the release date:** OpenRouter slug says `20261016`; the OpenRouter page header says "Released
Oct 21, 2026"; Nace's GA blog is dated 2026-10-19 (updated that day); Nace's models page
carried 2026-10-13 (group-e file); decisions-api.dev says released Oct 21
(https://www.nace.ai/blog/introducing-drex-max;
https://decisions-api.dev/model/drex-max; group-e: `2026-11-top15-e-exits-misc.md`).
**The id now serves v1.1 in place** — `drex-max-v1.1` was released 2026-10-28 and replaced the
original under the same id (Nace retired the original id on their side 2026-11-08, forwarding
to v1.1) (https://www.nace.ai/drex; https://agentapilist.com/apis/nace-drex, verified
2026-11-11).

**Status/price on OpenRouter (snapshot 2026-11-15):** listed at **$0.06/M input after a 50%
discount (provider row: DeepInfra $0.12 → $0.06), output free**, weighted-average effective
input $0.1191/M; **262K context** (Nace's own product page instead says 131,072 tokens per
question — the figures conflict); **single provider (DeepInfra)**, P50 0.34 s, 99.99%
availability Nov 12–15; activity panel shows 952M prompt / 323M completion tokens (undated
crawl). Nace's own API lists $0.03/M input (50% off the $0.06 list), output not billed
(https://openrouter.ai/nace-ai/drex-max;
https://www.nace.ai/drex; https://agentapilist.com/apis/nace-drex). Repo check (2026-11-15):
research **#10/19**, finance_trading **#1/10** (the tag leader), **0 tokens** in the
2026-10-16..2026-11-14 chat window — same decision-traffic caveat as above, though the
OpenRouter page shows nonzero activity.

**Benchmark standing — no rows in the first-party anchor feed (confirmed, per the parent's
2026-11-15 anchors); rich third-party decision-board coverage exists:**

- **First-party (Nace):** public Decision Index 0.4 **67.52** (vs Drex v2.0 61.25, Jev 1.13.0
  57.96), JevBench **92.2%** (213/231), Decision Bench v4 **94.3%**, DecideBench item 98.5 /
  pair 97.0, public Vision Index 73.92 (v1) / 75.9 (v1.1), AA Decision Index **64** at
  release (https://huggingface.co/nace-ai/drex-max-v1;
  https://www.nace.ai/blog/introducing-drex-max;
  https://www.nace.ai/research/towards-foundation-decision-models, arXiv 2611.07854).
- **Artificial Analysis (independent):** Nace's page reports **v1.1 at 72.6, #1 of 18 decision
  models on AA Decision Index v2.1 as of 2026-11-12**, ahead of GLiDE v1.2 (72.5), mammoth-1
  (71.4), d1-ultra (70.6), Decider v1.2 (69.8)
  (https://www.nace.ai/drex/decision-index, updated 2026-11-12) — **but a secondary source
  read AA v2 at 73.39 against 17 models on 2026-11-08**, a different index edition; state the
  edition and date with any quote
  (https://www.orcarouter.ai/blog/drex-max-1-1-vs-drex-max, 2026-11-09).
- **modeltested (independent hands-on, updated Oct 30, 2026): #3 of 27 decision models tested**
  — 94% accuracy overall, 92% on hard cases, calibration 95, called through OpenRouter's
  Decisions API; behind Span-02 (96%), and it notes 21 regular open models scored higher on
  their suite (https://modeltested.com/decision-models/drex-max).
- **Community benchmark (r/LocalLLaMA, data through 2026-11-06, 2,826 real GitHub/Firefox/CVE
  decisions, post-2026-09-15 items to avoid leakage): Drex Max v1.1 in the statistically tied
  top tier — 65.6% balanced accuracy vs d1-ultra 66.1% and Decider v1.2 65.6% — rated "close
  runner-up" and "leading in domain-specific triage," best overall going to Perplexity
  Decider v1.2 (https://www.reddit.com/r/LocalLLaMA/comments/1xruhp3/).
- Version-delta caution: orcarouter's diff of v1.0→v1.1 (2026-11-09) says all Nace numbers are
  vendor-run and un-reproduced, the knowledge rows are mixed, and AA has no separate row for
  the original Max — so the boards cannot size the v1→v1.1 delta
  (https://www.orcarouter.ai/blog/drex-max-1-1-vs-drex-max).

**Opinions:**
- Positive but vendor-heavy. The open-weights release (2026-11-01) got trade coverage:
  MarkTechPost led with "all figures below are self-reported by Nace AI" and highlighted
  local Apple-Silicon inference (~400 ms/decision, Q8_0 within 0.02 of H100 bf16)
  (https://www.marktechpost.com/2026/11/01/nace-ai-open-sources-drex-max-v1-local-inference).
- r/LocalLLaMA release threads are detailed and engaged, including a direct comparison that
  Drex Max (AA 64) sits ~15 points above Cloudflare Clef (49) at release, Nace's claim of ~8×
  lower cost than the next-best model on the AA index, and ~256K context vs GLiDE 1.2's 64K
  (https://www.reddit.com/r/LocalLLM/comments/1xjgq9v/;
  https://www.reddit.com/r/LocalLLaMA/comments/1xl5yfs/). One commenter sniped that "the best
  model will always be on the Pareto frontier, by definition," and another voiced general
  skepticism of Artificial Analysis after its open-weight-model scoring changes
  (https://www.reddit.com/r/LocalLLaMA/comments/1xr2rqk/).
- Latency complaints in that thread drew a Nace response: "The latency you're seeing comes
  from serving load, not from the model itself. We've had a big jump in traffic, and we are
  scaling up capacity" (same thread).
- No press coverage of Nace/Drex Max beyond trade aggregators found; no negative independent
  review found.

**Known for:** Nace.AI's 27B multimodal "decision model that sees" — screenshots, documents
and video frames in, calibrated probabilities out in ~180 ms, currently #1 among decision
models on AA's Decision Index (v1.1, dated 2026-11-12).

**Caveats that change decisions:** never chat — Decisions API only; **single provider
(DeepInfra)** on OpenRouter; the `drex-max` id silently changed meaning when v1.1 replaced v1
in place (2026-10-28; original id retired Nace-side 2026-11-08) — benchmark rows and behavior
pin to whichever build was live; **conflicting context figures** (OpenRouter 262K vs Nace
product page 131,072/question vs 16,384 default in open weights) and conflicting prices
($0.06/M OpenRouter 50%-off snapshot vs $0.03/M Nace API, both 2026-11-15); RAIL-M license
(commercial use conditions, group-e: barred above $1M revenue for v1.5 — verify the exact
terms for Max), v1.1 weights not yet open; most headline scores are Nace-run; finance_trading
#1 partly reflects Nace's separate finance-tuned variant (`drex-max-finance`, 2026-11-01).

---

## stealth/crouton-alpha

**Decision: EXIT — but a *revealed* exit, not an anonymous one: write the reveal into the
note.**

**What it was.** A free stealth preview on OpenRouter: catalog entry 2026-11-03 01:38 UTC,
announced 20:17 UTC that day, **1,048,576-token context** (max completion 943,718), text /
image / video / PDF / audio in, text out, reasoning always on (default effort "max",
effort levels max/xhigh/high/medium/low/minimal), tool calling (tool_choice auto only) and
structured outputs, **$0 in / $0 out**, no listed expiration — pitched as "a lightweight model
built for scalable coding, agentic, and multimodal workflows" to run bounded sub-tasks under
a frontier planner
(https://openrouter.ai/stealth/crouton-alpha, snapshot 2026-11-15;
https://x.com/OpenRouter/status/2117712705901728199;
https://kingy.ai/blog/crouton-alpha-free-stealth-model, read 2026-11-03;
https://cellcog.ai/blog/what-is-crouton-alpha/, table read 2026-11-03 20:36 UTC). Also routed
by OpenCode (`crouton-alpha-free`, 30-day data retention) and Command Code
(https://aibriefingdaily.com/news/crouton-alpha-free-stealth-model-opencode-openrouter-30-day-retention).

**Identity — confirmed, unlike the space-bunny-era guessing stage: Meta's Muse Ember.**
Alexandr Wang (Meta's chief AI officer) posted 2026-11-10 03:46 UTC: "crouton-alpha 🥐 was an
early version of muse ember 🔥 we fixed a bunch of the issues before launch — thanks for all
the testing! **we processed over 5T tokens in testing**" (https://x.com/alexandr_wang/status/2120000217827475623);
OpenRouter reposted and its model page now reads "revealed to be an early version of Muse
Ember… The stealth period has ended; use Muse Ember at openrouter.ai/meta/muse-ember"
(snapshot 2026-11-15). The repo's **5.07T tokens over 6/30 days** corroborates Wang's ">5T".
Pre-reveal sleuthing had converged on Meta within 20 minutes (blocked-country list matching
Meta's API, a Japanese word every Muse model fails, Muse-only effort settings) — with one
clue that didn't fit (token counts), graded "likely, not settled" until the reveal
(https://cellcog.ai/blog/what-is-crouton-alpha/).

**Exit dates.** Listed 2026-11-03; Muse Ember launched **2026-11-09**; reveal **2026-11-10**;
gone from OpenRouter's catalog on a read at 23:34 UTC **2026-11-13** (CellCog, same URL), and
absent from the model list at the repo check (2026-11-15). Traffic window: 5.07T tokens over
6 of 30 days (repo check) — consistent with a Nov 3–~Nov 9 life. Successor:
**`meta/muse-ember`** at $0.10/M in, $0.50/M out, 1M ctx (Meta blog 2026-11-09:
https://research.meta.ai/blog/muse-ember; price confirmed on OpenRouter by CellCog's
2026-11-13 read).

**Benchmark standing: none — state that plainly.** No benchmark rows in the anchor feed, and
**no official score of any kind was published during the preview** — "No official scores.
Command Code shows its intelligence and coding indexes as not yet scored"
(https://kingy.ai/blog/crouton-alpha-free-stealth-model); "We found no benchmark, speed figure
or independent test in any listing we checked, so how well it codes is unknown"
(https://aibriefingdaily.com/news/crouton-alpha-free-stealth-model-opencode-openrouter-30-day-retention).
A community tracker measured ~175 tok/s in its own tests
(https://huggingface.co/stealth-model/crouton-alpha). Post-reveal Muse Ember benchmarks
(AA Intelligence Index 36 at max effort ≈ Claude Haiku 5.5's 35.8, ~$0.14/task vs $0.41;
VentureBeat, 2026-11-09:
https://venturebeat.com/technology/metas-proprietary-muse-ember-nearly-matches-claude-haiku-5-5-at-1-3-the-estimated-per-task-cost)
belong to the successor id and were not researched here, per the space-bunny precedent.

**Opinions:** thin and mostly descriptive — no capability verdicts possible. OpenRouter's
announcement drew 191.8K views (https://x.com/OpenRouter/status/2117712705901728199); the
reveal post ~107.6K views (https://x.com/alexandr_wang/status/2120000217827475623). Guides
focused on terms and unknowns: i10x (2026-11-04) recorded community clue-hunting — "Community
clues point Crouton toward Meta's Muse family, but there is no official confirmation" (pre-
reveal) (https://i10x.ai/news/crouton-alpha-pulse-alpha-stealth-models); kingy.ai listed the
unknowns (maker, size, weights, quantization "unknown", post-preview price, benchmarks,
regions) and ~93% uptime at 02:13 UTC 2026-11-04 (https://kingy.ai/blog/crouton-alpha-free-stealth-model);
AI Briefing Daily's terms analysis is the most careful (retention vs training distinctions,
rate limits, no printed end date — "free for the next week" from Nov 3 implies Nov 10, "that's
our arithmetic") (https://aibriefingdaily.com/news/crouton-alpha-free-stealth-model-opencode-openrouter-30-day-retention).

**Known for:** Meta's free anonymous week-long stealth preview (2026-11-03 – ~2026-11-09) that
absorbed over 5T testing tokens and was revealed as an early Muse Ember.

**Caveats that change decisions:** exit — not selectable; only successor `meta/muse-ember`
remains. During the preview: prompts/completions "may have been retained by the provider but
are not used for training" (OpenRouter), 30-day retention on OpenCode, no EU in-region
routing / blocked in Europe, free preview removable at any time with or without notice,
no benchmarks or parameter count ever published, ~93% uptime early on — do not project any
quality claim from the stealth id onto Muse Ember: Meta says issues were "fixed… before
launch."

---

## Policy summaries

**baseten/elephant-1-20261021** — Base Labs' 9B MIT-licensed decision model (Qwen3.5-9B
fine-tune, released 2026-10-21): typed questions in, calibrated probabilities out in one pass
via the Decisions API only — never chat. On OpenRouter it is single-provider (Baseten) at
$0.035/M input, output free, 16K context (snapshot 2026-11-15); at launch it was the best
sub-15B model on the Jev Decision Index (62.65 on edition 0.4; rescored 60.26 Full on the
0.4.1 board of 2026-10-22) and tied #1 on AA's Decision Index (65 pre-release; 64.69, 3rd of
17, checked 2026-10-23). Pick it for cheap routing/guardrail/scoring at small size; caveats
that decide: declared training overlap with Decision Index benchmark train splits (one private
test excluded by the board), deliberately abstention-heavy knowledge behavior, 16K context,
single provider, three weeks old.

**baseten/joey-1-20261029** — Base Labs' 2B MIT decision model (Qwen3.5-2B, released
2026-10-29), the family's cost/latency floor: $0.01/M input, output free on OpenRouter and
Baseten (2026-11-15), 16K context, Decisions API only, single provider (Baseten). It is
positioned as a first-line filter that escalates uncertain answers to elephant-1/mammoth-1;
its "best under 4B" standing rests on Baseten's own runs (Jev 0.4 public split 63.30; AA
replica 62.9) and its "strongest ≤3B" claim is unpublished internal testing — no independent
evaluation exists yet. Pick it only where per-call cost and ~20 ms P50 dominate; caveat that
every headline number is vendor-run and the model is three weeks old.

**nace-ai/drex-max-20261016** — Nace.AI's flagship 27B multimodal decision model (text +
screenshots in, probabilities out, ~180 ms), served on OpenRouter via the Decisions API only
from a single provider (DeepInfra) at $0.06/M input after a 50% discount with free output,
262K context (snapshot 2026-11-15; Nace's product page says 131,072/question — figures
conflict; Nace's own API is $0.03/M). The `drex-max` id now serves **v1.1**, replaced in place
on 2026-10-28, which Nace reports at #1 of 18 on AA Decision Index v2.1 (72.6, as of
2026-11-12 — an AA v2 reading of 73.39 on 2026-11-08 also circulates); independent checks
agree it is top-tier: modeltested #3/27 (94% accuracy, 2026-10-30) and a tied-top 65.6% in a
2,826-decision community benchmark (data through 2026-11-06). Pick it for screen/document-
driven agent decisions and the finance_trading tag (leader at #1/10, repo check 2026-11-15);
caveats: never chat, in-place version swap under one id, RAIL-M license (v1.1 weights not yet
open), most headline scores are Nace-run, and its finance rank partly reflects the separate
`drex-max-finance` variant.

**stealth/crouton-alpha** — Exit with a confirmed identity: a free stealth preview on
OpenRouter (listed 2026-11-03; 1,048,576 ctx; multimodal in/text out; reasoning on by default;
$0/$0), revealed by Meta's Alexandr Wang on **2026-11-10** as an early version of **Muse
Ember**, with ">5T tokens in testing" matching the repo's 5.07T over 6/30 days; gone from the
catalog by 2026-11-13 and absent at the 2026-11-15 check. No benchmark data of any kind
existed for the stealth id — it was never a capability pick, and the space-bunny precedent
applies: do not project successor scores onto it. Documented exit; the live route is
`meta/muse-ember` ($0.10/$0.50, 1M ctx, launched 2026-11-09); revisit only under the
successor id.