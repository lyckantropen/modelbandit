# research/2026-11-free-catalog-admissions — five opencode/* free routes missing from policy.json `free_models` — 2026-11-15

**Scope.** Free-tier maintenance (README §4) for the 2026-11 summaries refresh: the
harness listing serves five free `opencode/*` models with **no** entry in policy.json's
`free_models` catalog, so they are invisible to modelbandit's deal/pick. This file gathers
the admission facts for each — what it is, `context_length` with its source, `exposure`
from documented data use, and whether a `summaries` entry resolves — plus a JSON snippet
per proposed entry and proposed summaries. Sources pulled **2026-11-15**: OpenCode Console
docs (https://opencode.ai/v2/docs/console/models), OpenCode's models metadata endpoint
`https://opencode.ai/inference/v1/models` — the endpoint the docs page itself names for
"the full list of available models and their metadata"
(https://opencode.ai/v2/docs/console/models) — OpenCode's Terms of Use (effective
Nov 8, 2026, https://opencode.ai/legal/terms-of-service), the OpenRouter keyless catalog
(https://openrouter.ai/api/v1/models), OpenRouter's free-variant docs
(https://openrouter.ai/docs/guides/routing/model-variants/free), vendor pages, and
third-party coverage — all cited inline. Every claim below carries its URL; where a fact
could not be found, that is stated instead of guessed.

**Method notes.**
- `context_length` sources follow README §4: OpenCode's own docs/metadata endpoint, or
  the OpenRouter keyless catalog when the model also exists there — the source is named
  per model below.
- `exposure` classes per README §4 and GLOSSARY.md: `no-retention` = "input is neither
  stored nor trained on"; `trains` = "input may be stored, collected, or trained on";
  no documentation → defaults to `trains`. The validator's vocabulary is
  `EXPOSURES = ("no-retention", "trains", "local")`
  (skills/modelbandit/scripts/modelbandit.py, line 2979).
- A grep of policy.json (2026-11-15) confirms **no** summaries, exposure overrides, or
  `free_models` entries exist for any of the five ids or their families
  (`beam|iceman|inkling|longcat|reflection|thinkingmachines|meituan` — no matches), so
  four new summaries and five new entries are proposed; only
  `opencode/minimax-m3.1-flash-free` resolves an existing summary.

**Free-tier window documentation (both platforms, what I actually found).**
- OpenCode words **every** free offer "for a limited time" with **no published end date**
  (Free models section, https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
  LongCat 2.5 Free additionally carries the only published numeric cap in this batch:
  **100 requests per day** (same URL). Churn precedent on the same page: the deprecated
  table now lists **Crouton Alpha Free (November 9, 2026)** and **Pulse Alpha Free
  (November 6, 2026)** among retired free routes.
- OpenRouter's catalog carries an explicit `expiration_date` field — **`null`** for
  `thinkingmachines/inkling-2-small` and its `:free` twin (fetched 2026-11-15), i.e. no
  published window end; its docs only say free variants "may have different rate limits
  or availability compared to paid versions" and that fallbacks to paid models are billed
  (https://openrouter.ai/docs/guides/routing/model-variants/free).
- Server-side rate limits on OpenCode's free lanes remain unpublished and cross-model —
  carried from this repo's prior cycle (research/2026-11-top15-a-opencode-deepseek-glm.md,
  citing https://github.com/anomalyco/opencode/issues/56211 and
  https://github.com/anomalyco/opencode/issues/55816).
- **Docs-vs-serving discrepancy, recorded not researched:** OpenCode's docs still list
  `Nemotron 3 Ultra Free` in the endpoints, pricing and Free-models tables (fetched
  2026-11-15, https://opencode.ai/v2/docs/console/models) while the harness listing no
  longer serves it; retirement was already decided for this cycle.

---

## opencode/beam-free

### What it is

- A Console free route ("Beam Free", priced **Free / Free / Free** for input/output/
  cached read, https://opencode.ai/v2/docs/console/models, fetched 2026-11-15) whose
  canonical id in OpenCode's own metadata is **`reflection/beam-1.0-501b-a23b`**
  (https://opencode.ai/inference/v1/models, fetched 2026-11-15) — i.e. **Reflection AI's
  Beam 1.0**, an open-weight sparse mixture-of-experts reasoning model, **501B total /
  23B active per token**, "for coding and long-horizon agentic workflows" (OpenRouter
  catalog description, https://openrouter.ai/api/v1/models, fetched 2026-11-15;
  Cloudflare's model docs concur: "Beam-1.-501B-A23B is Reflection AI's open-weights
  mixture-of-experts model with 501B total parameters and 23B active parameters, built
  for coding, reasoning, and agentic workloads",
  https://developers.cloudflare.com/ai/models/reflection-ai/beam-1.0-501b-a23b/).
- OpenCode metadata for the route (fetched 2026-11-15): `release_date` 2026-10-05,
  `last_updated` 2026-10-16, knowledge cutoff 2026-06-30, text-only input, reasoning
  with efforts `low`→`max`, `open_weights: true`.
- Free-window start: OpenCode announced free access to GLM 5.3 Flash and Beam "with a
  full 1M-token context window" on 2026-10-17
  (https://aicoder.com/news/news-20261017-opencode-free-glm-5-3-flash-reflection-beam-1m-context);
  a directory confirms OpenCode added Beam Free "to both Zen and Go"
  (https://www.aipromonow.com/en/promos/opencode-beam-free-oct2026).
- Licence: **Apache 2.0** per third-party coverage of Reflection's release
  (https://digintoai.com/en/articles/opencode-beam-1-0-free) — I did **not** verify this
  against Reflection's own model card; treat as reported, not confirmed.

### context_length (required)

**1048576.** Two independent sources agree: the OpenRouter keyless catalog's
`reflection/beam-1.0-501b-a23b` entry has `context_length: 1048576` (fetched 2026-11-15),
and OpenCode's models metadata endpoint reports `limit.context 1048576` / output 131072
for `beam-free` (same date). A third-party model page agrees (context window 1,048,576,
max tokens 131,072, https://pi.dev/models/opencode/beam-free).

### Exposure

Documented — classed **`trains`, with an explicit judgment flag** (see below).

- Console docs, Free models section: "**Beam Free** is free on OpenCode for a limited
  time. **Its provider does not use your data for training and retains it for 30 days
  for safety reasons.**" Privacy table: "**Beam Free:** Prompts and other inputs are not
  used for training. Data is retained for 30 days for safety reasons."
  (both https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
- So: training use is documented **absent**, retention is documented **present**. Under
  the GLOSSARY's class definitions (`no-retention` = "input is neither stored nor trained
  on"; `trains` = "input may be stored, collected, or trained on", GLOSSARY.md
  "Exposure"), 30-day storage puts this route in **`trains`** — the class is decided by
  storage, not training. **Flag for the distiller:** this is the one admission where the
  documentation says training does NOT happen; if `exposure` is read as training-only,
  the vocabulary has no class for "retained-but-not-trained" and this entry should be
  held until that is resolved. README §4's two templates don't cover it verbatim.
- The Terms of Use defer third-party-model data use to each model's own terms and add
  that on an unpaid account "we may use Content to further develop and improve our
  Services" (https://opencode.ai/legal/terms-of-service) — the gateway-level gap this
  repo documented for the DeepSeek/GLM lanes (GitHub issue #35102 auto-closed unanswered,
  https://github.com/anomalyco/opencode/issues/35102) applies here too.
- Geo-restriction (limits documentation): Beam Free "is not available in Angola,
  Belarus, Cambodia, China (including Hong Kong and Macau), Cuba, the Democratic Republic
  of the Congo, Equatorial Guinea, Iran, Iraq, Laos, Libya, Nigeria, North Korea, Russia,
  Syria, Turkmenistan, Uzbekistan, Venezuela, or the Crimea, Donetsk, and Luhansk regions
  of Ukraine" (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).

### Window / limits

"limited time", no end date (docs URL above). OpenRouter has **no `:free` entry** for
Beam (only the paid `reflection/beam-1.0-501b-a23b`, catalog entry created 2026-10-16
14:21 UTC, $0.30/M input — verified against the keyless catalog 2026-11-15), so the
OpenCode lane is the only free way to this model. Shared free-lane rate limits remain
unpublished (prior-cycle citations above).

### Benchmark standing (context for the summary)

No first-party rows for the `opencode/*` id itself (an `opencode/*` id has no benchmark
row of its own — repo precedent from research/2026-11-top15-a-opencode-deepseek-glm.md).
From the catalog-embedded benchmark rows fetched 2026-11-15
(https://openrouter.ai/api/v1/models), for the paid family id: Artificial Analysis
intelligence index **17.7** (coding/agentic **null**); Design Arena — website Elo 1239
(46.0% win, rank 50), uicomponent 1260 (49.0%, rank 39), codecategories 1224 (43.8%,
rank 55), gamedev 1187 (40.1%, rank 62), 3d 1125 (33.5%, rank 81). Mid-to-lower pack at
best; reasoning defaults to `max` effort (same fetch). No community opinion source on the
free lane was found beyond launch coverage (URLs above).

### Resolves a summary?

**No** — nothing in policy.json `summaries` matches `opencode/beam-free` or
`reflection/beam` by prefix (grep 2026-11-15). Propose a new summary keyed
**`reflection/beam`** (family-key precedent: `opencode/deepseek-v4.1-flash-free` →
`deepseek/deepseek-v4.1-flash`), which also stands in for the paid OpenRouter id should
it ever rank.

---

## opencode/iceman-free

### What it is

- A **stealth route**: "**Iceman Free** is a stealth model that's free on OpenCode for a
  limited time. The team is using this time to collect feedback and improve the model."
  (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15). OpenCode's metadata
  endpoint carries **no `canonical_id`** — description "Stealth model, free for a limited
  time", `release_date` 2026-11-06, text-only input, tools and reasoning supported
  (https://opencode.ai/inference/v1/models, fetched 2026-11-15).
- Maker: **undisclosed**. "No lab had claimed it when ArtificialWatch last checked, on
  November 10, 2026"; first listed on the OpenCode console 2026-11-06, first observed by
  their hourly sweep 2026-11-07 00:03 UTC via models.dev
  (https://artificialwatch.com/wire/radar-opencode-iceman-free, fetched 2026-11-15). The
  same source's headline says "Iceman, the OpenCode stealth model no lab has claimed, has
  run 3.4 trillion tokens" — the window for that number is unstated (same URL). A
  dedicated tracker speculates about the maker (https://stealthmodels.com/iceman-contributor);
  **I found no confirmed identity and repeat none.**
- What it is beyond that: unknown — no vendor, family, size, licence, or benchmark
  documentation exists as of 2026-11-15. This is stated rather than guessed.

### context_length (required)

**262144** (output 131072) — from OpenCode's own models metadata endpoint
(`limit.context 262144`, https://opencode.ai/inference/v1/models, fetched 2026-11-15),
the endpoint the console docs page names as the metadata source. **Not on OpenRouter** —
the keyless catalog has no iceman entry (checked 2026-11-15), so no cross-check exists.
ArtificialWatch's independent catalog read agrees: "Context window: 262,144 tokens …
Listed price: $0/$0 per 1M" (URL above).

### Exposure

Documented — **`trains`**, the strongest documented exposure in this batch.

- Privacy exceptions list: "**Iceman Free:** During its free period, collected data is
  **retained and used to improve the model**." Free models section: "The team is using
  this time to collect feedback and improve the model."
  (both https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
- Gateway-level handling by OpenCode itself remains undocumented (issue #35102,
  https://github.com/anomalyco/opencode/issues/35102), and with no named vendor there are
  **no vendor terms to check** — the identity gap and the data-use gap compound.

### Window / limits

"limited time", no end date (docs URL above). Stealth windows churn quickly — the
precedent in this policy is `stealth/space-bunny-alpha`, withdrawn at its listed expiry
2026-10-05 (policy.json summary). Rate limits unpublished (prior-cycle citations above).

### Resolves a summary?

**No** (grep 2026-11-15). Propose a new summary keyed **`opencode/iceman-free`** —
self-keyed because no family exists to key on (identity unknown), the same self-key
pattern the `lmstudio/*` catalog entries use.

---

## opencode/inkling-2-small-free

### What it is

- The Console free route "Inkling 2 Small Free" — canonical id in OpenCode's metadata:
  **`thinkingmachines/inkling-2-small`**, i.e. Thinking Machines Lab's **Inkling 2
  Small**, confirmed as the brief expected (https://opencode.ai/inference/v1/models,
  fetched 2026-11-15).
- The model: "we are introducing **our second model generation** with Inkling 2 Small.
  It is a Mixture-of-Experts model with **594B total parameters, 17B active**, and
  supports image inputs and variable effort" (Thinking Machines Lab's announcement,
  https://thinkingmachines.ai/news/inkling-2-small/, launched **2026-11-05**; model card
  https://thinkingmachines.ai/model-card/inkling-2-small/). Open-weight multimodal
  reasoning model, text+image in (OpenRouter catalog description and modality,
  https://openrouter.ai/api/v1/models, fetched 2026-11-15; OpenCode metadata:
  `open_weights: true`, family `ling`, efforts `none|minimal|low|medium|high|max`,
  `release_date` 2026-11-05, `last_updated` 2026-11-12).
- OpenRouter serves it as **`thinkingmachines/inkling-2-small`** ($0.30/M input) and
  **`thinkingmachines/inkling-2-small:free`**, both entries created 2026-11-09 22:04 UTC
  (canonical slug `thinkingmachines/inkling-2-small-20261107`), `text+image->text`,
  `expiration_date: null` (keyless catalog, fetched 2026-11-15).
- Free-window announcements: Soumith Chintala announced the OpenCode free route "for a
  limited time" in a post dated 2026-11-07 (https://blockchain.news/ainews/inkling-2-small-free-on-opencode-limited-time-access);
  a directory covers both free routes (OpenRouter + OpenCode Zen),
  https://www.aipromonow.com/en/promos/inkling-2-small-free-openrouter-opencode.

### context_length (required)

**1048576.** OpenRouter keyless catalog: `context_length 1048576` for both the paid and
`:free` entries (fetched 2026-11-15). OpenCode's models metadata endpoint agrees
(`limit.context 1048576`, output 131072, same date). A third-party page checked
2026-11-11 independently lists 1,048,576
(https://www.ayautomate.com/free-models/opencode-zen-inkling-2-small-free).

### Exposure

Documented — **`trains`**.

- The route's own bullet: "**Inkling 2 Small Free** is free on OpenCode for a limited
  time. **Its provider retains your data and may use it for model training**; see
  Privacy. It's not available in the European Union, Iceland, Liechtenstein, Norway,
  Cuba, Iran, North Korea, Russia, Ukraine, or Venezuela."
  (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
- Privacy exceptions list: "During its free period, collected data is **retained** and
  **may be used to monitor the model's real-world performance and for model training**.
  See Thinking Machines' Terms of Service
  (https://thinkingmachines.ai/legal/tml-free-research-api-tier-terms-of-service.pdf)
  and Privacy Notice
  (https://thinkingmachines.ai/legal/tml-free-research-api-tier-privacy-notice.pdf)"
  (exception text https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
  This is the only model in this batch whose OpenCode doc explicitly links **vendor**
  terms and a vendor privacy notice — both PDFs are cited here as OpenCode links them; I
  did not fetch their contents.

### Window / limits

"limited time", no end date; limits "not published" per a directory checked 2026-11-11
(https://www.ayautomate.com/free-models/opencode-zen-inkling-2-small-free). On
OpenRouter the twin's `expiration_date` is `null` and its docs only promise that free
variants "may have different rate limits or availability compared to paid versions"
(https://openrouter.ai/docs/guides/routing/model-variants/free, fetched 2026-11-15).
Standout limit: the **EU/Iceland/Liechtenstein/Norway geo-block** (docs URL above).

### Benchmark standing (context for the summary)

No rows for the `opencode/*` id itself. Catalog-embedded rows for the family id fetched
2026-11-15 (https://openrouter.ai/api/v1/models): Artificial Analysis intelligence index
**30.6**, coding/agentic **null**, no Design Arena rows; reasoning **mandatory**,
default effort `high`, supported efforts minimal→max (default parameters same fetch).
Community/opinion signal on the free lanes themselves: none found beyond launch coverage
(URLs above).

### Resolves a summary?

**No** (grep 2026-11-15). Propose a new summary keyed **`thinkingmachines/inkling-2-small`**
(family key, consistent with how other `opencode/*` entries point at the underlying
model's key).

---

## opencode/longcat-2.5-free

### What it is

- The Console free route "LongCat 2.5 Free" — OpenCode's metadata carries canonical id
  **`meituan/longcat-2.5`** and the description "**Meituan's multimodal reasoning model
  for long-horizon coding and agent tasks, with visual understanding and a 1M-token
  context window**"
  (https://opencode.ai/inference/v1/models, fetched 2026-11-15). The brief's "possibly
  Meituan's LongCat family" is therefore **confirmed by OpenCode's own canonical id**.
- Route metadata (same fetch): `release_date` 2026-11-02, `last_updated` 2026-11-02,
  `open_weights: **false**`, text+image in / text out, output 262144, reasoning with
  toggle. (OpenCode documents no free-window start date; I state the metadata date
  without claiming it is the window's start.)
- Size/specs: explainx's update gives "Confirmed specs: about **1.6T total parameters,
  ~48B active**, 1M context, and image understanding" for `LongCat-2.5-Preview`, live on
  Meituan's own API since the 25 September 2026 changelog
  (https://www.explainx.ai/blog/longcat-2-5-1-6-trillion-agent-model-2026;
  corroborated: https://www.orcarouter.ai/blog/longcat-2-5) — these are **vendor preview
  specs, not independently reproduced**; per explainx Meituan's technical report was still
  pending, and the pitch shifted from LongCat 2.0's coding-benchmark framing to agent
  autonomy (same URL). LongCat 2.0 context: a 1.6T/48B-active MoE trained on AI ASIC
  superpods (same URL).
- **Not on OpenRouter**: the keyless catalog carries only `meituan/longcat-2.0`
  (context_length 1048756) — no 2.5 entry as of 2026-11-15 (checked), so there is **no
  OpenRouter cross-check** for this route and no `:free` twin. A provider aggregator lists
  "Longcat 2.5 Preview Free" among the most recently added OpenCode Go models as of
  2026-11-11 (https://models.litellm.ai/providers/opencode_go).
- **Open-weights conflict, reported not resolved:** OpenCode's metadata says
  `open_weights: false`, while explainx (2026-09-27) wrote "LongCat 2.0 was MIT licensed
  … LongCat 2.5 is expected to follow, but confirm the model card before relying on it"
  (URL above). Neither position is confirmed against a Meituan model card as of
  2026-11-15.

### context_length (required)

**1000000.** Source: OpenCode's own models metadata endpoint (`limit.context 1000000`,
output 262144, https://opencode.ai/inference/v1/models, fetched 2026-11-15) — the
endpoint the console docs page names as the metadata source. The route description says
"1M-token context window" and explainx's confirmed preview specs also say 1M context
(URLs above). OpenRouter has no row to cross-check against (absence verified 2026-11-15).

### Exposure

Documented — **`no-retention`**, the cleanest promise in this batch.

- Free models section: "**LongCat 2.5 Free** is free on OpenCode for a limited time,
  **with a limit of 100 requests per day**. **Its provider follows a zero-retention
  policy and does not use your data for model training.** It's not available in [long
  country list]."
  (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
- Privacy table: "**LongCat 2.5 Free: Hosted in China.** Prompts and other inputs are
  **not used for training or retained**." (same URL).
- Caveats that travel with the promise: the route is **hosted in China** (same URL) —
  jurisdiction may fail company policy regardless of what the intermediary promises, the
  exact advice this repo's prior cycle recorded for the DeepSeek lane
  (research/2026-11-top15-a-opencode-deepseek-glm.md, citing
  https://www.explainx.ai/blog/opencode-deepseek-v4-1-flash-free-zen-go-limits-what-is-verified-2026);
  and zero-retention is a **downstream-provider** promise — OpenCode's own gateway-level
  handling of prompts remains undocumented (issue #35102 auto-closed unanswered,
  https://github.com/anomalyco/opencode/issues/35102), with third-party-model data use
  deferred to each model's terms (https://opencode.ai/legal/terms-of-service).

### Window / limits

"limited time", no end date, **plus the only published numeric cap in this batch: 100
requests per day** (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
That cap — not privacy — is the main fit constraint: it rules the route out for
high-volume agent rings.

### Benchmark standing (context for the summary)

None found: no OpenRouter row for 2.5 (checked 2026-11-15), hence no benchmark feed
coverage, and no independent benchmark or community opinion of the OpenCode free lane as
of 2026-11-15 — vendor preview framing only (explainx, orcarouter URLs above). Stated as
an evidence gap, not filled by inference from LongCat 2.0.

### Resolves a summary?

**No** (grep 2026-11-15). Propose a new summary keyed **`meituan/longcat-2.5`**.

---

## opencode/minimax-m3.1-flash-free

*OpenCode-free-specific facts only; the model research of record is
research/2026-10-top15-h-flash-tier.md (2026-10-25) and policy.json already carries
summary `minimax/minimax-m3.1-flash` — not redone here.*

### What it is

- The Console free route "MiniMax M3.1 Flash Free" — canonical id in OpenCode's
  metadata: **`minimax/MiniMax-M3.1-Flash`**
  (https://opencode.ai/inference/v1/models, fetched 2026-11-15). Route metadata:
  `release_date` 2026-10-19 (= MiniMax M3.1 Flash's launch date; the OpenRouter catalog
  id was created that day, per research/2026-10-top15-h-flash-tier.md), `limit.context`
  **1000000** / output **512000**, inputs text + images (jpeg/png/gif/webp) + video
  (mp4/avi/quicktime/mkv), reasoning efforts `low`→`max`, `open_weights: true`
  (same fetch). Priced **Free / Free / Free** in the Console price table
  (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
- Route status: its OpenRouter `:free` window is **already gone** — ended 2026-10-22/23,
  leaving the model paid-only on OpenRouter at $0.15/$0.60
  (research/2026-10-top15-h-flash-tier.md, citing
  https://freetokens.custats.info/offers/openrouter-minimax-m3-1-flash-free.html and
  https://openrouter.ai/api/v1/models) — so this OpenCode lane is currently the only free
  route to M3.1 Flash.

### context_length (required)

**1048576.** Source: OpenRouter keyless catalog `minimax/minimax-m3.1-flash`
`context_length: 1048576` (fetched 2026-11-15) — README §4's OpenRouter source, and
consistent with the existing summary's "1M ctx". OpenCode's own metadata endpoint
reports `limit.context 1000000` for the free route (same fetch) — same ~1M window, two
roundings of the same number; either is defensible, the OpenRouter figure is proposed.

### Exposure

Documented — **`no-retention`**.

- "**MiniMax M3.1 Flash Free** is free on OpenCode for a limited time. **Its provider
  follows a zero-retention policy and does not use your data for model training.**"
  (https://opencode.ai/v2/docs/console/models, fetched 2026-11-15).
- It is **not** among the Privacy section's exceptions on the same page (unlike
  MiMo-V2.6-Flash Free, Big Pickle, Iceman, Flint, the Nemotron endpoints, Beam, Inkling),
  and the preamble states "All our models are hosted in the US and EU. Our providers
  follow a zero-retention policy and do not use your data for model training, with the
  following exceptions:" (same URL) — so both halves of `no-retention` (not stored, not
  trained on) are documented for this route.
- Same standing caveats as every OpenCode free lane: gateway-level prompt handling by
  OpenCode itself undocumented (https://github.com/anomalyco/opencode/issues/35102);
  Terms defer third-party data use to model terms
  (https://opencode.ai/legal/terms-of-service).

### Window / limits

"limited time", no end date (docs URL above); unpublished cross-model server-side rate
limits (prior-cycle citations above). The paid OpenRouter sibling gives a fallback once
the window closes.

### Resolves a summary?

**Yes** — policy.json `summaries` contains `minimax/minimax-m3.1-flash` (verified
2026-11-15), reachable via the entry's explicit `summary_ref`. **No new summary is
proposed for this model.**

---

## Proposed free_models entries

For each: a sourced `context_length` and a documented `exposure` decision — both
required by README §4 — plus the `summary_ref` naming the summaries key (existing for
Minimax, new for the other four).

```json
"opencode/beam-free": {
  "context_length": 1048576,
  "exposure": "trains",
  "summary_ref": "reflection/beam"
}
```

```json
"opencode/iceman-free": {
  "context_length": 262144,
  "exposure": "trains",
  "summary_ref": "opencode/iceman-free"
}
```

```json
"opencode/inkling-2-small-free": {
  "context_length": 1048576,
  "exposure": "trains",
  "summary_ref": "thinkingmachines/inkling-2-small"
}
```

```json
"opencode/longcat-2.5-free": {
  "context_length": 1000000,
  "exposure": "no-retention",
  "summary_ref": "meituan/longcat-2.5"
}
```

```json
"opencode/minimax-m3.1-flash-free": {
  "context_length": 1048576,
  "exposure": "no-retention",
  "summary_ref": "minimax/minimax-m3.1-flash"
}
```

**Flags — read before distilling:**

- **opencode/beam-free — the one exposure judgment call.** Its documentation is
  "not used for training" **and** "retained for 30 days" (https://opencode.ai/v2/docs/console/models).
  It is admitted as `trains` on the GLOSSARY's storage clause ("input may be stored,
  collected, or trained on") — NOT on training language, which the docs explicitly
  contradict. **If the operator reads `exposure` as "does input train a model", recommend
  NOT admitting this entry as-is**: the vocabulary (`EXPOSURES = no-retention | trains |
  local`) has no class for "retained-but-not-trained", and no-train documentation means
  `trains` would misreport the training fact. The alternatives are holding the entry or
  extending the vocabulary first. Everything else about the entry (context, summary) is
  admit-ready.
- **opencode/iceman-free — thinnest evidence, admit-ready by the bar but flagged.** Both
  required facts are documented (ctx 262144 from OpenCode's metadata endpoint; exposure
  `trains` from OpenCode's Privacy table), so it meets README §4. But the maker, family,
  quality, licence, benchmarks and longevity are all unknown, and there is no family to
  inherit standing from — the proposed summary says exactly that. **Recommend-skip is
  defensible** if the operator doesn't want an unclaimed stealth route visible to
  deal/pick; I recommend admitting only alongside that honest summary.
- **opencode/inkling-2-small-free, opencode/longcat-2.5-free,
  opencode/minimax-m3.1-flash-free — admit-ready.** Both required facts sourced for each;
  the Minimax entry needs no new summary (existing key resolves).
- Three of the five proposed `summary_ref` values name summaries that do **not yet
  exist** (`reflection/beam`, `thinkingmachines/inkling-2-small`, `meituan/longcat-2.5`)
  plus the self-keyed `opencode/iceman-free` — admission requires them to land in
  `summaries` together with the entries (README §4).

---

## Policy summaries

Proposed `summaries` entries, 2–3 sentences each, dated where numbers appear. No entry
for Minimax — its existing summary resolves.

**reflection/beam.** Reflection AI's Beam 1.0 — a 501B-total/23B-active open-weight
sparse MoE for coding and long-horizon agentic work (knowledge cutoff 2026-06-30,
OpenCode metadata release 2026-10-05; Apache 2.0 licence reported by third parties, not
verified against Reflection's model card) — has been free on the OpenCode Console as
`opencode/beam-free` since the ~2026-10-16/17 announcement, at 1,048,576 ctx
(https://opencode.ai/inference/v1/models; https://openrouter.ai/api/v1/models;
https://aicoder.com/news/news-20261017-opencode-free-glm-5-3-flash-reflection-beam-1m-context;
all fetched 2026-11-15). Pick it only for cost-free long-context agentic/coding loops
inside OpenCode with effort pinned (its default is `max`); what changes the decision: a
weak catalog-embedded benchmark standing (AA intelligence 17.7 with coding/agentic null,
Design Arena website Elo 1239 rank 50, as of 2026-11-15,
https://openrouter.ai/api/v1/models), documented **30-day retention** even though
training is documented not to happen (class `trains` on storage grounds —
https://opencode.ai/v2/docs/console/models), a long geo-block list (China, Russia and
more, same URL), unpublished shared free-lane rate limits
(https://github.com/anomalyco/opencode/issues/56211), and a "limited time" window with
no end date.

**opencode/iceman-free.** OpenCode stealth route, listed 2026-11-06 as "a stealth model
that's free on OpenCode for a limited time" — 262,144 ctx / 131,072 out, text-only with
tools and reasoning, no canonical id, and unclaimed by any lab as of 2026-11-10
(https://opencode.ai/inference/v1/models;
https://artificialwatch.com/wire/radar-opencode-iceman-free, both fetched 2026-11-15).
Exposure is the batch's worst and documented: "collected data is retained and used to
improve the model" during the free period
(https://opencode.ai/v2/docs/console/models) — pick it only for non-sensitive,
throwaway experimentation when nothing else is free. Everything that normally decides a
pick is unknown — maker, quality, benchmarks, licence, vendor terms, and how long the
codename lives (ArtificialWatch reports 3.4T tokens run, window unstated) — and with no
family to inherit standing from, this summary is all the fit judgment there is.

**thinkingmachines/inkling-2-small.** Thinking Machines Lab's second-generation
open-weight model — Inkling 2 Small, a 594B-total/17B-active multimodal (text+image)
MoE reasoning model with variable effort, launched 2026-11-05 — is free on OpenCode as
`opencode/inkling-2-small-free` and as `thinkingmachines/inkling-2-small:free` on
OpenRouter, both at 1,048,576 ctx (https://thinkingmachines.ai/news/inkling-2-small/;
https://opencode.ai/inference/v1/models; https://openrouter.ai/api/v1/models, fetched
2026-11-15; free-window announcement dated 2026-11-07,
https://blockchain.news/ainews/inkling-2-small-free-on-opencode-limited-time-access).
Pick it for cost-free reasoning/agentic work needing images in context while the windows
last — the catalog's AA row reads intelligence 30.6 with coding/agentic null, reasoning
mandatory at default effort `high` (2026-11-15 fetch). What changes the decision:
documented retention with possible training use ("retains your data and may use it for
model training" → `trains`, https://opencode.ai/v2/docs/console/models), a hard geo-block
covering the EU, Iceland, Norway, Liechtenstein and sanctioned states (same URL; TML's
free-tier terms and privacy notice govern upstream,
https://thinkingmachines.ai/legal/tml-free-research-api-tier-terms-of-service.pdf), no
published end date or rate limits on either platform, and no benchmark rows on the
OpenCode lane itself.

**meituan/longcat-2.5.** Meituan's LongCat 2.5 — an agent-autonomy-focused multimodal
MoE sequel to LongCat 2.0, vendor preview specs ~1.6T total / ~48B active (not
independently reproduced; technical report pending as of the 2026-09-27 write-up),
listed by OpenCode with canonical id `meituan/longcat-2.5`, release_date 2026-11-02, at
1,000,000 ctx (https://opencode.ai/inference/v1/models;
https://www.explainx.ai/blog/longcat-2-5-1-6-trillion-agent-model-2026;
https://www.orcarouter.ai/blog/longcat-2-5, all context as of 2026-11-15). Exposure is
documented `no-retention` — "zero-retention … does not use your data for model training"
and "not used for training or retained" — but the route is **hosted in China** and capped
at **100 requests per day** (https://opencode.ai/v2/docs/console/models, fetched
2026-11-15). Pick it for patient cost-free agentic/coding loops with image input inside
OpenCode; the daily cap rules out high-volume agent rings, China hosting may fail company
policy regardless of the promise, OpenCode marks it not-open-weights (contradicting an
"expected to follow 2.0's MIT" third-party expectation, unresolved), and as of 2026-11-15
there is no OpenRouter row, no benchmark coverage, and no community signal for 2.5 —
vendor framing only.