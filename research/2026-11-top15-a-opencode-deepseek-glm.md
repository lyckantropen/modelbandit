# research/2026-11-top15-a — opencode/deepseek-v4.1-flash-free, opencode/glm-5.3-flash-free — 2026-11-01

**Scope.** Gap-model research for the 2026-11 summaries refresh: two harness-hosted
OpenCode free routes that rank in the policy's task domains but have no `summaries`
entry. Sources pulled 2026-11-01: this repo's own tooling (`--check-policy --top 15
--scope` and `--anchors`, combined benchmarks feed `as_of` 2026-11-01T12:00:16.750Z),
OpenCode's V2 docs and Console pages, Artificial Analysis model pages, DeepSeek's and
Z.ai's release pages, OpenCode's official X announcements, GitHub issues, and
third-party reviews — all cited inline. Prices and index numbers are dated snapshots.

**Rank provenance (fact stated up front).** The domain ranks in the brief were
re-verified today with `modelbandit.py --check-policy --top 15 --scope`:
`opencode/deepseek-v4.1-flash-free` — research #3/25, writing #3/26, coding #2/26,
orchestration #4/26, ops #2/24; `opencode/glm-5.3-flash-free` — research #11/25,
writing #11/26, coding #6/26, orchestration #3/26, ops #5/24. These boards are built
on OpenRouter's task-classification feed, but an `opencode/*` id has **no leaderboard
row of its own**: `_family_share` in `skills/modelbandit/scripts/modelbandit.py`
states "its popularity is the family's revealed preference. It inherits only
[0.5] of that share", and the same scope output shows the catalog window
2026-10-02..2026-10-31 at **0.00T tokens, 0/30 days** for both ids. The ranks are
inherited family standing, not measured traffic on the free lanes.

**Anchor verification (brief vs. the same feed, 2026-11-01T12:00:16Z).**
- **Confirmed exactly:** `deepseek/deepseek-v4-pro-20260813` AA intelligence 23.1,
  coding 68.8, agentic 41.3, $0.11/$4.00; `deepseek/deepseek-v4-pro-20260423` coding
  59.4, agentic 26.3, $1.74/$3.48; OpenRouter evals gpqa_diamond 90.3% / tau airline
  77.5% and 87.1% / 76.8% respectively. Extended: cost-per-task $0.1060/$0.1010
  (0813) and $0.0421/$0.0541 (0423); Design Arena rows exist only for `-20260423`
  (best: 3d Elo 1251, 56.8% win rate), none for `-20260813`.
- **Confirmed:** "no benchmark rows" for both `opencode/*` ids — the anchors run
  closes with `no benchmark rows: opencode/deepseek-v4.1-flash-free,
  opencode/glm-5.3-flash-free`. There is no first-party benchmark data on the free
  lanes themselves; everything below is family context.
- **Contradicted — report, do not overwrite:** the brief's "no benchmark rows for
  glm-5.3 family in this feed" does not reproduce. The same feed (identical
  `as_of` timestamp) returns AA rows for `z-ai/glm-5.3-flash-20260826`
  (intelligence 27.8, coding 71.5, agentic 50.9, $0.10/$0.50) and
  `z-ai/glm-5.3-20260816` (31.7 / 74.8 / 53.1, $0.98/$3.08), plus OpenRouter eval and
  Design Arena rows (details in the GLM section). The claim as phrased is false for
  this feed; it may have come from an id set that did not resolve.
- **Index rescale between snapshots:** AA's page now runs **Intelligence Index v5.0**
  (https://artificialanalysis.ai/methodology/intelligence-benchmarking). The 2026-10-17
  research captured GLM-5.3-Flash at 42 on v4.3.2
  (https://artificialanalysis.ai/models/glm-5-3-flash); today that page reads **28**
  and the feed 27.8. Not a data conflict — a rescale. Never compare AA numbers across
  the two dates.
- **DeepSeek v4.1-flash family has no AA rows in this feed** (only v4-pro does), and
  AA's own page now marks DeepSeek V4.1 Flash (0910) **deprecated** with the
  intelligence index showing **N/A** under v5.0 — "We only continue performance
  benchmarking for the default 10k input token workload… We suggest considering
  DeepSeek V4.1 Flash 1017 instead"
  (https://artificialanalysis.ai/models/deepseek-v4-1-flash).

---

## opencode/deepseek-v4.1-flash-free

### What it is — the route and its underlying model

- **A free route served by the OpenCode harness**, not an OpenRouter slug. OpenCode
  (the OSS coding agent) runs its own model gateway — called **Console** in the
  current V2 docs, historically **Zen** — whose catalog carries `opencode/<id>`
  models; this route's console id is `deepseek-v4.1-flash-free`, served at
  `https://opencode.ai/inference/openai/v1/chat/completions`, priced **Free / Free /
  Free** for input/output/cached read (https://opencode.ai/v2/docs/console/models,
  fetched 2026-11-01). The local OpenCode catalog on this machine (checked today via
  the models tool) lists `opencode/deepseek-v4.1-flash-free`, display name
  "DeepSeek V4.1 Flash Free", $0.00/$0.00, reasoning variants `low`/`high`/`max`,
  released-date 2026-09-10 (the underlying model's release date).
- **Underlying model: DeepSeek-V4.1-Flash** (DeepSeek, released 2026-09-10): 552B
  sparse MoE on the new Causal Encoder–Decoder architecture, **8B active on input /
  16B on output**, native visual understanding, 1M context, **MIT**
  (https://api-docs.deepseek.com/news/news260910;
  https://artificialanalysis.ai/models/deepseek-v4-1-flash;
  weights https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash). DeepSeek's own
  release note names the harness as a launch partner: "Official partners WorkBuddy
  (including CodeBuddy) & **OpenCode** now fully support V4.1-Flash"
  (https://api-docs.deepseek.com/news/news260910).
- **Checkpoint:** the route went free on **2026-10-15** (OpenCode on X:
  https://x.com/opencode/status/2110635747648909472) and was **updated to the 1017
  checkpoint in Go and Free on 2026-10-19** ("DeepSeek V4.1 Flash updated to 1017 in
  OpenCode Go and Free — No changes needed on your end",
  https://x.com/opencode/status/2112220734768779441). So the free lane currently
  serves the V4.1-Flash-1017 weights (DeepSeek's 2026-10-17 minor update,
  https://api-docs.deepseek.com/news/news261017), though OpenCode documents no
  checkpoint pin — treat the mapping as announced-not-contracted.
- **Free tier mechanics:** "Free" on OpenCode means an `opencode`/`opencode-go`
  model with no input price; it can be hidden with `OPENCODE_DISABLE_FREE_MODELS=1`
  (https://opencode.ai/v2/docs/models/). Every free offer is worded "for a limited
  time" with no published end date (https://opencode.ai/v2/docs/console/models).

### Data-handling terms (the question this route exists to answer)

- **Documented no-retention, no-training for this exact route.** Official Console
  docs, Free models section: "**DeepSeek V4.1 Flash Free** is free on OpenCode for a
  limited time. **Its provider follows a zero-retention policy and does not use your
  data for model training.**" (https://opencode.ai/v2/docs/console/models,
  fetched 2026-11-01). The Privacy preamble on the same page: "All our models are
  hosted in the US and EU. Our providers follow a zero-retention policy and do not
  use your data for model training, with the following exceptions:" — the exceptions
  list (Big Pickle, Flint 40B Free, MiMo-V2.6-Flash Free, the three NVIDIA Nemotron
  free endpoints, plus per-vendor notes for OpenAI/Anthropic/Mistral/Beam) **does
  not include DeepSeek V4.1 Flash Free** (same URL). So: input does **not** train
  models, and a no-retention statement **is** published — this is the documented
  basis for the catalog's `no-retention` exposure (README §4 rule).
- **The gap that remains:** what **OpenCode itself** does with prompts transiting its
  gateway is not stated. GitHub issue #35102 (2026-07-03) asked for exactly that and
  was auto-closed unanswered; it quotes the privacy policy's collected category
  "information included in conversations or prompts that you submit to AI" with the
  purpose "Providing, Customizing and Improving the Services… testing, research,
  internal analytics and product development" — "broad enough to potentially cover
  training internal models, but there's no explicit commitment one way or the other"
  (https://github.com/anomalyco/opencode/issues/35102;
  policy https://opencode.ai/legal/privacy-policy). The Terms of Service defer
  third-party model data use to each model's own terms
  (https://opencode.ai/legal/terms-of-service). Zero-retention is a
  **downstream-provider** promise, not a gateway-level one.
- Third-party read agrees with the per-model promise and the gap: "DeepSeek V4.1
  Flash Free is not on the exception list, and the page says its provider follows a
  zero-retention policy" (explainx.ai, 2026-10-15/17,
  https://www.explainx.ai/blog/opencode-deepseek-v4-1-flash-free-zen-go-limits-what-is-verified-2026),
  which also notes the Go privacy table marks DeepSeek V4.1 Flash "0 days*" retention
  with an unread footnote, and advises that "DeepSeek is a China-based provider and
  … your own company policy may restrict sending code there regardless of what the
  hosting intermediary promises" (same URL).

### Benchmark standing

- **No first-party rows for the id itself** (stated above; `--anchors` 2026-11-01).
  Its board positions are inherited family standing at 0.5× share.
- **Family anchors (verified, feed 2026-11-01T12:00:16Z):** deepseek-v4-pro family
  AA 23.1/68.8/41.3 ($0.11/$4.00) and 59.4 coding / 26.3 agentic ($1.74/$3.48);
  evals gpqa_diamond 90.3% / 87.1%, tau_bench_verified_airline 77.5% / 76.8%.
- **The actual family (v4.1-flash), from the same feed:** no AA rows; OpenRouter
  evals gpqa_diamond **87.9–90.2%** across slugs (bare 87.9, `-20260910` 89.1,
  `-20261017` 90.1, `-1017` 90.2) at $0.0066–0.0230/task; tau airline **72.3–75.1%**
  (`-20261017` 72.3, `-20260910` 75.1); Design Arena `deepseek-v4.1-flash-20261017`
  3d Elo 1362 (47.3% win), website 1300, svg 1248 — mid-pack at best.
- **AA's own page (v5.0 era, 2026-11-01):** intelligence index **N/A** (0910
  deprecated), speed **182.1 t/s (#7/79)**, TTFT 0.90s, $0.30/$1.20 list, 552B/16B
  active, MIT, 20 providers (https://artificialanalysis.ai/models/deepseek-v4-1-flash).
  Under the previous v4.3.2 scale it scored 39 (2026-10-17 snapshot) — not
  comparable to today's numbers.
- The catalog's free-route context of **1024K** (policy.json `free_models`, verified
  by `--scope`: "context 1024K, $0.00/$0.00") conflicts with secondary reports that
  the free endpoint is capped at **~200K in / 32K out** vs 1M/131K paid
  (https://www.aipromonow.com/en/promos/opencode-zen-deepseek-v4-1-flash-free-oct2026;
  explicitly flagged as "not confirmed in OpenCode docs" by explainx, URL above).
  OpenCode's docs state no cap. Report the conflict; don't silently pick one.

### Opinions

- **Family reception** (context, all dated): HN thread on the 1017 update, 487
  points/469 comments — "crazy numbers for a Flash model", "daily driver since V4",
  dissent on UI design vs Opus 5.5 (https://news.ycombinator.com/item?id=50129045);
  modelsentiment index **54/100, no clear lean** with cost praised 90% and speed 78%
  but **writing & tone only 39%** (https://modelsentiment.com/m/deepseek-v4.1-flash);
  recurring writing/censorship complaints in r/DeepSeek
  (https://www.reddit.com/r/DeepSeek/comments/1wcht7m/,
  https://www.reddit.com/r/DeepSeek/comments/1wiqlz4/) and r/SillyTavernAI
  (https://www.reddit.com/r/SillyTavernAI/comments/1wcbg1q/); an unverified,
  contested PSA about API-key abuse in a sandbox
  (https://www.reddit.com/r/LocalLLaMA/comments/1x32vhx/); EQ-Bench Creative Writing
  v3 Elo 1540.1, mid-pack below the April V4-Flash (https://eqbench.com/creative_writing.html).
- **Free-route coverage:** launch announced 2026-10-15 (X, above); Chinese-language
  timeline says integrated 2026-09-10, Go quota raised to $80 on 2026-10-12, then an
  independent free tier added (https://www.chaincatcher.com/en/article/2296509);
  how-to guides confirm hands-on use without sign-in or card (techpilot.ai ran it
  2026-10-17, https://techpilot.ai/deepseek-v4-1-flash-free-opencode/;
  https://lucadidomenico.studio/en/blog/deepseek-v4-1-flash-free-opencode).
- **Speed on the free lane:** apidog's side-by-side (2026-10-16) timed one-line
  questions at **4–15 s (3 runs)** and write-and-run tasks at 16–36 s — i.e. the
  DeepSeek free lane was the *fast* free option that day, against GLM free's 7–196 s
  (https://apidog.com/blog/glm-5-3-flash-free-opencode/).
- **Still-live signal:** aipromonow's community poll reads 89% "still works" (18
  votes) as of the 2026-11-01 fetch (URL above). A Chinese community benchmark
  (Zhihu, via bswen) scored the *older* DeepSeek V4 Flash Free 5/5 on a harder
  programming round — the guide itself warns "A community test of DeepSeek V4 Flash
  Free is not a test of a later V4.1 Flash deployment"
  (https://docs.bswen.com/blog/2026-04-21-free-models-opencode/;
  original https://zhuanlan.zhihu.com/p/2068628560567349553).

### Known for

The free in-harness route to DeepSeek's current 552B CED flash model — the family
that this policy ranks #2–#4 across five domains — at $0 with a documented
zero-retention, no-training promise (https://opencode.ai/v2/docs/console/models).

### Caveats

- **Limited time, no end date, churn precedent:** every OpenCode free offer is
  "limited time" (docs, URL above); the predecessor route `deepseek-v4-flash-free`
  was added 2026-07-19 and dropped 2026-08-20 from the tracked free list, and a user
  report cited by explainx says an earlier DeepSeek free promo ended and vanished
  from the picker (https://mvalentsev.github.io/awesome-free-ai-coding/providers/opencode/;
  https://www.explainx.ai/blog/opencode-deepseek-v4-1-flash-free-zen-go-limits-what-is-verified-2026
  citing https://github.com/anomalyco/opencode/issues/43805).
- **Rate limits are real and unpublished:** the official bot answer on GitHub says
  "Rate limit exceeded" "comes from the OpenCode Zen service… The limit is enforced
  on the server, and… cover[s] more than one model, so switching to another free
  model or another project folder won't clear it. It usually resets after a while" —
  closed as not planned; sibling issues ask for the limit and reset time to be
  published (#56196, #56122, #55816, #52894)
  (https://github.com/anomalyco/opencode/issues/56211;
  https://github.com/anomalyco/opencode/issues/55816). Chronic 429s on sustained
  workloads are reported (https://github.com/anomalyco/opencode/issues/43786;
  https://github.com/anomalyco/opencode/issues/14273). Neither Zen nor Go docs
  publish a free-model rate limit (https://apidog.com/blog/glm-5-3-flash-free-opencode/).
- **In-OpenCode-only gate:** external calls return `403 FreeTierError: OpenCode's
  free tier can only be used from within OpenCode` (mvalentsev, verified 2026-11-01,
  URL above; apidog reproduced 403 on 2026-10-16). **Sources disagree on how solid
  that gate is:** a 2026-09-14 measurement found the free tier callable with a raw
  curl and no key/account — the only gate being an arbitrary `x-opencode-session`
  header — citing the gateway's handler source
  (https://note.com/bright_hosta5/n/nb1f00d9fd603?hl=en), and community plugins
  still exist to route the free lane from other harnesses with spoofed headers
  (https://dsh-plugin.org/plugins/jiujiezongheti/zen-useragent). State both; the
  gate's strictness has changed over time.
- **Serving quality unknown:** the docs never name which provider actually serves
  the free lane, whether it is quantized, or how it queues against paid traffic —
  "Whether its quantization, rate limits or queueing differ from the paid endpoint is
  not documented" (explainx, URL above). For family context, OpenRouter's paid
  v4.1-flash routes span $0.18–$2.40/M output across fp4/fp8/mxfp4 quants
  (2026-10-17 research, research/2026-10-top15-a-deepseek-glm.md).
- **Context likely 200K, not the catalog's 1024K** (conflict above) — large-repo
  sessions may overflow; verify with a long prompt before trusting either number.
- **No uptime commitment:** a free endpoint carries none; DeepSeek's own API had a
  ~5-hour outage on 2026-10-15 (https://www.explainx.ai/blog/deepseek-5-hour-api-outage-7-day-credit-refund-october-15-2026).
  Keep a paid fallback configured.
- **Gateway security:** OpenCode disclosed on 2026-10-17 that a legacy Console
  system was breached the night of 2026-10-16, exposing linked external provider
  API keys for ~1.4% of Console users (Anthropic revoked keys, OpenAI refunded
  credits) — it affected BYOK keys rather than the keyless free lane, but it is the
  gateway this route depends on
  (https://breachhistory.com/opencode/opencode-console-breach2026;
  https://labs.cloudsecurityalliance.org/research/csa-research-note-opencode-console-provider-key-breach-20261/).
- **Quality caveats inherited from the family:** most-verbose-tier output and the
  weakest writing-tone sentiment of the DeepSeek line (39% praise, above), mid-pack
  creative-writing Elo — fine for agentic/coding work, not for polished prose.
- **Licensing:** underlying weights are MIT (AA page, URL above) — no license
  friction for the model itself; the *route's* terms are OpenCode's
  (https://opencode.ai/legal/terms-of-service).

---

## opencode/glm-5.3-flash-free

### What it is — the route and its underlying model

- **OpenCode harness free route**, console id `glm-5.3-flash-free`, display name
  "GLM-5.3-Flash Free", endpoint
  `https://opencode.ai/inference/openai/v1/chat/completions`, priced **Free / Free /
  Free** (https://opencode.ai/v2/docs/console/models, fetched 2026-11-01). Local
  catalog check today: $0.00/$0.00, variants `low`/`high`/`max`, released-date
  2026-08-26 (the underlying model's release date). Announced free on **2026-10-16**
  (OpenCode on X: "GLM 5.3 Flash is now free in OpenCode",
  https://x.com/opencode/status/2110986357539754114).
- **The flash variant is GLM-5.3-Flash (Zhipu/Z.ai, released 2026-08-26):** a
  **newly trained base model** — "starts from a newly trained base model, with its
  architecture and training recipe redesigned around capability and efficiency…
  a hybrid architecture combining sparse and linear attention, sharply reducing
  long-context serving costs" (https://z.ai/blog/glm-5.3-flash) — **320B total / 18B
  active** MoE, first natively multimodal GLM-5 (text+image in), 1M context,
  **MIT** (https://artificialanalysis.ai/models/glm-5-3-flash;
  https://docsbot.ai/models/glm-5-3-flash; ~30T-token multimodal pre-training and
  low/high/max reasoning (default max) per https://opper.ai/zhipu/glm-5-3-flash).
  It is the cheap sibling of the 753B/40B GLM-5.3 flagship
  (https://z.ai/blog/glm-5.3) — Z.ai's own framing: "GLM-5.3-Flash: Frontier
  Intelligence, Flash Cost".
- **It has been free before, under a name:** from 2026-08-20 an anonymous "Ox Alpha"
  sat at zero price on OpenCode/OpenRouter until Z.ai revealed it as GLM-5.3-Flash
  on 2026-08-26 (https://apidog.com/blog/ox-alpha-was-glm-5-3-flash; the OpenCode
  data page itself labels the model "GLM-5.3-Flash (formerly ox-alpha)",
  https://opencode.ai/data/zhipuai/glm-5-3-flash; Bloomberg reveal via
  https://linas.substack.com/p/glm-5-3-flash-guide). That free window lasted six
  days (https://apidog.com/blog/glm-5-3-flash-free-opencode/).

### Data-handling terms

- **Same documented promise as the DeepSeek route, verbatim:** "**GLM-5.3-Flash
  Free** is free on OpenCode for a limited time. **Its provider follows a
  zero-retention policy and does not use your data for model training.**"
  (https://opencode.ai/v2/docs/console/models, fetched 2026-11-01). It is **not**
  among the page's training-use exceptions — unlike Big Pickle / Flint 40B Free /
  MiMo-V2.6-Flash Free ("collected data may be used to improve the model") and the
  NVIDIA endpoints ("do not submit personal or confidential data"), which is exactly
  why the catalog's `no-retention` exposure is documented rather than defaulted
  (README §4). Hosted "in the US and EU" per the same page's Privacy section.
- **Same gap:** gateway-level handling of prompts by OpenCode itself remains
  unstated — issue #35102 auto-closed unanswered
  (https://github.com/anomalyco/opencode/issues/35102); policy
  https://opencode.ai/legal/privacy-policy. The upstream-model question (Zhipu's own
  terms for its API) is separate from this lane's documented promise.

### Benchmark standing

- **No first-party rows for the id itself** (`--anchors`, 2026-11-01); ranks are the
  0.5× inherited family standing described in the provenance note.
- **Family anchors — contradicting the brief (see verification note):** feed
  `as_of` 2026-11-01T12:00:16Z carries `z-ai/glm-5.3-flash-20260826` AA
  **intelligence 27.8, coding 71.5, agentic 50.9, $0.10/$0.50** and
  `z-ai/glm-5.3-20260816` **31.7 / 74.8 / 53.1, $0.98/$3.08**; OpenRouter evals
  gpqa_diamond 84.1% (`-20260826`) and 90.9% (bare slug), tau airline 75.6% /
  70.0%; flagship glm-5.3 gpqa 85.4%/82.3%, tau 77.3%/76.0%; Design Arena
  `glm-5.3-flash-20260826` 3d Elo 1314 (56.1% win), svg 1277 (55%), website 1270.
- **AA's own page (v5.0, 2026-11-01):** intelligence **28** (#7/22 in its
  open-weights class), speed 68.7 t/s (#43/79, below the 73 median), TTFT 1.48 s,
  **$0.58/task (#8/21)**, verbosity 120M output tokens (#15/22), $0.15/$0.50,
  26 providers (https://artificialanalysis.ai/models/glm-5-3-flash). The 42 in the
  2026-10-17 research was the v4.3.2 scale — rescale, not regression.
- Family writing benchmark: GLM-5.3 flagship is the #1 open-weight model on EQ-Bench
  Creative Writing v3 (Elo 2075); GLM-5.3-Flash is **unscored under its own name** —
  the `ox-alpha` row at Elo 1971.7 is a hedged identity match
  (https://eqbench.com/creative_writing.html). LMArena via modelsentiment: flash
  Arena text #29/105, Code Arena #20/83, **AA agentic #8/51** (old-scale read)
  (https://modelsentiment.com/m/glm-5.3-flash).

### Opinions

- **Family reception (context):** modelsentiment scores GLM-5.3-Flash **63/100
  Positive, 7th of 26** (184 opinions/7d) — coding praised 84%, cost 96%,
  intelligence 80%, **writing & tone 50% (split)**, speed 42% split
  (https://modelsentiment.com/m/glm-5.3-flash). r/SillyTavernAI is warm — "GLM 5.3
  flash is very good… Prose is a bit better than alpha-" (an early post, written
  before the Ox Alpha identity was known)
  (https://www.reddit.com/r/SillyTavernAI/comments/1vz5cy0/). Local-hardware
  enthusiasm: Unsloth quants fit it in 100–128GB (https://linas.substack.com/p/glm-5-3-flash-guide)
  and "pruned to half the experts… Q3 (71 GB) solves every task the full 341 GB
  model solves" for coding (https://www.reddit.com/r/LocalLLM/comments/1x50ol2/).
  Nathan Lambert's line on the flagship — gains are post-training, model "likely a
  narrower… than Claude Fable or GPT Sol" — frames the family
  (https://www.interconnects.ai/p/glm-53-how-chinese-labs-keep-stride).
- **Free-route hands-on (the key opinion source):** apidog ran a clean install on
  2026-10-16 — no sign-in, no key — and the model **passed every coding test**, but
  was slow and uneven: one-line questions took **7–196 s across 11 runs**
  (write-and-run 13–109 s), and `--variant low` didn't fix it ("points to load on
  the free endpoint, not reasoning depth"); PDF attachments were rejected while
  images worked; measured metadata: **200K context / 32K output**, in-OpenCode-only
  (403 FreeTierError reproduced), and "'Flash' in this model's name refers to price,
  not speed" (https://apidog.com/blog/glm-5-3-flash-free-opencode/).
- **User chatter:** an X user testing the free setup reports "the 200K context limit
  becomes noticeable pretty quickly on larger repos. once the session gets long, i
  have to split work more aggressively"
  (https://x.com/yuhasbeentaken/status/2111019390460186911); aipromonow's poll reads
  82% "still works" (11 votes) as of 2026-11-01
  (https://www.aipromonow.com/en/promos/opencode-zen-glm-5-3-flash-free-oct2026);
  a hands-on piece frames it as "GLM 5.3 Flash Free in OpenCode: Can It Replace
  Claude or ChatGPT?" and corrects readers expecting the full GLM-5.3
  (https://www.mayhemcode.com/2026/10/glm-53-flash-free-in-opencode-can-it.html);
  a free-model directory lists it among 10 live OpenCode Zen free models (updated
  2026-10-30, https://freeinference.dev/providers/opencode-zen/).
- I found **no** Reddit/HN thread debating this free route's *output quality*
  specifically — community signal on the lane itself is usage/limits, not prose;
  the quality opinions above are family-level.

### Known for

The free in-harness route to Z.ai's 320B/18B multimodal GLM-5.3-Flash — the
intelligence-per-dollar Pareto pick of the family — with documented zero-retention
terms, ranked #3 orchestration / #5 ops on inherited family standing
(https://opencode.ai/v2/docs/console/models; https://z.ai/blog/glm-5.3-flash).

### Caveats

- **Latency is the route's own problem:** even at `low` effort, responses ran to
  ~196 s on launch day; "give the free model work you don't sit and watch"
  (https://apidog.com/blog/glm-5-3-flash-free-opencode/). The paid family is not
  fast either — AA measures 68.7 t/s, below the class median
  (https://artificialanalysis.ai/models/glm-5-3-flash).
- **Context/output caps:** measured 200K in / 32K out on the free lane vs 1M/131K
  paid — vs this policy's catalog row of **1024K**, which the measurement contradicts
  (apidog, URL above; aipromonow says the same). OpenCode's docs publish no cap;
  flag the conflict at distill time rather than trusting 1024K.
- **In-OpenCode-only, limited time, churn precedent:** 403 FreeTierError outside the
  harness (apidog; https://mvalentsev.github.io/awesome-free-ai-coding/providers/opencode/);
  no end date published; predecessors `glm-4.7-free` and `glm-5-free` now carry
  deprecated status in the models.dev catalog OpenCode reads, and the Ox Alpha free
  week lasted six days (https://apidog.com/blog/glm-5-3-flash-free-opencode/).
- **Rate limits unpublished and shared:** same GitHub evidence as the DeepSeek
  section — server-side, cross-model, no published reset
  (https://github.com/anomalyco/opencode/issues/56211;
  https://github.com/anomalyco/opencode/issues/55816); community guides add that
  free Zen models "throttle requests per minute… painful for large agentic loops"
  (https://www.maximalstudio.in/blog/opencode-zen-free-models) — treat that
  per-minute figure as a blog claim, not documentation.
- **The Go plan is not free:** on the $10 Go subscription the same model is metered
  at a $60 monthly usage limit (~31,580 requests by OpenCode's estimate), and only
  three promo models are marked free there (https://apidog.com/blog/glm-5-3-flash-free-opencode/).
- **Gateway-level data gap + breach** (identical to the DeepSeek section):
  OpenCode's own prompt handling is undocumented
  (https://github.com/anomalyco/opencode/issues/35102), and the 2026-10-16/17
  Console breach exposed linked BYOK keys for ~1.4% of users
  (https://breachhistory.com/opencode/opencode-console-breach2026).
- **Family-level quality caveats:** writing & tone sentiment is split (50%),
  creative-writing standing under its own name is unmeasured (ox-alpha Elo hedged),
  reasoning defaults to `max` upstream (thinking tokens bill as output on paid
  routes), and OpenRouter's paid flash routes lean on fp4/nvfp4 quants — pin fp8 or
  first-party there (https://modelsentiment.com/m/glm-5.3-flash;
  https://eqbench.com/creative_writing.html; https://opper.ai/zhipu/glm-5-3-flash).
- **Traffic-rank caveat inherited from the family:** the family's top-of-board
  traffic is partly an artifact of the Ox Alpha stealth launch, and these free-lane
  ranks are 0.5× inherited share with **0 measured tokens** — neither is deliberated
  preference for this route (https://linas.substack.com/p/glm-5-3-flash-guide).
- **Licensing:** MIT — no friction (https://artificialanalysis.ai/models/glm-5-3-flash).

---

## Policy summaries

**opencode/deepseek-v4.1-flash-free.** A limited-time, zero-retention route through
the OpenCode harness to DeepSeek-V4.1-Flash (552B CED MoE, MIT, updated to the 1017
checkpoint 2026-10-19), standing on inherited family share at research #3, coding
#2, ops #2 of this policy's boards as of 2026-11-01, at $0/$0 — with OpenCode's docs
stating its provider "follows a zero-retention policy and does not use your data for
model training" (https://opencode.ai/v2/docs/console/models;
https://x.com/opencode/status/2112220734768779441). Pick it for cost-free agentic
and coding loops inside OpenCode; what changes the decision: unpublished, cross-model
server-side rate limits (https://github.com/anomalyco/opencode/issues/56211), a
likely ~200K/32K free-lane cap against the catalog's 1024K (unconfirmed by docs,
https://www.aipromonow.com/en/promos/opencode-zen-deepseek-v4-1-flash-free-oct2026),
OpenCode's own gateway-level prompt use being undocumented
(https://github.com/anomalyco/opencode/issues/35102), in-OpenCode-only enforcement
(403 FreeTierError), no end date or uptime commitment — and no benchmark rows of its
own, so family quality caveats (verbosity, 39% writing-tone sentiment) apply
(https://modelsentiment.com/m/deepseek-v4.1-flash).

**opencode/glm-5.3-flash-free.** A limited-time, zero-retention OpenCode-harness
route to Z.ai's GLM-5.3-Flash (newly trained 320B/18B multimodal base, hybrid
sparse+linear attention, MIT, released 2026-08-26, free since 2026-10-16), carrying
inherited family standing at orchestration #3 / ops #5 / coding #6 as of 2026-11-01,
with the same documented "zero-retention… does not use your data for model training"
terms (https://opencode.ai/v2/docs/console/models;
https://z.ai/blog/glm-5.3-flash;
https://x.com/opencode/status/2110986357539754114). Pick it for patient,
cost-free coding and orchestration work inside OpenCode where GLM-family quality is
wanted; what changes the decision: measured 200K/32K free-lane limits vs the
catalog's 1024K, launch-day latency of 7–196 s per answer and a below-median 68.7
t/s family speed (https://apidog.com/blog/glm-5-3-flash-free-opencode/;
https://artificialanalysis.ai/models/glm-5-3-flash), unpublished shared rate limits,
six-day precedent for this model's free windows ending, PDF-attachment rejection on
the lane, and the same undocumented gateway-level prompt handling — note the family
rows **do** exist in the benchmarks feed (AA 27.8/71.5/50.9 on 2026-11-01), so the
brief's "no rows" line should not be carried into the summary.