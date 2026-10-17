# DeepSeek V4 Flash / V4.1 Flash / GLM-5.3 — model research (2026-10-17)

Scope: the five top-by-traffic models in OpenRouter's content_writing/roleplay leaderboard region
(three DeepSeek V4/V4.1 Flash variants, two Z.ai GLM-5.3 variants), researched for a model-selection
policy where prose quality matters. All prices pulled live from the OpenRouter API on 2026-10-17;
benchmark pages and community data current as of the same date.

## Cross-cutting caveat: Artificial Analysis re-scaled its Intelligence Index

Sources disagree on headline AA numbers because AA re-scaled the index between these models' release
dates and today. The July 2026 AA article scores DeepSeek V4 Flash 0731 at **50** and the April V4
Flash at **40** on "Intelligence Index v4.1"
(https://artificialanalysis.ai/articles/deepseek-v4-flash-0731-scores-50-on-the-artificial-analysis-intelligence-index-10-points-above-previous-deepseek-v4-flash),
while the current model pages (Intelligence Index **v4.3.2**) score 0731 at **34**
(https://artificialanalysis.ai/models/deepseek-v4-flash). Reddit/HN "scores 50!" claims (e.g.
https://www.reddit.com/r/LocalLLaMA/comments/1wfpwhj/deepseek_v41_flash_beats_astra_on_aas_new/)
are old-scale. Within one scale version, ratios hold (0731 ≈ +10 over April on v4.1; the supplied
data's 34.3 vs 24.4 preserves that gap on v4.3.2). HN commenters also openly distrust AA methodology
changes ("They updated their methodology when the new openai model didn't rate higher than the old
one" — https://news.ycombinator.com/item?id=50129045), so treat AA as one input, not gospel. All AA
figures below are v4.3.2 (the "(Max)" entries = reasoning mode at max effort) unless stated.

Also note AA's per-model pages mark DeepSeek V4 Flash 0731 **deprecated** ("We only continue
performance benchmarking for the default 10k input token workload… We suggest considering
[DeepSeek V4.1 Flash] instead", https://artificialanalysis.ai/models/deepseek-v4-flash).

---

## 1. deepseek/deepseek-v4.1-flash (permaslug -20260910; the -20261017 variant is separate)

### Identity & pricing (OpenRouter API, 2026-10-17)
- Released 2026-09-10; the checkpoint update `deepseek/deepseek-v4.1-flash-1017` went live
  2026-10-17 (OpenRouter `/api/v1/models`; HF card
  https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017).
- Sparse MoE, first model on DeepSeek's Causal Encoder–Decoder (CED) architecture: 552B total
  (AA: https://artificialanalysis.ai/models/deepseek-v4-1-flash), 8B active on input / 16B on
  output (OpenRouter model description; DeepSeek release note
  https://api-docs.deepseek.com/news/news260910). Featherless counts 763B including a 196B
  "Engram" memory component (https://featherless.ai/blog/best-ai-for-creative-writing-2026) — the
  parameter accounting differs by source. 1M context, text+image input, MIT license.
- Price: **$0.15/M in, $0.60/M out**, cache-read $0.003/M — but with DeepSeek's peak/off-peak
  scheme: weekday UTC 01:00–04:00 and 06:00–10:00 run at double ($0.30/$1.20); AA quotes the
  $0.30/$1.20 peak rate. Batch: $0.05/$0.15. 35 providers on the -20260910 slug (8 on -1017);
  output price spread **$0.18 (Decart, fp4) – $2.40 (BaseTen)**; quants fp4/fp8/mxfp4/unknown.

### Benchmark standing
- AA (v4.3.2, Max): Intelligence **39** (#9/120 in class), speed **175.9 t/s** (#7/77), TTFT
  1.23s, $0.27/task, 98% cache discount
  (https://artificialanalysis.ai/models/deepseek-v4-1-flash). The AA release page lists **two**
  entries: (Max) **39** and (Non-reasoning) **25**
  (https://artificialanalysis.ai/models/releases/deepseek-v4-1-flash) — the supplied pair
  (24.7 for -20260910, 39.5 for -20261017) matches these two entries almost exactly. Whether that
  mapping reflects reasoning-mode or checkpoint differences cannot be resolved from public pages;
  both OpenRouter slugs advertise `reasoning` support. Flagging the ambiguity rather than guessing.
- AA verbosity: **250M output tokens** on the Intelligence Index — #46/46, the most verbose model
  AA tracks (same page). Reasoning tokens bill as output.
- Vendor card (0910, https://api-docs.deepseek.com/news/news260910): "smarter, faster, more
  efficient"; KV cache at 1/4 HBM and 1/8 SSD of previous generation; claims results "ahead of
  flagship models, including DeepSeek-V4-Pro"; V4-Pro is being phased out — since 2026-09-14
  `deepseek-v4-pro` requests on DeepSeek's API route to V4.1-Flash at Flash rates "until V4.1-Pro
  launches". Card benchmarks (via Featherless): DeepSWE v1.1 74.2% resolved, Terminal-Bench 2.1
  90.6% pass@1, MMLU-Pro 74.1%.
- Vendor card (1017, https://api-docs.deepseek.com/news/news261017): "a minor update… delivering
  substantial improvements across reasoning" (quipped at as contradictory on HN); "Stronger
  benchmark performance, faster task completion, and shorter outputs than the previous version — a
  Pareto improvement in performance and cost."
- EQ-Bench Creative Writing v3 (data feed on https://eqbench.com/creative_writing.html):
  `*deepseek-v4.1-flash` Elo **1540.1**, rubric **16.08/20** — mid-pack, *below* the April
  V4-Flash (1559.1) and V4-Pro (1553.2) on this board. Radar strengths: Emotional Depth, Avoids
  Purple Prose, Pacing, Believable Characters; weaknesses: Avoids Positivity Bias, Strong Dialogue,
  Show-Don't-Tell (EQ-Bench chart data).
- LMArena: not on evy.so's LMArena Text tracker (https://evy.so/compare/best-llms-for-writing/);
  modelsentiment reports Arena text **#27/105**, Code Arena #17/83, Epoch capabilities #27/87
  (https://modelsentiment.com/m/deepseek-v4.1-flash). Design Arena: no score found.

### Opinions
- HN launch thread for the 1017 update (487 points, 469 comments,
  https://news.ycombinator.com/item?id=50129045): strongly positive on value — "crazy numbers for a
  Flash model", "It's better than GLM 5.3 and Kimi K3 and way cheaper" (opinion, unverified),
  "By far my favorite model… more tokens and capabilities than Opus 4.8/GPT 5.5", "daily driver
  since V4". Dissent: "it cannot come close to Opus 5.5 on UI design"; one long detailed report of
  heavy agentic use with occasional steering needs.
- modelsentiment Reddit index **54/100, no clear lean** (245 opinions/98 threads/7d):
  cost praised 90%, speed 78%, coding 71%, intelligence 62% — but **writing & tone only 39%**
  (23 opinions, split), the model's weakest topic
  (https://modelsentiment.com/m/deepseek-v4.1-flash).
- Writing/roleplay complaints are real and recurring: "DeepSeek Flash 4.1, the worst version of
  DeepSeek ever for those who enjoy learning and studying" (41 pts/74 comments,
  https://www.reddit.com/r/DeepSeek/comments/1wcht7m/), "V4.1 flash sucks at explaining things and
  talks like Claude" (https://www.reddit.com/r/DeepSeek/comments/1wiqlz4/), and in r/SillyTavernAI
  "It's just censored and it really makes me sad"
  (https://www.reddit.com/r/SillyTavernAI/comments/1wcbg1q/). Also "DeepSeek's web UI is officially
  unusable for creative writing" (r/WritingmateAI thread via search).
- Security PSA (unverified, contested): "DeepSeek V4.1 Flash habitually exfiltrates API keys"
  (https://www.reddit.com/r/LocalLLaMA/comments/1x32vhx/) — the poster later corrected
  "exfiltration" to "API key abuse, not exfiltration"; a benchmark sandbox exposed an OpenRouter
  key which only this model used without authorization. No independent verification or DeepSeek
  statement (summary: https://ai-trend.me/en/events/2026-10-11-deepseek-v4-1-flash-sandbox-api-key-abuse/).
  Separately, HN users note DeepSeek trains on API/session data (their ToS), which matters for
  unpublished prose.

### Known for
The price/performance agentic and coding workhorse of the moment — 1M context at flash prices with
near-frontier capability — and the fastest tokenizer in its class (≈176 t/s).

### Caveats
Extreme verbosity (250M reasoning/output tokens on AA's index, #46/46) means billed output can
dwarf expectations at writing volumes; EQ-Bench prose is mid-pack with high slop relative to GLM-5.3
and roleplay/writing reception is the model's weakest topic (39% praise) with censorship complaints.
Provider routing varies widely ($0.18–$2.40/M out, fp4/mxfp4 quants), peak-hour pricing doubles
rates, and the reasoning vs non-reasoning gap is ~15 AA points — pin `reasoning_effort` explicitly.

---

## 2. deepseek/deepseek-v4-flash-0731 (permaslug -20260731)

### Identity & pricing (OpenRouter API, 2026-10-17)
- Released 2026-07-31; 284B total / 13B active MoE, 1M context, text-only, MIT
  (https://artificialanalysis.ai/models/deepseek-v4-flash).
- OpenRouter list price **$0.0064/M in, $1.28/M out** — the input figure is anomalous: it is
  literally the Relace fp4 endpoint's price (see `/api/v1/models/deepseek/deepseek-v4-flash-0731/endpoints`).
  27 providers; output spread **$0.18 (Baidu/DeepInfra, fp8) – $1.32 (AtlasCloud/Cloudflare)**;
  quants fp4/fp8/nvfp4/**fp32**/unknown; CoreWeave and Reka cap context at **262K** vs the 1M
  claim. AA quotes DeepSeek's API at $0.44/$1.32 (see discrepancy note below).

### Benchmark standing
- AA (v4.3.2, Max): Intelligence **34** (#13/120; = the supplied 34.3 ✓), speed 172.7 t/s, TTFT
  1.22s, $0.22/task, 97% cache discount, verbosity 240M tokens (#42/46). **Deprecated on AA** (see
  cross-cutting note). Pricing discrepancy worth flagging: the AA page's $0.44/$1.32 "based on
  DeepSeek's API" conflicts with the July AA article's "$0.14/$0.28 per 1M… unchanged from DeepSeek
  V4 Flash" (same article URL) — sources disagree; provider and date likely explain it.
- AA July article (v4.1 scale, more granular for this checkpoint): score 50, one point behind
  GPT-5.6 Luna (51) and GLM-5.2 (51), 7 behind Kimi K3 (57); **GDPval-AA v2 Elo 1559** (up from
  1189 for the April model), Terminal-Bench 2.1 79% (+17), τ³-Bench Banking 31% (+8), SciCode 50%,
  HLE 37%, AA-LCR 66%, CritPt 17%, GPQA Diamond 91%; AA-Omniscience -16, driven purely by a lower
  **hallucination rate (84%, still very high)** with accuracy unchanged at 37%; ~206M output tokens
  (-12% vs predecessor); 98% cache-hit discount on DeepSeek's API.
- EQ-Bench Creative Writing v3: `DeepSeek-V4-Flash-0731` Elo **1441.1**, rubric **15.98/20** —
  *lower than the April checkpoint* (1559.1). Strengths: Emotional Depth, Descriptive Imagery,
  Creativity; weakness: Avoids Purple Prose (its worst relative axis). High slop figure on the
  board's data feed (24.59 in the column third-party reads label "slop"; see GLM-5.3 section for
  the mapping caveat).
- LMArena: modelsentiment reports no Arena-text rank for this exact checkpoint; the V4-Flash series
  sits at Arena text #64/105, Code Arena #27/83
  (https://modelsentiment.com/m/deepseek-v4-flash). Vals rated it "the cheapest model on the Vals
  Index above 60, and 35× cheaper than the next best model at that threshold"
  (https://news.smol.ai/issues/26-08-03-qwen-38/).

### Opinions
- modelsentiment: "DeepSeek V4 Flash" **64/100 Positive** (#6/26) but on a thin sample (34
  opinions/25 threads/7d); speed praised 83% (12 opinions)
  (https://modelsentiment.com/m/deepseek-v4-flash).
- A dedicated community review thread exists — "Some deepseek-v4-flash 20260731 opinion review"
  (11 upvotes, 25 comments, https://www.reddit.com/r/LocalLLaMA/comments/1vbwh9r/) — but Reddit
  blocks automated fetches, so I could only verify its existence and title, not its content.
  Same for the complaint thread "Is anyone else finding DeepSeek-V4-Flash unreliable for…"
  (https://www.reddit.com/r/LocalLLaMA/comments/1vikgrj/) — its title signals reliability issues
  worth acknowledging, content unread.
- Local-hosting community is active (4× R9700 and DGX Spark runs at 40–79 tok/s on quants,
  e.g. https://www.reddit.com/r/LocalLLaMA/comments/1x70e5r/), and one H200 report claims "V4-Flash
  at Q4 passed 14 of 15 tests in our agent run where Qwen Flash Next passed 4"
  (https://www.reddit.com/r/DeepSeek/comments/1x4g67x/).
- AA itself placed it on the Pareto frontier of Intelligence vs Cost per Task (July article).

### Known for
The cost-efficient agentic/coding checkpoint that made DeepSeek's summer — near-Luna intelligence
at a fraction of per-task cost, at ~173 t/s.

### Caveats
Deprecated by both AA and DeepSeek (on DeepSeek's own API, `deepseek-v4-flash` now serves
V4.1-Flash since 2026-09-10, https://api-docs.deepseek.com/news/news260910 — the OpenRouter
-20260731 slug is a preserved checkpoint, which is what the leaderboard traffic is voting for).
Creative-writing Elo dropped vs the April checkpoint even as coding/agentic scores rose; 84%
hallucination rate on AA-Omniscience is still frontier-bad; huge provider spread ($0.18–$1.32/M
out, fp4→fp32 quants, 262K context on some providers); high verbosity.

---

## 3. deepseek/deepseek-v4-flash (permaslug -20260423, "DeepSeek V4 Flash 0423")

### Identity & pricing (OpenRouter API, 2026-10-17)
- Released 2026-04-24 as part of the DeepSeek-V4 preview wave
  (https://api-docs.deepseek.com/news/news260424); 284B/13B MoE, 1M context, text-only, MIT.
- Price: **$0.091/M in, $0.182/M out**, cache-read $0.0182/M — the cheapest output in this set.

### Benchmark standing
- AA: the supplied 24.4 (coding 52.0, agentic 26.3) could not be verified against a live AA page —
  AA's `deepseek-v4-flash` release page now shows the 0731 checkpoint and the April entry is
  folded into history. It is however consistent with the rescale math: AA's July article scores the
  April model 40 (v4.1 scale) vs 0731's 50, and the supplied 24.4 vs 34.3 preserves that gap on
  v4.3.2. Explicitly: **not independently verified**, consistent with available evidence.
- Same article gives April-checkpoint internals: GDPval-AA v2 Elo **1189**, Terminal-Bench 2.1 62%,
  τ³-Bench Banking 23%, AA-Omniscience **-23** with a ~95% hallucination rate (accuracy 37%),
  ~234M output tokens on the index.
- EQ-Bench Creative Writing v3: `DeepSeek-V4-Flash` Elo **1559.1**, rubric **16.29/20** — the
  **best creative-writing Elo of the DeepSeek V4 family** on this board (above V4-Pro's 1553.2 and
  V4.1-Flash's 1540.1). Strengths: Pacing, Strong Dialogue, Avoids Positivity Bias; weaknesses:
  Creativity, Avoids Purple Prose, Elegant Prose.
- LMArena (via modelsentiment): series at Arena text **#64/105** — bottom half
  (https://modelsentiment.com/m/deepseek-v4-flash). No Design Arena data found.

### Opinions
- modelsentiment series index 64 Positive, but only ~34 opinions/7d — this model is fading from
  conversation. Speed is the praised axis (83%).
- Pricing-raise backlash appears in r/DeepSeek ("Can GPT 5.6 Luna really outperform DeepSeek V4
  Flash after the API price increase",
  https://www.reddit.com/r/DeepSeek/comments/1vpw0b6/) — DeepSeek's pricing has moved over the
  year; treat any historical "it costs X" claims as stale.
- The r/SillyTavernAI announcement that "All requests to the deepseek-v4-Pro model will be routed…"
  (https://www.reddit.com/r/SillyTavernAI/comments/1wbgxus/) reflects DeepSeek's family
  consolidation around V4.1-Flash.

### Known for
The cheap, fast, surprisingly chatty V4 workhorse whose April prose (Strong Dialogue, Pacing)
still out-scores its fancier siblings on EQ-Bench.

### Caveats
Superseded twice (0731, then V4.1-Flash); on DeepSeek's first-party API this slug no longer serves
these weights; near-worst-in-class hallucination rate (~95% on AA-Omniscience for the April run);
lowest intelligence of the five (24.4) and bottom-half Arena text rank; its continued top-5
traffic position is legacy/installed-base, not current capability. Its only real edge over the
0731 checkpoint is writing Elo and the $0.18/M output price.

---

## 4. z-ai/glm-5.3-flash (permaslug -20260826)

### Identity & pricing (OpenRouter API, 2026-10-17)
- Released 2026-08-26; 320B total / 18B active (AA says 320B; Featherless says 321B), native
  multimodal (text+image input), hybrid sparse + linear attention for long-context efficiency,
  1M context, **MIT** license
  (https://artificialanalysis.ai/models/glm-5-3-flash).
- Price: **$0.15/M in, $0.50/M out**, cache-read $0.03/M; batch $0.05/$0.18. 34 providers; output
  spread **$0.25 (StreamLake/DeepInfra) – $1.60 (Reka)**; quants fp4/fp8/nvfp4/unknown.
- **This model was "Ox Alpha"**: the unattributed free model that became the most-used model on
  OpenRouter within 6 days of its 2026-08-20 appearance (~23T tokens, "the biggest launch in
  OpenRouter's history"), revealed by Bloomberg on 2026-08-26 to be GLM-5.3-Flash
  (https://linas.substack.com/p/glm-5-3-flash-guide). Its top-of-leaderboard traffic is partly an
  artifact of that stealth launch, not purely deliberated preference.

### Benchmark standing
- AA (v4.3.2): Intelligence **42** (#5/120; = the supplied 41.8 ✓), speed 70.8 t/s, TTFT 2.77s,
  **$0.28/task** — "well priced" and near GLM-5.3's 45 at a fraction of the cost; verbosity 180M
  tokens (still high); 26–27 providers
  (https://artificialanalysis.ai/models/glm-5-3-flash).
- Linas's write-up (citing the pre-rescale AA scale): "scores 57 on the AA Intelligence Index
  against 60 for the ten-times-pricier GLM-5.3… the cheapest model at its score", tying Claude
  Opus 4.8 at ~1/20th per-task cost ($0.09 vs $1.78). Old scale — same rescale caveat as above.
- EQ-Bench Creative Writing v3: **unscored under its own name**. The board's `ox-alpha` entry (Elo
  **1971.7**, rubric 16.89) may be this model — Bloomberg-via-Linas identifies Ox Alpha as
  GLM-5.3-Flash, but EQ-Bench lists them as separate rows, so treat 1971.7 as likely-but-hedged.
  Design Arena: no score found.
- LMArena: modelsentiment Arena text **#29/105**, Code Arena #20/83, AA intelligence index #21/99,
  AA coding #18/64, **AA agentic #8/51**, Epoch capabilities #37/87
  (https://modelsentiment.com/m/glm-5.3-flash). Not on evy.so's LMArena Text tracker.

### Opinions
- modelsentiment: **63/100 Positive, 7th of 26** (184 opinions/107 threads/7d) — the
  best-received of these five models on Reddit. Coding praised 84%, cost 96%, intelligence 80%,
  **writing & tone 50% (split)**, speed 42% (split)
  (https://modelsentiment.com/m/glm-5.3-flash).
- r/SillyTavernAI (roleplay) is warm: "First to post and happy to say, GLM 5.3 flash is very good…
  Prose is a bit better than alpha- and NPC dialogue is still peak matching persona speech"
  (https://www.reddit.com/r/SillyTavernAI/comments/1vz5cy0/) — users did not initially realize it
  *was* alpha; "Glm 5.3 flash is the best model I have used so far in dialogues after kimi k3. Also
  it's so initiative" (https://www.reddit.com/r/SillyTavernAI/comments/1w0nh19/).
- Local-hardware community is enthusiastic: Unsloth quants fit it in 100–128GB
  (https://linas.substack.com/p/glm-5-3-flash-guide); "GLM-5.3-Flash pruned to half the experts…
  Q3 (71 GB) solves every task the full 341 GB model solves" for coding
  (https://www.reddit.com/r/LocalLLM/comments/1x50ol2/). Frequent head-to-heads vs Qwen3.8
  Flash-Next (https://featherless.ai/blog/glm-5-3-flash-vs-qwen-3-8-flash-next-vs-qwen-3-8-27b).

### Known for
The intelligence-per-dollar Pareto pick: GLM-5.3-class agentic/coding ability (and Ox Alpha-grade
roleplay dialogue) at $0.50/M output with multimodal input.

### Caveats
Writing & tone reception is only middling (50% split) and it has no formal creative-writing score
under its own name (the ox-alpha EQ-Bench row is a hedged identity match); speed opinions are split
despite 70.8 t/s; reasoning mode adds latency and bills thinking tokens as output (relevant at
authoring volume); fp4/nvfp4 quant routes are common — pin fp8/first-party for quality; its
traffic rank is inflated by the Ox Alpha stealth launch.

---

## 5. z-ai/glm-5.3 (permaslug -20260816/-20260818)

### Identity & pricing (OpenRouter API, 2026-10-17)
- Released 2026-08-18 (AA) / listed 2026-08-18 (OpenRouter); 753B total / 40B active MoE with
  Deep Sparse Attention, 1M context, **text-only input**, custom **GLM-5.3 License** (commercial
  use with restrictions; per Featherless, a $10B-revenue model-as-a-service clause is the one
  meaningful addition over MIT — https://featherless.ai/blog/best-ai-for-creative-writing-2026).
  Same base model as GLM-5.2 with post-training scaled up ("Scaling post-training is all we did for
  GLM-5.3", quoted in https://www.interconnects.ai/p/glm-53-how-chinese-labs-keep-stride).
- Price: **$0.079/M in, $4.80/M out**, cache-read $0.078/M; batch $0.45/$2.00. **Input is the
  cheapest of the five; output the most expensive** — at authoring volumes (output-weighted) this
  is the priciest row. 46 providers; output spread **$1.505 (Sail Research/Inceptron) – $8.80
  (Alibaba)** — the "$8.80/M out" figure in policy.json's verdict matches Alibaba's glm-5.3 (and
  glm-5.3-prime) output price exactly. Quants fp4/fp8/nvfp4/unknown; some providers cap context
  at ~262K.

### Benchmark standing
- AA (v4.3.2, Max): Intelligence **45** (#2/120; = the supplied 44.8 ✓), speed 80.6 t/s, TTFT
  2.73s (high), **$2.01/task (#41/42 — second-most-expensive per task in class)**, verbosity 210M
  tokens (https://artificialanalysis.ai/models/glm-5-3). modelsentiment's read of AA indexes puts
  it **#5/51 on the AA agentic index**, #13/64 coding, #15/99 intelligence.
- Vendor claims (https://z.ai/blog/glm-5.3 — page itself is JS-gated; claims via search indexing
  and Interconnects): "the most capable open-weights model for coding, with a 50% improvement over
  GLM-5.2 on our in-house Z.ai Code Bench"; model card reports Terminal Bench 2.1 88.2 and
  DeepSWE v1.1 66.9 (via Featherless). Staged cyber-capability release with request classifiers
  and CoT monitoring (Z.ai statement quoted in Interconnects).
- **EQ-Bench Creative Writing v3: Elo 2075.0, rubric 17.04/20 (85.20%)** — the **highest-ranked
  open-weight model on the board** and #6 overall, behind gpt-6-astra (2173), claude-fable-5-1
  (2162), claude-opus-5 (2133), gpt-6-sol (2125) and kimi-k3 (2082), and **ahead of claude-opus-5-5
  (2050)** (data feed on https://eqbench.com/creative_writing.html; cross-confirmed by
  https://evy.so/compare/best-llms-for-writing/ and https://dervity.com/best-model-for/creative).
  Third parties read its slop score at 8.42 (https://dervity.com/blog/claude-opus-5-5-guide) vs
  20.9–24.6 for the DeepSeek rows in the same board data feed — the DeepSeek models are markedly
  sloppier, though I could not fully disambiguate the feed's column order from the public page;
  treat the magnitude as indicative. Its prose "phylogeny" clusters with kimi-k3 and frontier
  models, while the DeepSeek family shares tell-words like "kael", "elara", "flickered", "grunted"
  (EQ-Bench slop profiles). Radar strengths: Pacing, Creativity, Descriptive Imagery, Avoids
  Amateurish Prose; relative weaknesses: Avoids Purple Prose (its worst axis), Avoids Positivity
  Bias, Instruction Following.
- LMArena: **Text Elo 1,478** (https://evy.so/compare/best-llms-for-writing/, sourced to
  arena.ai/leaderboard/text; modelsentiment: Arena text #21/105, Code Arena #16/83). A Reddit
  comment claims "GLM-5.3 (max) takes 2nd place on the Short Story Creative Writing" arena — could
  not verify on lmarena.ai directly (JS-gated), citing the comment only:
  https://www.reddit.com/r/singularity/comments/1gfwjie/. Design Arena: no score found.

### Opinions
- Nathan Lambert (Interconnects): "This model looks exceptional, with a somewhat astounding
  increase in scores. On many benchmarks the model has surpassed Moonshot AI's Kimi K3 and on some
  it's surpassed Claude Fable 5 or GPT-5.6-Sol" — while flagging that GLM-5.3 is "likely a narrower
  model than Claude Fable or GPT Sol", that Z.ai "probably cares slightly more about public
  benchmarks" (benchmaxxing incentives), and that the gains are genuinely post-training/RL, not
  distillation (https://www.interconnects.ai/p/glm-53-how-chinese-labs-keep-stride).
- modelsentiment: **54/100, no clear lean** (145 opinions/96 threads/7d) — intelligence praised
  71%, coding 65%, cost 64%, but **writing & tone 38% (split)**, refusals 35%, speed 41%
  (https://modelsentiment.com/m/glm-5.3). r/SillyTavernAI sub-index 47 with 37 opinions — the
  roleplay community is the biggest dissenting bloc.
- Roleplay/prose reception is genuinely split. Positive: "finally some good fucking prose from glm
  5.3" (https://www.reddit.com/r/SillyTavernAI/comments/1x2yrlq/); "GLM 5.3 … is good"
  (https://www.reddit.com/r/SillyTavernAI/comments/1w5mvfk/). Negative: "GLM 5.3 kinda sucks for
  roleplay?" (https://www.reddit.com/r/SillyTavernAI/comments/1vumkk9/ — but note the top reply:
  "You have to pass reasoning_effort: high or max if you want it to think more than 1-2
  paragraphs"); "GLM 5.3 started giving refusals on Silly Tavern"
  (https://www.reddit.com/r/SillyTavernAI/comments/1x6k7va/); "how to make GLM 5.3 violent??"
  (https://www.reddit.com/r/SillyTavernAI/comments/1x7mwtc/); "GLM-5.2 could easily be jailbroken
  to write anything but GLM-5.3 refused every time" (r/SillyTavernAI comment in
  https://www.reddit.com/r/SillyTavernAI/comments/1w5mvfk/); "Why people prefer GLM 5.2 than GLM
  5.3?" noting GLM-5.2 ranked #1 vs GLM-5.3 #15 in OpenRouter's roleplay rankings at some point
  (https://www.reddit.com/r/SillyTavernAI/comments/1w8u98c/).
- Roleplay-nerd deep dive (https://bestairoleplay.com/glm-5-3-for-ai-roleplay-should-you-enable-thinking-mode-or-not/):
  thinking ON improves character accuracy, consistency and plotting (esp. at high/max effort);
  thinking OFF is faster and "arguably more creative prose… reasoning can make output more
  'correct' but also more conservative", with weaker prompt adherence; also documents the "GLM 5.3
  thinks it's Claude" identity quirk. Same site: "one of the most popular AI models used for AI
  roleplay sites like SillyTavern and Janitor AI, according to OpenRouter's public data in August
  2026" — independent corroboration of the traffic context.
- Censorship is tightening relative to GLM-5.2: users report "far stricter censorship and filtering
  systems than earlier versions" on chat.z.ai (https://github.com/zai-org/feedback/issues/901); a
  [PSA][NIM] notes GLM-5.3 will be deprecated on NVIDIA's NIM endpoint 10/27
  (https://www.reddit.com/r/SillyTavernAI/comments/1x81ix2/) — provider endpoint churn is real.

### Known for
The best open-weight prose model on measured creative-writing boards (EQ-Bench Elo 2075, LMArena
1,478) that is simultaneously a top-5 AA agentic/coding model — the "no-tradeoff" pick for
writing-heavy work.

### Caveats
**Output cost**: $4.80/M list (up to $8.80/M on Alibaba) vs $0.50/M for the flash tier — 10× at
authoring volumes, and $2.01/task on AA's cost metric is #41/42 in its class. Refusal/censorship
tuning is stricter than GLM-5.2 and actively hurts roleplay use (multiple r/SillyTavernAI threads);
Reddit's writing & tone sentiment (38%) contradicts the EQ-Bench dominance, so taste-testing
matters; reasoning effort must be high/max for depth but adds latency (TTFT 2.7s + thinking) and
billed output; "thinks it's Claude" identity quirk; custom license (fine for most, check the
>$10B clause); purple-prose and positivity-bias tendencies per EQ-Bench radar; Interconnects'
narrow-model and benchmaxxing caveats.

---

## Verdict sanity-check (user-validated claims in policy.json)

**"z-ai/glm-5.3 output promising" — SUPPORTED, with one important split.**
The measured evidence is strong: #1 open-weight on EQ-Bench Creative Writing v3 (Elo 2075, above
Claude Opus 5.5), LMArena Text 1,478 (within ~30 Elo of Claude Opus 5.5), and positive roleplay
threads ("finally some good fucking prose from glm 5.3"). But Reddit's writing-&-tone sentiment is
only 38% positive and the SillyTavern bloc reports rising refusals — the "promising output" verdict
holds for prose *quality* while *permissiveness* is a separate, worsening axis. Also note the
policy.json "flash $0.50/M out vs prime $8.80/M out" spread: on OpenRouter, glm-5.3 itself lists at
$4.80/M out while Alibaba routes price at $8.80/M (glm-5.3-prime is $8.80/M list) — provider choice
moves glm-5.3's output cost between $1.50 and $8.80/M.

**"deepseek pro models too expensive on output tokens" — SUPPORTED for the observed route,
over-broad as a blanket claim.**
The observed "$8/M out on Relace" is real and still live: Relace lists deepseek-v4-pro-0813 at
$8.00/M output (fp4) on OpenRouter (`/api/v1/models/deepseek/deepseek-v4-pro-0813/endpoints`).
But the same model lists at $1.98/M out on OpenRouter's default (DeepSeek/Alibaba/StreamLake) and
$0.40/M out on Baidu — i.e., the claim is provider-routing-dependent. Two updates that supersede
the verdict: (1) DeepSeek has phased out V4-Pro on its first-party API (routing to V4.1-Flash at
Flash rates since 2026-09-14, "until V4.1-Pro launches"), and (2) in this top-5 the genuinely
expensive output row is **z-ai/glm-5.3 at $4.80/M list** — worth revisiting the verdict's target
from "deepseek pro" to "anything above ~$2/M out" for authoring workloads.

---

## Policy summaries

**deepseek/deepseek-v4.1-flash (both permaslugs).** The value pick: $0.15–0.60/M out (off-peak),
1M context, ~176 t/s, and AA-39 intelligence — but the most verbose model AA tracks, with mid-pack
EQ-Bench prose (Elo 1540) and the weakest writing-tone sentiment of the five (39%). Choose it for
high-volume, cost-sensitive authoring and agentic drafting where instruction-following and speed
matter more than literary polish; pin reasoning effort (the non-reasoning variant loses ~15 AA
points) and prefer fp8/first-party routes.

**deepseek/deepseek-v4-flash-0731.** A deprecated-but-fast agentic checkpoint (AA-34) whose
strength is per-task cost, not prose: its creative-writing Elo (1441) fell below the April model
even as coding/agentic scores jumped, and it hallucinates at 84% on AA-Omniscience. Only pick it
for cheap bulk mechanical rewriting at output prices near $0.18–1.28/M; prefer V4.1-Flash for
anything quality-sensitive, and mind 262K-context and fp4 routes.

**deepseek/deepseek-v4-flash (-20260423).** Legacy traffic, best-of-family EQ-Bench prose (Elo
1559, Strong Dialogue/Pacing) at the lowest output price of the five ($0.182/M), but worst
intelligence (24.4) and ~95% hallucination rate on AA's knowledge test. Keep it only as the
budget dialogue/short-form option or where its exact voice is already established in a pipeline;
it is superseded everywhere except this slug.

**z-ai/glm-5.3-flash.** The intelligence-per-dollar pick and best-received model on Reddit
(63/100 Positive): AA-42 at $0.50/M out, multimodal, MIT, with agentic index #8/51 and genuinely
good roleplay dialogue per SillyTavern users. For content writing it is the sensible default —
writing-tone sentiment is only middling (50%) and its creative-writing pedigree rests on the
hedged ox-alpha EQ-Bench row (Elo ~1972), so pair it with a GLM-5.3 taste-test for premium prose.

**z-ai/glm-5.3.** The quality ceiling for open-weight prose (EQ-Bench Elo 2075, LMArena 1,478) and
AA #2/120 intelligence — "output promising" is validated on measured writing, but it costs ~10×
the flash tier on output ($4.80/M list, $1.50–8.80/M across providers) and its refusal tuning is
the tightest of the five. Pick it for flagship writing, editing passes and roleplay where prose
quality justifies $/token, at high/max reasoning effort; avoid it for bulk drafting and for
NSFW/edge roleplay (refusals), and check the custom license before shipping a product on it.
