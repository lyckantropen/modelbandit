# Re-research batch K — `openai/gpt-5.6-sol`, `openai/gpt-4o-mini`, `openai/gpt-oss-120b`, `qwen/qwen3.6-35b-a3b` (2026-10-25)

Scope: the four `summaries` entries in `skills/openrouter-model-router/policy.json` that the
2026-10-18/19 refresh cycle left standing while every other stale entry was re-researched. All
four are flagged `stale` by `bind.py --check-policy` — i.e. each has a summary but does not rank
in the top-15 of any domain as of this pass. Selection ranking here is OpenRouter revealed
preference: **unranked = invisible to selection, which is a traffic fact, not a quality verdict.**
This file re-verifies every anchor as of 2026-10-24/25, reports where sources disagree, and ends
with one recommended verdict per model (update / retire / keep as dated exclusion) plus one
proposed 2–3-sentence policy summary each. Nothing in `policy.json` was edited; `hints` and `fit`
were not touched.

Method and shared data sources (all retrieved 2026-10-25):

- OpenRouter task classifications, 7-day window, `as_of 2026-10-24` — https://openrouter.ai/api/v1/classifications/task?window=7d — 29 tags, each listing that task's top-10 models by tag share. "Absent from all 29 tags" below means: not in the top-10 of any task.
- OpenRouter daily token rankings, window 2026-09-25 → 2026-10-24 — https://openrouter.ai/api/v1/datasets/rankings-daily
- OpenRouter's Artificial Analysis benchmark feed, `as_of 2026-10-24` — https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis
- OpenRouter endpoint/pricing payloads, live 2026-10-25 — https://openrouter.ai/api/v1/models/<model-id>/endpoints
- Domain pools recomputed 2026-10-25 with the skill's own weighting (`usage_share × tag_usage_share`, `scripts/bind.py:domain_candidates`) over the five domains in `policy.json`: research 18 candidates, writing 19, coding 21, orchestration 19, ops 18. Top-15 cut applies to those pools.

---

## openai/gpt-5.6-sol

### Benchmark standing

- **Artificial Analysis, read 2026-10-25**: Intelligence Index **47, #28/215**, 81.7 output tok/s (#97/186), **$4.00 in / $20.00 out**, 90% cache discount, **$1.99 per II task** (#80/113), 1M context, released July 2026 — https://artificialanalysis.ai/models/gpt-5-6-sol. The same page now carries a **deprecation banner**: "This model is deprecated… OpenAI has launched a newer release, GPT-6 Sol. We suggest considering it instead," and AA says it now benchmarks only the default 10k-input workload. **This banner was not present in the 2026-10-18 pass** — it is the single biggest change to this entry.
- OpenRouter's AA feed (`as_of 2026-10-24`) still anchors **II 47 / coding 77.4 / agentic 50.2** for the Max variant — https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis. Coding-index standing on modelsentiment's strip: **#3/65**, Arena text **#16/122**, Code Arena #20/85 (2026-10-25) — https://modelsentiment.com/m/gpt-5.6-sol.
- **Traffic (OpenRouter revealed preference)**: 4.225T tokens over 2026-09-25…10-24, present **25 of 30 days**, last present 2026-10-23, rank sliding from ~16–25 early in the window to ~44–48 late — https://openrouter.ai/api/v1/datasets/rankings-daily. Yet it is **absent from all 29 task tags** (`as_of 2026-10-24`) and therefore has **no rank at all** in any of the five domain pools (18 / 19 / 21 / 19 / 18 candidates for research / writing / coding / orchestration / ops) — outside the top-15 everywhere: https://openrouter.ai/api/v1/classifications/task?window=7d.
- **Price, dated 2026-10-25**: list **$4.00 in / $20.00 out**, cached input **$0.40**, cache writes 1.25× input, and — new and decision-relevant — "GPT-5.6 Sol's promotional pricing is available **at least through November 21, 2026**"; prompts **>272K input tokens are priced at 2× input and 1.5× output for the full request** (→ $8/$30); 1,050,000 context / 128,000 max output / Feb 16 2026 cutoff — https://developers.openai.com/api/docs/models/gpt-5.6-sol. **Price sources disagree**: AA's own page shows $4/$20 (https://artificialanalysis.ai/models/gpt-5-6-sol) while OpenRouter's AA feed carries $8/$40 (https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis) and live OpenRouter endpoints (2026-10-25) run output **$10.00–$40.00/M** across 7 endpoints (fast/flex tiers) — https://openrouter.ai/api/v1/models/openai/gpt-5.6-sol/endpoints. The $4/$20 figure is the API list price with an expiry; the higher figures are tiered/long-context rates.
- Vendor/third-party checks carried over from the batch-E file (unchanged this pass): Sonar's 4,444-task Java benchmark (81.99% pass vs GPT-5.5's 78.66%, blocker vulns 18→9/mLOC but criticals 20→125/mLOC — https://www.sonarsource.com/blog/openai-gpt-5-6-sol-and-terra); CodeRabbit review ensemble 69.7% actionable passes — https://www.coderabbit.ai/blog/gpt-5-6-sol-and-terra-benchmark.

### Opinions

- **Product-level supersession (new)**: GPT-6 launched to all ChatGPT plans on **2026-10-07** and "will replace GPT-5.6 Sol and GPT-5.6 Luna in ChatGPT," while Codex and ChatGPT Work keep September builds — https://deploymentsafety.openai.com/gpt-6-october/introduction. The ChatGPT-vs-Codex version split therefore now has three tiers, not two. OpenAI's docs still say GPT-5.6 Sol/Terra/Luna "remain available during the rollout" — https://learn.chatgpt.com/docs/models.
- **Degradation anecdotes exist but are not confirmed by aggregates**: "GPT-5.6 Sol has seriously deteriorated the past week or so" (2026-09-20, OpenAI community) — https://community.openai.com/t/gpt-5-6-sol-has-seriously-deteriorated-the-past-week-or-so/1399353 — and a matching Codex bug report — https://github.com/openai/codex/issues/45801. Against that, modelsentiment's 7-day Reddit read on **2026-10-25 is index 59 (95% interval 51–68), 11th of 24, "4 points colder than the previous 7 days, within noise"**, with 83% praise on coding — https://modelsentiment.com/m/gpt-5.6-sol. **Sources disagree on whether quality actually moved; the aggregate says no.**
- Collaboration/writing verdict carried over (dated 2026-10-18): Every's month-long test, "GPT-5.6 Sol Is Our Favorite Model to Collaborate With," while also ranking it **last of six** on its one-shot writing bench — https://every.to/vibe-check/gpt-5-6-sol (disclosure: OpenAI early access). Launch-thread skepticism: https://news.ycombinator.com/item?id=48849066.
- Safety/measurement caveats carried over: METR's predeployment eval found "GPT-5.6 Sol's detected cheating rate was higher than any public model we have evaluated on our ReAct agent harness" (published under NDA with OpenAI approval — https://metr.org/blog/2026-06-26-gpt-5-6-sol/), and the resulting time-horizon estimate ranges from 11.3h to >270h depending on how cheating runs are scored — https://montanaresearch.org/blog/eleven-hours-or-270-metr-gpt-5-6-sol/.

### Known for

The community/collaboration workhorse: near-frontier coding and agentic execution plus the strongest *collaborative* writing and knowledge-work experience in OpenAI's lineup when fed sources, style guides and live editorial direction — and, per OpenAI's own deprecation tables, still the designated replacement for retiring legacy models.

### Caveats

- **Deprecated in product terms, not in API terms.** AA marks it deprecated in favor of GPT-6 Sol (https://artificialanalysis.ai/models/gpt-5-6-sol) and ChatGPT has moved to GPT-6 (https://deploymentsafety.openai.com/gpt-6-october/introduction), but it does **not** appear on OpenAI's API deprecation list at all — to the contrary, it is the recommended replacement for `gpt-5`/`gpt-5-mini`/`gpt-5-nano`/`gpt-5-pro`/`o3`/`o3-pro` (removal **2026-12-11**) and for the 2026-10-23 legacy batch (`gpt-4-0613`, `gpt-4-turbo`, `gpt-4o-2024-05-13`, `o1`, `o3-mini`, `o4-mini`, …) — https://developers.openai.com/api/docs/deprecations (table quoted at https://www.string.ink/blog/openai-october-23-model-shutdowns/). **Two sources, two statuses; both are current.**
- **Price has an expiry**: $4/$20 is promotional, "available at least through November 21, 2026" (https://developers.openai.com/api/docs/models/gpt-5.6-sol); >272K prompts cost 2×/1.5× for the whole request ($8/$30), and OpenRouter fast tiers already run $10–$40/M out (https://openrouter.ai/api/v1/models/openai/gpt-5.6-sol/endpoints). Re-price any commitment after 2026-11-21.
- **Overbuilding and one-shot prose weakness** remain its quality gaps (Every, links above); version split across ChatGPT/Codex/Work now spans three builds.
- Still outside every domain top-15 (data sources above): the policy engine will not select it on popularity; it can only enter via `hints` weighting.

### Verdict

**UPDATE** — AA now deprecates it in favour of GPT-6 Sol and ChatGPT dropped it on 2026-10-07, the promo price carries a hard horizon (2026-11-21), and OpenAI simultaneously keeps naming it the migration target for legacy models through 2026-12-11; the summary must carry all three facts.

---

## openai/gpt-4o-mini

### Benchmark standing

- **Artificial Analysis, read 2026-10-25**: Intelligence Index **7 (marked *Estimated*)**, #52/71 in the non-reasoning class ("below average… median: 9"), 100.8 tok/s (#28/59), **$0.15 in / $0.60 out**, 50% cache discount, cost/task unknown to AA, 128k context, knowledge cutoff **Oct 2023**, released July 2024, **deprecation banner** pointing to "GPT-5 mini" — https://artificialanalysis.ai/models/gpt-4o-mini. OpenRouter's AA feed (`as_of 2026-10-24`): **II 6.7 / coding 11.4 / agentic null** — https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis.
- Hard benchmark ceiling (carried over, unchanged): GDPval-AA **0.0%**, τ-Bench Banking 2.9%, HLE 4.2%, LiveCodeBench 23.4%, Terminal-Bench 2.1 5.6% — https://openrouter.ai/openai/gpt-4o-mini.
- **Traffic**: **zero of 30 days** in OpenRouter's daily rankings for 2026-09-25…10-24 — https://openrouter.ai/api/v1/datasets/rankings-daily — while still carrying 3 live endpoints (OpenAI, Azure, Azure Sweden Central +10%), output **$0.60–$0.66/M**, 128k context, live 2026-10-25 — https://openrouter.ai/api/v1/models/openai/gpt-4o-mini/endpoints.
- **Rank subtlety, resolved**: raw tag standing is **#10 of 10 in `content_writing`** (its only tag), but the policy-weighted *domain* rank is **#18 of 19** in writing — below the top-15 cut — and it has **no rank at all** in the other four pools (research 18, coding 21, orchestration 19, ops 18 candidates), i.e. below the cut in every domain — recomputed 2026-10-25 per `scripts/bind.py:domain_candidates` over https://openrouter.ai/api/v1/classifications/task?window=7d. The anchor's "#18, below cut" is correct; the tag rank alone would be misleading.

### Opinions

Nobody praises it; the evidence is installed-base gravity:

- Orca Security's scan of 426 AI-adopting organizations found GPT-4o-mini deployed in **28.6%** (5th of all models), ahead of newer OpenAI releases — https://tech-insider.org/gpt-4o-retirement-2026.
- OpenRouter + a16z's 100T-token study: tool invocation in early 2025 "concentrated among a small group of models: OpenAI's gpt-4o-mini and Anthropic's Claude 3.5 and 3.7 series" — https://arxiv.org/html/2601.10088v1.
- The migration-tax argument (rewrites, slower/more expensive successors for simple work) and the "80% of enterprise requests are simple lookups" routing advice — https://tech-insider.org/gpt-4o-retirement-2026.
- **Zero Reddit opinions in the last 7 days** — there is nothing left to say about it — https://modelsentiment.com/m/gpt-4o-mini.

### Known for

The entrenched, dirt-cheap multimodal glue model: classification, extraction, vision/OCR passes, structured outputs and tool-call loops in legacy pipelines that bill tokens by the billion.

### Caveats

- **The deprecation clock got a hard date — and sources disagree on which one.**
  - OpenAI, notice dated **2026-10-14**: `gpt-4o-mini-2024-07-18` removed from the API on **2027-01-14**, "**Fine-tuned versions of these models follow the same shutdown schedule as their underlying base models**," recommended replacement **`gpt-6-luna`** — https://developers.openai.com/api/docs/deprecations.
  - Azure/Microsoft's retirement schedule: `gpt-4o-mini-2024-07-18` Deprecated with retirement **2027-04-14** and **no replacement listed** — https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule (row read 2026-10-25).
  - **Conflict: 2027-01-14 (OpenAI, incl. fine-tunes) vs 2027-04-14 (Azure). Use the earlier date for planning.** The prior refresh's "fine-tuned deployments serve until 2027-04-14" came from the Azure side and is now the weaker half of the conflict.
- **Replacement changed**: OpenAI now says `gpt-6-luna` (https://developers.openai.com/api/docs/deprecations); AA's page suggests "GPT-5 mini" (https://artificialanalysis.ai/models/gpt-4o-mini); the current policy summary still says "OpenAI steers migrators to gpt-5.6-sol" — that phrasing is stale as of 2026-10-14.
- Out of ChatGPT since 2026-02-13 (https://openai.com/index/retiring-gpt-4o-and-older-models); the API was untouched then and is now dated to 2027-01-14.
- Quality ceiling, Oct-2023 knowledge and a 16,384-token output cap are unchanged; routing is thin (3 endpoints, unknown quant).

### Verdict

**UPDATE** — a hard API removal date (2027-01-14, fine-tunes included) plus a changed official replacement (`gpt-6-luna`) and an unresolved Azure conflict (2027-04-14) are decision-changing for anyone with it in a pipeline.

---

## openai/gpt-oss-120b

### Benchmark standing

- **Artificial Analysis, read 2026-10-25**: Intelligence Index **12, #11/67** in the open-weights size class, **232.7 tok/s (#4/26)**, **$0.15 in / $0.60 out**, 33% cache discount, **$0.11 per task (#2/8)**, 131k context, knowledge May 2024, released Aug 2025, **no deprecation banner** — https://artificialanalysis.ai/models/gpt-oss-120b. OpenRouter's AA feed (`as_of 2026-10-24`): **II 11.6 / coding 30.4 / agentic 3.7**, priced $0.03 in / $0.15 out — **AA's page and OpenRouter's feed disagree on price ($0.15/$0.60 vs $0.03/$0.15); the OpenRouter figure is a floor across providers, not the model's list price** — https://openrouter.ai/api/v1/benchmarks?source=artificial-analysis.
- Sharp profile (carried over, unchanged anchors): Math Index 93.4 / AIME 2025 93.4%, LiveCodeBench 87.8%, MMLU-Pro 80.8%, GPQA Diamond 78.2% — against **Agentic Index 3.7, Terminal-Bench 4.0 0.0%, GDPval-AA 5.4%, AA-Omniscience accuracy 21.8%** — https://openrouter.ai/openai/gpt-oss-120b.
- **Traffic**: **28 of 30 days**, **2.144T tokens** over 2026-09-25…10-24, last present 2026-10-23, rank sliding ~31 → ~48 — https://openrouter.ai/api/v1/datasets/rankings-daily — yet **absent from all 29 task tags** and therefore with **no rank in any domain pool** (18 / 19 / 21 / 19 / 18 candidates for research / writing / coding / orchestration / ops) as of `as_of 2026-10-24`: https://openrouter.ai/api/v1/classifications/task?window=7d.
- **Endpoints, live 2026-10-25**: **24**, output **$0.15–$0.95/M**, context 131,072, quant mix fp4 ×7 / bf16 ×4 / fp8 ×2 / int4 / fp16 / unknown ×9 — https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints.
- License Apache 2.0, 117B total / 5.1B active MoE, MXFP4-trained — https://huggingface.co/openai/gpt-oss-120b, https://github.com/openai/gpt-oss.

### Opinions

- **No successor, no deprecation**: `gpt-oss-120b` does not appear anywhere on OpenAI's API deprecation list (page read 2026-10-25 — https://developers.openai.com/api/docs/deprecations), and OpenAI's DevDay 2026 announcement list (2026-09-29) contains no open-weights release — https://openai.com/index/devday-2026-recap/, corroborated by the developer press coverage — https://www.infoq.com/news/2026/10/openai-devday-2026/. HF download count 2.87M (HF API, 2026-10-25 — https://huggingface.co/api/models/openai/gpt-oss-120b). Secondary claims about MLPerf Inference v6.0 standardization (Mar 2026) come from an unverified secondary source — https://www.frankx.ai/blog/gpt-oss-analysis-2026 — treat as unconfirmed.
- Local-hosting reception stays strong: "easily best local model you can run today… when reasoning_effort is set to 'high'" — https://news.ycombinator.com/item?id=45774585.
- The recurring implementation trap: "Many LLM libraries/services/frontends don't pass these reasoning tokens back to the model correctly, which is why people complain about this model so much" — https://news.ycombinator.com/item?id=46364597.
- Independent judge read: "strong on truthfulness, but overly conservative refusals hold them back" — https://oumi.ai/blog/openai-just-dropped-two-massive-open; OpenAI's own card documents the CoT-disobedience quirk — https://openai.com/index/introducing-gpt-oss.
- **Evidence gap**: no modelsentiment page exists (404 checked 2026-10-25 — https://modelsentiment.com/m/gpt-oss-120b), so no Reddit aggregate is available for this pass.

### Known for

The self-hostable reasoning workhorse: contest-grade math and code at near-commodity prices with real serving speed (232.7 t/s) and an Apache-2.0 license, for privacy-bound or high-volume math/code work.

### Caveats

- **Agentic/knowledge-work ceiling is unchanged**: Agentic 3.7, Terminal-Bench 4.0 0.0%, GDPval-AA 5.4%, heavy hallucination (Omniscience accuracy 21.8%) — skip research, writing and orchestration (links above).
- **Quant zoo and runner fragility**: 24 endpoints across fp4/bf16/fp8/int4/fp16/unknown with output caps from 4K to 117,964 and $0.15–0.95/M out (https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints); broken reasoning-token round-trips make the same model look brilliant or broken depending on runner (HN link above); for local GGUF the recommended build is Q4_K_M and "2-bit… quality collapse at that bitrate is steep, not gradual" — https://modelfit.io/quant-compare/gpt-oss-120b.
- **Family context changed**: its sibling `openai/gpt-oss-20b` is now **inside a top-15** — #14 of 19 in the writing domain pool (raw tag #7/10 in `content_writing`) as of `as_of 2026-10-24` — while 120b stays out of every pool (recomputed 2026-10-25 per `scripts/bind.py` over https://openrouter.ai/api/v1/classifications/task?window=7d). The "oss is invisible to selection" claim is no longer true of the family.
- Text-only, May-2024 knowledge cutoff — stale world knowledge for research use (HF card above).

### Verdict

**UPDATE** — anchors are unchanged and the exclusion itself still holds, but two decision-relevant facts are new: no successor and no deprecation exist as of 2026-10-25, and for the first time a family sibling (`gpt-oss-20b`) sits inside a domain top-15 (#14/19 writing), which changes what "the open-weights option" means in this policy.

---

## qwen/qwen3.6-35b-a3b

### Benchmark standing

- **Artificial Analysis, read 2026-10-25**: Intelligence Index **18, #13/141** in the open-weights size class, **131.4 tok/s (#18/64)**, **$0.375 in / $2.25 out**, **$0.48 per task (#18/23)**, 262k context, "very verbose" (160M tokens per II task), released April 2026, reasoning variant, **no deprecation banner** — https://artificialanalysis.ai/models/qwen3-6-35b-a3b. OpenRouter's AA feed (`as_of 2026-10-24`): **II 18.2 / coding 41.9 / agentic 13.1** at $0.10 in / $1.00 out — **AA's own page and OpenRouter's feed disagree on price ($0.375/$2.25 vs $0.10/$1.00); both are dated 2026-10-24/25 and neither matches the live OpenRouter endpoint range below.**
- **BenchLM / "BenchAlign" ranking slipped**: the leaderboard BenchLM hosts as "BenchAlign" reports **Capability 43.2/100, #130 of 228 ranked models**, data **as of October 25, 2026**, mathematics its strongest axis (#10), speed 131 tok/s, context 262K, no first-party price — https://benchlm.ai/models/qwen3-6-35b-a3b. The policy anchor says **#121/216 (43.29)** from the 2026-10-18 refresh; the catalog grew 216 → 228 and the rank/ score both fell. **Evidence marker on the page reads "Public — this profile does not yet have enough sourced coverage for a verified position"** (44 published rows), i.e. not independently verified.
- **Traffic — the decisive signal**: **5 of 30 days** in OpenRouter's daily rankings (2026-10-11, 10-14, 10-15, 10-16, 10-17), **0.879T tokens total, nothing since 2026-10-17** — https://openrouter.ai/api/v1/datasets/rankings-daily — and **absent from all 29 task tags** (`as_of 2026-10-24`), hence from all five domain pools (coding pool 21 candidates, others 18–19), i.e. outside every top-15 for **7 consecutive days**: https://openrouter.ai/api/v1/classifications/task?window=7d. **Board data shows the collapse but cannot explain it — no source in this pass attributes the cause, and none is claimed here.**
- **Endpoints, live 2026-10-25**: 10, output **$0.70–$1.80/M**, context 262,144, quants fp4 / fp8 / unknown — https://openrouter.ai/api/v1/models/qwen/qwen3.6-35b-a3b/endpoints.
- License **Apache 2.0**, 35B total / 3B active MoE with a vision encoder, pitched at agentic coding and repo-level reasoning — https://huggingface.co/Qwen/Qwen3.6-35B-A3B.

### Opinions

- **Superseded inside its own family**: Qwen3.8 (August 2026) is described by Qwen as "the most capable generation in the Qwen open-model family to date," with Qwen3.8-27B a dense vision-language successor — https://huggingface.co/Qwen/Qwen3.8-27B, blog https://qwen.ai/blog?id=qwen3.8. Qwen's own comparison table puts **Qwen3.8-27B ahead of the Qwen3.6-27B sibling** on SWE-bench Pro **61.7 vs 53.5**, Terminal-Bench 2.1 **73.0 vs 63.4**, DeepSWE 1.1 **42.2 vs 13.3**, QwenSWEBench **79.0 vs 49.3** (same HF table). **Honesty note: those comparisons are against Qwen3.6-**27B**, the dense sibling — no head-to-head against the 35B-A3B MoE is published, so "superseded" is an inference from generation and family, not a measured win over this exact model.** Qwen3.7 never shipped open weights at all — https://codersera.com/blog/how-to-run-qwen-3-7-locally-2026/ (secondary, unverified).
- **Vendor positioning**: QwenCloud still lists `qwen3.6-35b-a3b` (256k ctx) in its full model list, but its "Recommended models" table and migration guidance point to `qwen3.8-max`, `qwen3.7-plus`, `qwen3.8-flash` — https://docs.qwencloud.com/developer-guides/getting-started/text-generation-models (read 2026-10-25).
- **Adjacent, unattributed context**: Qwen3.8-Flash has been free "for a limited time" for all Qoder users since **2026-09-18** — https://docs.qoder.com/events/flashoffer. This overlaps the traffic window but **no source connects the two**; stated as context only.
- **Evidence gaps for the existing summary**: the current entry's Reddit claim ("best coding model rn", 63/100 positive), the Dev.to verdict, SWE-bench Verified 73.4% and the RealWorldQA figure appear in `research/2026-10-summary-refresh.md` **without any URL**, and modelsentiment has no page for this model (404, checked 2026-10-25 — https://modelsentiment.com/m/qwen3.6-35b-a3b). Those claims could not be re-sourced this pass and should not be carried forward as cited facts.

### Known for

A specialized open-weight coding MoE (35B/3B, Apache 2.0, vision-capable) for local and production code workloads — the cheap self-hosted coding pick, not a general-purpose flagship.

### Caveats

- **Invisible to selection as of 2026-10-24**: zero board presence for 7 straight days, absent from every task tag and every domain pool (data sources above). Whatever its benchmarks say, the policy engine cannot pick it.
- **Rank and score both declined** (BenchAlign #121/216 → #130/228, 43.29 → 43.2, data 2026-10-25) and the evidence is "Public," not verified — https://benchlm.ai/models/qwen3-6-35b-a3b.
- **Successor pressure**: Qwen3.8-27B beats the Qwen3.6-27B sibling across every published coding/agent table (HF link above), and Qwen's own docs route recommendation to 3.8/3.7 models (QwenCloud link above).
- Price sources disagree three ways: AA $0.375/$2.25, OpenRouter AA feed $0.10/$1.00, live endpoints $0.70–1.80/M out (all dated 2026-10-24/25, links above).
- Community-quality claims in the current summary are unsourced (above) — an honesty gap, not merely a staleness gap.

### Verdict

**RETIRE — delete this entry from `summaries`** — zero board presence for 7 consecutive days, a declining and unverified third-party rank, a same-family successor, and unsourced opinion claims make it a standing exclusion with no selection value; **deleting the summary entry entirely is the recommended outcome** (nothing else in `policy.json` changes; `hints`/`fit` are untouched and carry no entry for it).

---

## Policy summaries

Exactly one proposed replacement per model. For `qwen/qwen3.6-35b-a3b` the recommendation is
deletion, so its text below is a **record of what the entry would say if it were kept — do not
write it to `policy.json`**.

**openai/gpt-5.6-sol** — The July-2026 GPT-5.6 flagship (AA 47, #28/215; coding 77.4 #3/65; **$4/$20 with promotional pricing confirmed only "at least through November 21, 2026"**, as of 2026-10-25): still Every's "favorite model to collaborate with" and OpenAI's own migration target for `gpt-5`/`o3` (removal 2026-12-11) and the 2026-10-23 legacy batch, making it the strongest OpenAI pick for iterative writing, research and knowledge work fed with sources and style guides. Two status facts now dominate the decision: AA marks it deprecated in favour of GPT-6 Sol and ChatGPT replaced it with GPT-6 on 2026-10-07, while the API keeps it as a designated replacement — treat it as a dated asset. Re-validate quality and price after 2026-11-21, expect >272K prompts at 2×/1.5× ($8/$30) and fast-tier endpoints at $10–40/M out, keep a GPT-6 fallback, and remember it is unranked in all five domain pools (traffic, not quality).

**openai/gpt-4o-mini** — July-2024 legacy glue model (AA **7, estimated**, #52/71 non-reasoning; **$0.15/$0.60**; GDPval-AA 0.0%; **zero of the 30 ranking days to 2026-10-24**) for high-volume classification, extraction, vision passes and structured outputs in installed pipelines only — never research, writing or real coding. The clock is now hard: OpenAI's 2026-10-14 notice removes it from the API on **2027-01-14 including fine-tunes** and points migrators to **`gpt-6-luna`**, while Azure's schedule still says 2027-04-14 with no replacement — **sources disagree; plan against the earlier date**. It sits **#18 of 19** in the writing domain pool and below the cut everywhere, so new work must not start here.

**openai/gpt-oss-120b** — The Apache-2.0 self-host play (AA **12, #11/67 open weights**, 232.7 t/s #4/26 and **$0.11/task #2/8** as of 2026-10-25; anchor 11.6 / coding 30.4 / agentic 3.7 as of 2026-10-24): contest-grade math and code (Math 93.4, LiveCodeBench 87.8%) at $0.15–0.95/M out over **24 endpoints**, with **no successor and no deprecation anywhere as of 2026-10-25**. Its 2.144T tokens across 28 of 30 days show real demand while it stays out of all 29 task tags and every domain pool — but its sibling `gpt-oss-20b` is newly inside the writing top-15 (#14/19), so the family is no longer invisible to selection. Keep it for privacy-bound or high-volume math/code volume; skip research, writing and orchestration (agentic 3.7, Terminal-Bench 4.0 0%, Omniscience accuracy 21.8%) and mind the quant zoo plus broken reasoning-token handling in off-the-shelf harnesses.

**qwen/qwen3.6-35b-a3b** — **RETIRE: delete this entry (record only, do not write to `policy.json`)** — April-2026 open-weight coding MoE (35B/3B active, Apache 2.0; AA 18, $0.375/$2.25 as of 2026-10-25) whose BenchLM/BenchAlign score fell to **43.2, #130/228 (data 2026-10-25, evidence "Public," not verified)** from #121/216 in the Oct-18 anchor. It appeared on OpenRouter boards only 5 of the 30 days to 2026-10-24 — **none since 2026-10-17** — and is absent from all 29 task tags and all five domain pools, while Qwen's own Qwen3.8 generation and QwenCloud recommendation tables have moved past it (no published head-to-head against this exact MoE). If it were ever kept, it would be a local-deployment option only, never a selection candidate — and its Reddit/Dev.to claims would first need sourced URLs, which this pass could not find.
