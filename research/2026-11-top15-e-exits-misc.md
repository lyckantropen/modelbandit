# Group E — exits, misc, just-below-cutoff (2026-11 summaries refresh)

Research pass per `research/README.md` §2, dated **2026-11-01**. Window/token and
rank facts come from the parent's `--check-policy`/`--anchors` output (2026-11-01)
and are labeled "repo check"; every web claim carries a URL. Prices and index
numbers are dated snapshots.

**Verification method and a methodological warning.** I fetched OpenRouter's
keyless chat catalog live (`https://openrouter.ai/api/v1/models`, 452 models,
2026-11-01) and fetched model/author pages directly. Two findings change how
"not in the model list" should be read:

1. **The chat catalog contains zero decision-type models and zero stealth models
   as of 2026-11-01** — no `nace-ai/*`, no `mercury-decide`, no `drex`, no
   `stealth/*`, no `span`/`kev`/`pplx`/`decide` ids at all. The demonstrably
   *live* decision model `nace-ai/drex-v2.0` (12.3B tokens/7d on OpenRouter's own
   author-page snapshot, https://openrouter.ai/nace-ai) is also absent from that
   catalog. So catalog-absence alone does **not** prove a per-model delisting for
   the two decision models in this group; I weigh the per-model evidence below
   instead of leaning on the catalog test.
2. **Author pages are stale and cannot be trusted for exits.** Live fetches on
   2026-11-01: `https://openrouter.ai/inception` still links
   `inception/mercury-decide`, `https://openrouter.ai/nace-ai` still links
   `nace-ai/drex-v1.5`, and `https://openrouter.ai/stealth` still lists
   `space-bunny-alpha` — while direct model-page fetches for those three return
   HTTP **404**, and the Stealth provider page says "Stealth has no models
   available on OpenRouter right now"
   (https://openrouter.ai/provider/stealth). Control fetches: model pages for
   `moonshotai/kimi-k3` and `recursive/flint-v1.0:free` return HTTP 200 (an
   API guide), so the 404 test is valid for **chat** models — but live
   `nace-ai/drex-v2.0` also 404s, so for **decision** models the page test is
   inconclusive (they are documented under a different page type).

---

## inception/mercury-decide-20260930

**Decision: EXIT — write a dated exit note; do not re-research.** The current
`policy.json` summary for this id is also factually wrong about what the model
is (it describes "a diffusion-based research model … 1,009 tokens/sec … 128K
context"; no source matches that description — Mercury Decide is a
non-generative decision model with a 66K context) and should be replaced outright.

**What it was.** Mercury Decide was Inception's structured-decision "System
One" endpoint: you send a `state` plus typed questions (`noul` yes/no,
`choice`, `score`, `extract`) and it returns calibrated probabilities taken
from the model rather than generated as text, so **only input tokens are billed**
— $0.02/M input at a listed 50% discount off $0.04, output free — over a
65,536-token context, released 2026-09-30, single provider (Inception), no
chat-completions/streaming/tool-calling support
(https://openrouter.ai/inception/mercury-decide, search snapshot retrieved
2026-11-01; Inception's own docs, live 2026-11-01:
https://docs.inceptionlabs.ai/capabilities/decisions; third-party snapshots:
https://decision.host/model/inception-mercury-decide/ dated 2026-10-09 and
https://infro.io/models/inception/mercury-decide pricing updated 2026-10-05).
Inception itself is a diffusion-LLM lab (Mercury chat family) that raised a
$50M seed led by Menlo Ventures with NVIDIA, Microsoft M12 and angels Andrew Ng
and Andrej Karpathy
(https://techcrunch.com/2025/11/06/inception-raises-50-million-to-build-diffusion-models-for-code-and-text/).

**Benchmark standing: none — state that plainly.** The anchor feed carries no
AA, Design Arena or OpenRouter-evals rows for this model, and I found no
independent benchmark table anywhere; decision models are not on those boards.
No capability-versus-autoregressive comparison exists in public sources as of
2026-11-01.

**When it disappeared — honest range, not a single date.** Repo check
(2026-11-01): not in the models catalog, absent from every tag and domain, 0
tokens across the whole 2026-10 window. Live: absent from the keyless catalog
(2026-11-01, with the class-wide caveat above), and the model page now 404s
(live fetch 2026-11-01) — but since live `drex-v2.0` also 404s, that page test
is inconclusive for decision models. Last positive public sightings: pricing
snapshot 2026-10-05 (https://infro.io/models/inception/mercury-decide) and the
decision.host render dated 2026-10-09. **An exact removal date cannot be pinned
from public sources**; defensible phrasing is "listed as of 2026-10-09, gone
from the chat catalog and every tag/domain by 2026-11-01, zero October traffic
per the repo window."

**Successor.** Inception's decision model remains documented and billed on
Inception's own API (`POST /v1/decisions`, model `mercury-decide`, $0.02/M —
https://docs.inceptionlabs.ai/capabilities/decisions, live 2026-11-01). On
OpenRouter the Inception family continues as chat models only —
`inception/mercury-3` (created 2026-10-16, $0.10/$0.35, 1M ctx),
`mercury-2.5`, `mercury-2` (live catalog check 2026-11-01;
https://openrouter.ai/inception/mercury-3) — and the decisions category is now
represented by routes like `typesafe/jev-router` (in the live catalog
2026-11-01) plus the Nace Drex models (see that section). Third-party note: the
AnyRouter platform made Mercury Decide BYOK-only on 2026-10-21
(https://anyrouter.dev/changelog) — ecosystem churn around that date, not
OpenRouter evidence.

**Opinions: essentially none found.** No community review, press benchmark or
leaderboard entry exists for Mercury Decide; launch coverage is limited to
vendor/adjacent write-ups summarized by decision.host
(https://decision.host/model/inception-mercury-decide/). Say "no independent
coverage" rather than guessing.

**Known for:** Inception's zero-output-cost structured-decision endpoint — typed
questions in, calibrated probabilities out, no text ever generated.

**Caveats:** exit status with the date range above; it was never chat (chat SDKs
cannot call it — Decisions API only); single provider; not available for EU
in-region routing (per the cached OpenRouter page); the repo's existing summary
misdescribes the model and must not be kept as-is.

---

## nace-ai/drex-v1.5-20261009

**Decision: EXIT-note for the chat catalog, with an ambiguity flag — do not
re-research, but the note must not claim a confirmed OpenRouter-wide delisting.**

**What it is / who makes it.** A ~9B (8.95B) non-generative decision model from
**Nace.AI**: `Qwen3_5ForCausalLM` backbone — base
`XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B` — plus a trained pointer head; one
forward pass per question returns a probability for every option you supply,
nothing is generated; TypeSafe System One compatible (`POST /v1/systemone`);
state up to 131,072 tokens; released on Nace's API 2026-09-28, listed on
OpenRouter 2026-10-09 at $0.04/M input with output free
(https://huggingface.co/nace-ai/drex-v1.5;
https://github.com/nace-ai/drex-decision-models;
https://console.nace.ai/docs/drex/reference/models;
https://openrouter.ai/nace-ai/drex-v1.5, search snapshot 2026-11-01;
https://systemonemodels.org/models/drex/).

**Benchmark standing (no AA/Design Arena/evals rows — confirmed none in the
anchor feed; decision models are not on those boards).** First-party: #1 model
under 10B on the public Decision Index 0.3.1 at 58.08, within the board's
0.9-point tie band with Jev 1.13.0 (57.96), ahead of Jev on 20 of 37 public
benchmarks; JevBench 86.2% vs Jev's 87.0%; long-context accuracy 89.5%
(8k–32k) and 93.4% (32k–128k) (https://huggingface.co/nace-ai/drex-v1.5).
Independent: #8 of 27 decision models tested — 92% accuracy, 84% hard cases,
calibration 93, measured through OpenRouter's Decisions API
(https://modeltested.com/decision-models/drex-v1-5/). Repo check (2026-11-01)
ranks it **finance_trading #1/10** — a tag outside the five policy domains, and
its listed reason for still surfacing in rankings.

**Status now — the conflict, stated rather than resolved.** Repo check
(2026-11-01): not in the models catalog, absent from all domains, 0 tokens in
the October window. Live catalog: absent — but so is every decision model,
including the definitely-live `drex-v2.0`. Meanwhile the live Nace author page
(fetched 2026-11-01) still lists `drex-max`, `drex-v1.5` and `drex-v2.0`
(https://openrouter.ai/nace-ai), and a search snapshot of the v1.5 model page
shows a DeepInfra provider row ($0.04, 100% uptime) and **13.1B tokens in the
prior 7 days** (crawl date unstated; https://openrouter.ai/nace-ai/drex-v1.5).
Direct model-page fetch 404s — inconclusive (live drex-v2.0 404s too). Honest
conclusion: **Drex v1.5 is out of OpenRouter's chat catalog and its 0-token
window argues against chat traffic, but whether OpenRouter still serves it via
the Decisions API (DeepInfra) is genuinely ambiguous from public sources.**

**Served elsewhere now — yes, with certainty:** Nace's own API at $0.05/M
(https://console.nace.ai/docs/drex/reference/models), DeepInfra at $0.04/M
(https://deepinfra.com/nace-ai/drex-v1.5), and as open weights (bf16 ~18 GB,
Q8_0 GGUF ~9.5 GB) runnable via Python, the Nace llama.cpp and Ollama forks
(https://huggingface.co/nace-ai/drex-v1.5;
https://github.com/nace-ai/drex-decision-models).

**Successors (superseded twice in three weeks):** `drex-v2.0` — 35B-A3B MoE
(~3B active), Nace release 2026-10-06, OpenRouter listing 2026-10-12, $0.06/M,
now the `drex-latest` target, 61.25 on the public Decision Index 0.3.1 in
Nace's own run (https://modelsystem.one/news/drex-v2-0/); `drex-max` —
2026-10-13, image-capable, $0.03/M on Nace's API
(https://console.nace.ai/docs/drex/reference/models); `drex-max-v1.1` —
2026-10-28, Nace API only (same page). On OpenRouter the author page shows all
three carrying traffic (Max 16.6B, v2.0 12.3B, v1.5 13.1B tokens/7d —
search snapshot 2026-11-01, crawl date unstated).

**Opinions:** narrow but real — the modeltested review (above) is the only
independent hands-on test I found; ecosystem comparison lives on the Decision
Index/JevBench boards cited in its model card
(https://huggingface.co/nace-ai/drex-v1.5). No press coverage found.

**Known for:** Nace.AI's small open-weights decision model — calibrated
probabilities over your own options in a single forward pass, #1 under 10B on
the public Decision Index at launch.

**Caveats:** never chat (Decisions API only — chat SDKs will not work);
license is **Nace.AI Open RAIL-M**: free including commercial use under $1M
annual revenue/funding, above that personal and research use only, competitor
use barred (https://systemonemodels.org/models/drex/) — the repo's prior
"MIT → RAIL-M relicensing" claim was **not** independently verifiable here;
superseded by v2.0 and Max within weeks; catalog absence is class-wide for
decision models and should not be written up as a unique delisting event.

---

## stealth/space-bunny-alpha

**Decision: EXIT — dated exit note (policy already excludes it; the summary's
identity claim must be corrected).**

**What it was.** A free stealth preview on OpenRouter: anonymous "large model
with blazing-fast inference, strong coding capabilities and native multimodal
input" (text/image/video in), 1,000,000-token context, mandatory reasoning,
listed `expiration_date` 2026-10-05, created 2026-09-23 14:48 UTC
(https://openrouter.ai/stealth/space-bunny-alpha, search snapshot 2026-11-01;
parameter table: https://codersera.com/blog/space-bunny-alpha-stealth-model-2026/;
original listing render: https://vuink.com/post/bcraebhgre-d-dnv/stealth/space-bunny-alpha
dated 2026-09-23).

**Identity — now confirmed, superseding the repo's current summary.** MiniMax
launched **M3.1 Flash on 2026-10-19 and confirmed Space Bunny was an early
version** of it (TokenPost, 2026-10-19:
https://www.tokenpost.com/news/technology/34757), and OpenRouter's model page
text now reads "revealed to be MiniMax M3.1 Flash by MiniMax … The free stealth
period has ended; use MiniMax M3.1 Flash at
https://openrouter.ai/minimax/minimax-m3.1-flash"
(search snapshot 2026-11-01). The pre-reveal sleuthing had already converged on
`MiniMax-M3.1-Flash-Preview` at ~85% confidence
(https://codersera.com/blog/space-bunny-alpha-stealth-model-2026/).
**`policy.json` currently says "identity contested (a GPT-core fusion router
per the best sleuthing, unconfirmed)" — that is now wrong and should be
replaced with the confirmed MiniMax attribution.**

**Exit dates.** Appeared 2026-09-23; listed expiry **2026-10-05**, and an
independent guide states the id "was withdrawn on October 5, 2026 and requests
to it will fail" (https://www.spacebunny.dev/guides/space-bunny-api). Repo
check (2026-11-01): **not in the model list, absent from all tags/domains, only
4 of 30 days with traffic in the 2026-10 window** — exactly consistent with an
end between Oct 1 and Oct 5 — cumulative **22.84T tokens** (note: the existing
policy summary says "28T tokens in 5 days" from the prior cycle; the two
figures come from different windows and should be reconciled to the repo's
current 22.84T catalog figure). Live check 2026-11-01: **no `stealth/*` ids
remain in the chat catalog at all**, and the model page 404s (valid test for
chat models — control pages return 200).

**Successor:** `minimax/minimax-m3.1-flash`, in the live catalog, created
2026-10-19, $0.15/$0.60 per 1M (catalog check 2026-11-01; price row:
https://openroutermodeltable.crashthatch.com/). The wider Stealth program also
looks wound down: OpenRouter's provider page reports "Stealth has no models
available on OpenRouter right now" (https://openrouter.ai/provider/stealth),
though its author page still stale-lists three ids.

**Benchmark standing: none — no AA, Design Arena or OpenRouter-evals rows
exist for the stealth id (anchor feed: no benchmark rows; confirmed — a stealth
preview is unlisted on those boards by construction).** Post-reveal M3.1 Flash
benchmarks belong to the successor id and were not researched here.

**Opinions / community:** Space Bunny topped OpenCode's daily token-usage
ranking by 2026-09-24, one day after appearing (TokenPost,
https://www.tokenpost.com/news/technology/34757); testers documented a
capability jump around 2026-09-29 and a regression around 2026-10-01 with no
provider statement — possibly multiple checkpoints under one name, so any
"benchmark" read of it is pinned to an unstated date
(https://codersera.com/blog/space-bunny-alpha-stealth-model-2026/).

**Known for:** the free 1M-context stealth preview (2026-09-23 – 2026-10-05)
later revealed as MiniMax M3.1 Flash.

**Caveats:** stealth terms — prompts/completions "may have been retained by
the provider but are not used for training" (cached OpenRouter page); free
preview ended without warning; identity attribution is MiniMax's own
confirmation, not an OpenRouter statement at listing time; do not confuse with
OpenCode Zen's separate `space-bunny-free` id
(https://www.spacebunny.dev/guides/space-bunny-api).

---

## recursive/flint-v1.0:free

**Decision: NOT AN EXIT — OpenRouter still lists it. Keep and refresh; no exit
note.** The brief's "dead/never-used free route" hypothesis fails
verification.

**Verified live (2026-11-01):** present in the keyless catalog — id
`recursive/flint-v1.0:free`, created 2026-10-21 22:46 UTC, 262,144-token
context, $0/$0 (live `https://openrouter.ai/api/v1/models`); model-page guide
returns HTTP 200 (https://openrouter.ai/recursive/flint-v1.0:free); the author
page lists it with a serving guide (https://openrouter.ai/recursive, live
200); it sits in OpenRouter's free-models collection showing **142B tokens in
the last 7 days** (search snapshot 2026-11-01;
https://openrouter.ai/collections/free-models); new-model event logged
2026-10-21 (https://modelcanary.com/event/1075).

**Conflict to record, not smooth over:** the repo check (2026-11-01) reports
**0 tokens / 0 of 30 days** for this id, while OpenRouter's own pages show
142B tokens/7d. The model was created 2026-10-21, late in the window, so this
is most plausibly window-source lag or a free-route accounting difference — but
the two figures disagree and the summary should carry the live 142B/7d figure
with its snapshot date, not the zero.

**What it is:** an open-weight mixture-of-experts from **Recursive** — ~40B
total parameters, ~2.5B active — "built by Recursive's autoresearch system
Eureka Machine for coding agents," suited to investigating codebases, fixing
bugs, implementing features and writing tests; served by a single provider
(Recursive, BF16), tools + reasoning supported, structured-output JSON-schema
flag off (https://openrouter.ai/recursive/flint-v1.0:free, search snapshot
2026-11-01; https://www.typingmind.com/guide/openrouter/flint-v1.0-free;
https://openroutermodeltable.crashthatch.com/).

**Benchmark standing: none.** The anchor feed carries no AA/Design
Arena/evals rows for it (stated in the brief), and I found no independent
evaluation — treat it as unbenchmarked.

**Opinions:** cost review (tokencost.app, 2026-10-23) is the main independent
write-up: free tier is capped at 20 requests/min and 50/day (1,000/day only
after $10 of credits) — "one or two real tasks" for a coding agent — the paid
`recursive/flint-v1.0` id existed but had **zero providers** when checked, and
it advises reading the endpoint's data policy before pointing a free tier at
proprietary code (https://tokencost.app/blog/recursive-flint-local-vs-api-cost).

**Known for:** a free, single-provider open-weight coding-agent model from an
autoresearch lab's Eureka Machine — Recursive's only OpenRouter route.

**Caveats that change decisions:** single provider with **10.04% uptime** in
the provider table (search snapshot 2026-11-01, crawl date unstated — re-verify
before quoting); free routes default to `trains` exposure in this repo's catalog
(existing policy entry: "collected data may be used to improve the model");
free ends without warning; rate limits are the real usage ceiling; zero
benchmark coverage.

---

## moonshotai/kimi-k3

**Decision: RE-RESEARCH / keep — this is not a declining classic to retire, and
it is not simply below the cutoff either: it is one of the busiest models in
the catalog with a genuinely contested successor story.**

**Status (verified 2026-11-01).** In the live catalog: created 2026-07-16,
context 1,048,576, baseline list price **$0.192 in / $15.00 out** (cache read
$0.182) — matches the brief's $0.19/$15.00; a `kimi-k3:batch` route also
exists. OpenRouter's page shows **20 providers** with a weighted average of
**$0.1495 / $7.15** (cheapest: Sail Research; dearest listed: $3.00/$15.00,
Fireworks Fast $4.50/$22.50) (https://openrouter.ai/moonshotai/kimi-k3, search
snapshot 2026-11-01). Repo check: **10.85T tokens, 2026-10-02..2026-10-31,
30/30 days**, created 2026-07-16 — absent from all 29 tags and all 5 domains
only at top-15 depth, i.e. heavy traffic below the ranking cutoff, not gone.

**Benchmark standing — anchors verified, with an important reading note.**
OpenRouter's benchmark panel (search snapshot 2026-11-01) confirms the anchor
rows exactly, and reveals they are the **"Low" effort setting**: Artificial
Analysis **Kimi K3 (Low)** Intelligence 17.4, Coding 72.0, Agentic 29.3 (anchor
$0.15/$22.00 matches the Wafer Fast provider row $0.149/$22, not the list
baseline); at **(Max)** effort AA reports Coding 76.2, Agentic 50.0, GPQA
Diamond 93.5%, HLE 46.9% — so the anchor's 17.4 intelligence is a low-effort
floor, not the model's ceiling. Design Arena Models Arena **1305–1381**
confirmed (SVG 1305 → 3D 1381), plus Agents-Arena rows 1116–1327. The anchor's
OpenRouter-evals rows (gpqa_diamond 91.9%, tau_bench airline 73.6% at
$0.2858/task) could not be re-verified from static page text (JS-rendered) —
report them as feed-provided, dated 2026-11-01T12:00Z. Vals AI rows on the
same page: GPQA Diamond 92.9%, SWE-bench 93.4%, LiveCodeBench 87.2%, Vals
Index 53.0%. Context anchor: family `kimi-k3.1-pro-20261023` AA intelligence
46.0 and Design Arena 1283–1441 — note the anchor's **$4.00/$20.00 price for
K3.1 Pro conflicts with the live catalog's $2.00/$10.00** (checked 2026-11-01)
and with multi-AI snapshots of $2/$10 dated 2026-10-24/25
(https://multiai.co/blog/kimi-k3-vs-k3-1-pro); date whichever number is used.

**Opinions (successor debate is the whole story):**
- BenchLeader, as of 2026-11-01: K3 and K3.1 Pro "neck and neck on quality"
  (BenchLeader Index 62.2 vs 61.5, inside margin) — pick **K3 for coding
  (64 vs 60), long context (69 vs 68) and first-answer speed (36.6s vs 68.0s)**,
  Pro for maths, agents and multimodal
  (https://www.benchleader.com/compare/kimi-k3-vs-kimi-k3-1-pro).
- Bito's real agent sessions (2026-10-24): a tie at 72% overall, with K3.1 Pro
  writing 2× the tokens for 68% longer and costing 74% more per long session
  ($4.28 vs $2.46) — "more thinking, same score"
  (https://bito.ai/blog/kimi-k3-1-pro-vs-kimi-k3/).
- MultiAI (2026-10-25): every broad index favors Pro (AA 44→55, LiveBench
  63.4→76.7, Terminal-Bench 4.0 12.6%→67.2%), but "anything that needs open
  weights today" stays on K3 — K3.1 Pro weights were promised by 2026-11-04
  (https://multiai.co/blog/kimi-k3-vs-k3-1-pro;
  Moonshot announcement: https://www.kimi.ai/blog/kimi-k3-1-pro).
- Superconductor (2026-08-03): best open-weight model on their custom
  SWE-Bench (~80% quality, same band as Opus 4.8 at ~¼ cost) **and the slowest
  agent they ran (~44 min/ticket)** (https://www.superconductor.com/blog/kimi-k3-benchmark).
- neurohive review: 4th of 580 on AA's then-current Intelligence Index, first
  open model atop WebDev Arena (1,678 Elo); research-level reasoning the named
  weakness (https://neurohive.io/en/state-of-the-art/kimi-k3-review/).
- Press: Financial Post — Moonshot's claim that K3 beats GPT-5.5 and Opus 4.8
  on coding/agentic benchmarks while lagging OpenAI/Anthropic flagships overall
  (https://financialpost.com/technology/what-know-chinese-ai-model-kimi-k3/).
- Hallucination caveat: AA-Omniscience reporting shows K3 guesses more often
  than K2.6 (39%→51% in one AA-dated snapshot cited by insidepc,
  2026-07-17: https://insidepc.tech/ai/ai-reviews/kimi-k3-review); MultiAI
  records a 53% "guesses when it doesn't know" rate
  (https://multiai.co/blog/kimi-k3-vs-k3-1-pro).

**Known for:** Moonshot's 2.8T-parameter open-weight multimodal flagship
(July 2026) — long-horizon agentic coding, repo navigation and 1M-context
knowledge work at a fraction of frontier prices.

**Caveats that change decisions:** successor K3.1 Pro (2026-10-23) wins most
broad indexes and is *cheaper per token* ($2/$10 live) but slower and more
verbose (per-session cost can be higher — Bito, MultiAI); K3's open-weights
advantage expires once K3.1 weights land (promised 2026-11-04); the headline AA
row is the Low-effort setting; enormous provider spread (20 hosts, $0.1495–$4.50
input, uptime 67%–100% on listed endpoints — Fireworks Spot 80.17%, Chutes
94.92%); always-thinks reasoning burns tokens even on trivial asks; price
snapshots disagree ($0.192/$15 list baseline vs $0.1495/$7.15 page average vs
$3/$15 Moonshot direct, https://evolink.ai/blog/kimi-k3-1-pro-vs-kimi-k3
checked 2026-10-24).

---

## qwen/qwen3.8-flash

**Decision: RE-RESEARCH / keep — busy (2.51T tokens, 29/30 days) and cheap;
absent from tags/domains is a top-15-cutoff fact, not a decline signal.**

**Status (verified 2026-11-01).** In the live catalog: created 2026-08-26,
**context 1,000,000** (the repo check's 977K figure disagrees — record both,
the live API value is authoritative for today), **$0.15 in / $0.47 out**,
cache read $0.016/M, text+image+video in. Repo check: 2.51T tokens, 29/30
days, absent from all tags/domains at top-15 depth.
(https://openrouter.ai/qwen/qwen3.8-flash, live page 200, 2026-11-01.)

**Benchmark standing.** Anchor rows: OpenRouter evals **gpqa_diamond 88.6%,
tau_bench airline 71.3%** — feed-provided (2026-11-01T12:00Z), not
re-verifiable from static page text (JS-rendered benchmarks). **No AA row —
corroborated independently:** Known Good, generated 2026-11-01, states "None of
the seven index evaluations have published a score for this model yet"
(https://theknowngood.com/models/qwen-qwen3-8-flash/). First-party Qwen numbers
(open-weight sibling **Qwen3.8-Flash-Next**, 125B total/6B active + 51B n-gram
embeddings, 2026-08-26): GPQA Diamond 91.7, SWE-bench Pro 62.5 (vs Opus 4.6
Max 53.4), DeepSWE 1.1 58.7, SWE-bench Multilingual 81.0, LiveCodeBench v6
91.9, CoWorkBench 73.9, Toolathlon 73.5, AndroidWorld 84.5, MathVision 95.7
(https://huggingface.co/Qwen/Qwen3.8-Flash-Next;
https://docs.qwencloud.com/developer-guides/getting-started/latest-model).
Independent: CrucibleMark total 78.23 (Silver, rank #13 of their field) with
tool execution 90 but synthesis only 62.5
(https://www.cruciblemark.com/reports/qwen3-8-flash/).

**Opinions:**
- Ben Bishop's four-flash shootout (2026-09-12): 4.68/5 average, **19/19
  completed with no errors, lowest recorded cost ($0.0337) and the best
  quality-per-dollar of the four**, though GLM-5.3-Flash scored slightly
  higher and faster (https://bshp.io/articles/flash-tier-shootout-benchmark/).
- 24-task head-to-head vs GLM-5.3-Flash (2026-08-26/27): quality tie; Qwen
  cheaper on prose (~½ the output tokens) but ~4× costlier per code task; the
  real day-one story was **429 rate-limit storms — 41 retries, code suite
  unreachable ~50 minutes — cleared within 24h** (shared OpenRouter pool)
  (https://dev.to/li_wujie_0995d9c1bca1f2e3/i-tested-glm-53-flash-and-qwen38-flash-on-24-real-tasks-49pe;
  https://jiebuilds.hashnode.dev/what-flash-ai-models-actually-cost-when-you-run-them-glm-5-3-flash-vs-qwen3-8-flash).
- CrucibleMark tool-calling verdict: "conditional deploy" — strong tool
  selection, but invalid tool calls and weak synthesis of results
  (https://www.cruciblemark.com/reports/qwen3-8-flash/tool-calling/).
- Vendor-claim audit (Laura Martel, 2026-08-26): Flash-Next tops 20 of 22
  published rows, with the losses on HLE (35.9 vs Opus 4.6's 40.0) and
  NL2Repo-Bench (48.1 vs DeepSeek V4 Flash's 54.2), and two of the wins sit on
  Qwen's own in-house benches (https://www.laura-martel.com/blog/qwen38-flash-next-architecture).
- Caveat round-up: benchmarks are vendor-reported, some in-house, hosted vs
  open-weight builds can differ (https://www.cometapi.com/what-is-qwen3-8-flash/).

**Known for:** Alibaba's cheap multimodal 125B/6B-active MoE — an explicit
early preview of the Qwen4 architecture with 1M context and strong agentic
coding/vision at flash-tier prices.

**Caveats that change decisions:** the production `qwen3.8-flash` and open
`Qwen3.8-Flash-Next` are not identical builds (post-training differences
undisclosed; https://www.cruciblemark.com/reports/qwen3-8-flash/ flags
Chinese-jurisdiction routing as MEDIUM sovereign risk); no third-party index
scores yet (no AA row as of 2026-11-01); launch-day rate limits were real but
transient; context figure discrepancy (977K repo row vs 1M live); price is a
2026-11-01 snapshot ($0.15/$0.47).

---

## tencent/hy3

**Decision: RE-RESEARCH / keep — sits just outside the cutoff (research
#17/25, coding #17/26, ops #19/24 — repo check, 2026-11-01) with 11.96T tokens
over 30/30 days.**

**Status (verified 2026-11-01).** In the live catalog: created 2026-07-06,
context 262,144, base price **$0.0825 in / $0.33 out with a peak override of
$0.132 / $0.528 for UTC 00:00–16:00** (the catalog carries day-part pricing —
check which window a quoted price came from). OpenRouter's page header shows
$0.0825/$0.33; other dated snapshots: page weighted average $0.14/$0.58
(search snapshot 2026-11-01), Tencent's global-availability press release
"starting at US$0.1288 in / US$0.5336 out" (2026-08-05,
https://www.tencent.com/tencent-hy3-now-available-globally-extending-practical-ai-across-products-workflows-and-cloud-services/),
launch-day community report $0.14/$0.58 (2026-07-06,
https://www.reddit.com/r/AIToolsPerformance/comments/1up628e/tencent_hy3_launched_at_058m_output_tokens_is_it/).
Repo check: 11.96T tokens, 30/30 days.

**Benchmark standing.**
- Anchor `tencent/hy3-preview-20260421`: AA coding 58.8, agentic 24.1,
  $0.18/$0.60 — **preview-era numbers**; the preview route now shows $0.063/$0.21
  at 65% off (search snapshot 2026-11-01,
  https://openrouter.ai/tencent/hy3-preview/benchmarks). The GA model's own AA
  row did not appear in my sources — do not carry preview AA numbers over to
  `tencent/hy3` as if they were its own.
- Anchor Design Arena (hy3-20260706): **1125–1180, 36–44% win** — confirmed on
  the live model page: Data Visualization 1125 (36.1%), Game Dev 1134, UI
  Component 1158, Code Categories 1175, 3D 1173 (44.0%), Website 1180 (41.3%)
  (https://openrouter.ai/tencent/hy3, search snapshot 2026-11-01; anchor's
  Design Arena price row $0.15/$0.64).
- First-party (Hugging Face model card, eval-result boards): **GPQA Diamond
  90.4, SWE-bench Verified 78.0, Terminal-Bench 2.1 71.7, SWE-bench Pro 57.9,
  SWE-bench Multilingual 75.8, DeepSWE 28, Apex-Agents 25.6, SkillsBench 55.3**
  (https://huggingface.co/tencent/Hy3).
- Independent aggregation (BenchmarkList, 45 benchmarks): Tau2-Bench Telecom
  92.7 (rank 42/337), BrowseComp 84.2 (26/69), HLE 33.5, AA-LCR 79.0, GPQA
  Diamond 89.7 (49/478), WebDev Arena 1511 (33/105) — and in its head-to-head
  panel Hy3 ranks **#8 of 8, −29.0 overall vs Kimi K3**, with its only category
  advantage being price ($0.66 vs $18)
  (https://benchmarklist.com/models/tencent-hy3/).

**Opinions:**
- Tencent's own launch claims (2026-08-05): 68× the prior generation's API
  calls and **#1 on OpenRouter's global LLM usage leaderboard within a week of
  launch**; blind evaluation by 270 domain experts 2.67/4, ahead of GLM-5.1's
  2.51, strongest in frontend, data/storage and CI/CD
  (https://www.tencent.com/tencent-hy3-now-available-globally-extending-practical-ai-across-products-workflows-and-cloud-services/;
  https://huggingface.co/tencent/Hy3).
- Independent release analysis (NYU Shanghai RITS, 2026-07-06): mid-pack
  against the frontier — trails Opus 4.8/GPT 5.5, competitive with or ahead of
  GLM 5.2, DeepSeek V4 Pro and Qwen3.7 Max on several rows; reliability gains
  (hallucination 12.5%→5.4%, multi-turn issue rate 17.4%→7.9%); aggressive
  pricing (~$0.18/$0.59); still trails on competition math (MathArena Apex
  38.7) (https://rits.shanghai.nyu.edu/ai/tencent-releases-hy3-295b-open-moe-model-under-apache-2-0/).
- Hacker News is mixed: one user finds it "stays on track much more reliably
  than DS4 Flash" with less long-context degradation and calls it "very
  competitive"; another says it "makes idiotic decisions all the time" versus a
  Gemma 31B; a third calls it near Sonnet 5 for their uses and "exceedingly
  cheap" (https://news.ycombinator.com/item?id=48847552). Note in that thread:
  effective input price via OpenRouter was said to match DeepSeek Flash V4's.
- Reddit: enthusiasm at launch — "Tencent REALLY cooked" (r/opencodeCLI,
  2026-07-27, https://www.reddit.com/r/opencodeCLI/comments/1v7uhb4/) with a
  counter-note that it "ignores tools and skills much more than DS flash";
  "performing straight up like a flagship paid model" (r/hermesagent,
  2026-07-22, https://www.reddit.com/r/hermesagent/comments/1v3r6p1/).
- Usage texture: Hy3 Preview's traffic did **not** fall after its free period
  ended, with Hermes Agent alone driving ~65% of usage over three weeks
  (HN comment, 2026, https://news.ycombinator.com/item?id=48332272).

**Known for:** Tencent's aggressively priced 295B/21B-open MoE (Apache 2.0,
released 2026-07-06) — dependable tool-calling and agentic coding at flash-tier
prices, briefly #1 by usage on OpenRouter the week it launched.

**Caveats that change decisions:** a newer generation is already on the router —
`tencent/hy4-preview` (created 2026-08-28, 1,048,576 ctx, $0.7506/$2.2509
off-peak, peak $0.834/$2.501 — live catalog 2026-11-01) — so Hy3 is
price/performance play, not frontier; day-part pricing means the cheap
$0.0825/$0.33 only applies 16:00–24:00 UTC; intelligence sits mid-pack
(BenchmarkList head-to-head #8/8, Design Arena 36–44% win); several headline
scores are Tencent-internal benchmarks; community reports split on reliability;
the launch `tencent/hy3:free` promo is long over
(https://news.ycombinator.com/item?id=48815521).

---

## Policy summaries

**inception/mercury-decide-20260930** — Exit note: Inception's non-generative
structured-decision endpoint (typed questions → calibrated probabilities, 66K
ctx, $0.02/M input, output free, released 2026-09-30), listed on OpenRouter as
of 2026-10-09 but gone from the models catalog, all tags/domains and its model
page by 2026-11-01, with zero traffic across October 2026; exact removal date
unpinnable, and absence from the chat catalog is class-wide for decision models.
No benchmark rows exist — never treat it as a capability pick. Still documented
on Inception's own API; OpenRouter's Inception family continues as Mercury 3 /
2.5 / 2 chat models. Replace the existing summary — it misdescribes the model.

**nace-ai/drex-v1.5-20261009** — Exit/exclusion note: a ~9B open-weights
decision model from Nace.AI (MiMo-V2.6-Distill-Qwen-9B + pointer head) that
returns probabilities over your options in one forward pass via the Decisions
API, #1 under 10B on the public Decision Index 0.3.1 at launch (58.08), which
is why it still tops the finance_trading tag. Absent from the chat catalog and
its October window is zero as of 2026-11-01, but that absence is class-wide for
decision models and OpenRouter's live Nace author page still lists it — whether
OpenRouter still serves it (DeepInfra) is genuinely ambiguous; it is certainly
served on Nace's own API ($0.05/M), DeepInfra ($0.04/M) and as open weights.
Superseded by Drex v2.0 (2026-10-06/12) and Drex Max (2026-10-13); license
Nace.AI Open RAIL-M (commercial use barred above $1M revenue).

**stealth/space-bunny-alpha** — Exit note: free stealth preview, 1M ctx,
text+image+video, that appeared 2026-09-23, topped OpenCode's daily usage
ranking by 2026-09-24, was withdrawn at its listed expiry **2026-10-05**
(4 of 30 October days with traffic; 22.84T tokens cumulative), and was
**confirmed by MiniMax as an early version of MiniMax M3.1 Flash** at that
model's launch on 2026-10-19 — superseding the old "identity contested" note.
Not selectable: no stealth ids remain in the catalog (checked 2026-11-01);
successor is `minimax/minimax-m3.1-flash` ($0.15/$0.60, 2026-10-19). Revisit
only if a stealth id returns named and priced.

**recursive/flint-v1.0:free** — Not an exit: OpenRouter still lists this free
route (created 2026-10-21, 262K ctx, $0/$0; verified in the live catalog
2026-11-01) and its pages show 142B tokens in the last 7 days, so the repo's
0-token window is stale — refresh rather than retire. What it is: Recursive's
open-weight ~40B/2.5B-active coding-agent MoE built by its Eureka Machine,
single provider, unbenchmarked. Caveats that decide: provider uptime was 10.04%
in the latest snapshot (re-verify), free routes default to `trains` exposure,
rate limits (50 req/day, 1,000 with $10 credits) are the real ceiling, and free
ends without warning.

**moonshotai/kimi-k3** — Keep and re-research: Moonshot's 2.8T open-weight
multimodal flagship (2026-07-16; 1M ctx; list $0.192/$15, page average
$0.1495/$7.15 across 20 providers as of 2026-11-01) with 10.85T tokens over
30/30 days in October — busy below the top-15 cutoff, not declining. Benchmarks
verified but note the anchor AA row (intelligence 17.4 / coding 72.0 / agentic
29.3) is the **Low** effort setting; at Max effort AA reports coding 76.2 and
agentic 50.0, Design Arena sits 1305–1381, evals gpqa 91.9% / tau airline
73.6% (feed, 2026-11-01). Pick it for cheap long-context agentic coding and
open weights today; caveat the successor split — K3.1 Pro (2026-10-23, live
$2/$10, not the anchor's $4/$20) wins most broad indexes but is slower and
pricier per long session (Bito tie at 72%), and K3's open-weights edge ends
when K3.1 weights land (promised 2026-11-04); also higher guess-rates than K2.6
and heavy provider quality/uptime spread.

**qwen/qwen3.8-flash** — Keep and re-research: Alibaba's cheap multimodal
125B/6B-active MoE (an explicit Qwen4 architecture preview; 2026-08-26), 1M
context (live; the repo's 977K row disagrees), $0.15/$0.47 as of 2026-11-01,
with 2.51T tokens over 29/30 days — below top-15 everywhere, not receding.
Benchmarks: OpenRouter evals gpqa_diamond 88.6% / tau airline 71.3% (feed
2026-11-01), **no AA row — confirmed, no third-party index scores it yet**;
vendor numbers are strong (GPQA 91.7, SWE-bench Pro 62.5) but partly in-house.
Pick it for high-volume multimodal/agentic work at flash prices; caveats: launch
429 storms (transient), invalid tool calls + weak synthesis in independent
testing, production build ≠ open Flash-Next, China-jurisdiction routing.

**tencent/hy3** — Keep and re-research: Tencent's aggressively priced 295B/21B
open MoE (2026-07-06; 256K; $0.0825/$0.33 off-peak with a pricier UTC 0–16
peak rate $0.132/$0.528 — live catalog 2026-11-01), 11.96T tokens over 30/30
days, ranking just outside the cutoff (research #17, coding #17, ops #19).
Benchmarks: first-party GPQA 90.4 / SWE-bench Verified 78.0 / TB2.1 71.7,
Design Arena 1125–1180 (36–44% win), head-to-head #8/8 at −29 vs Kimi K3 —
mid-pack intelligence at bottom-tier price; the AA rows belong to hy3-preview,
not GA. Pick it for cheap, dependable tool-calling and agentic coding where
price dominates; caveats: `tencent/hy4-preview` (2026-08-28) already supersedes
it generationally, day-part pricing, split community reliability reports, and
several headline scores are Tencent-internal.