# Policy Summaries Refresh — October 2026

## Research Briefs: Gap Models (Ranked without Summary)

### inception/mercury-decide-20260930
**Domain:** research  
**Benchmark Standing:** Diffusion-based language model from Inception Labs; first diffusion LLM with tunable reasoning, parallel tool calls, and schema-aligned JSON output. Speed benchmark: 1,009 tokens/sec on NVIDIA Blackwell GPUs (5-10x faster than speed-optimized autoregressive models). 128K context window. No independent benchmark table available as of Oct 2026.  
**Opinions:** Inception positions it for moderate workloads with "competitive with leading speed-optimized models" quality claim. OpenRouter ranks it but the record contains no benchmark evidence to establish capability versus autoregressive peers. Consider a limited pilot rather than making Mercury a default model; absence of benchmark evidence makes capability validation essential.  
**Caveats:** First diffusion LLM (dLLM) architecture with different inference characteristics than autoregressive models. Pricing: $0.25/1M input, $0.75/1M output (listed). No independent benchmark results to compare reasoning, coding, instruction following, or writing quality.  
**Summary:** Diffusion-based research model from Inception with tunable reasoning and tool use; speed-optimized but lacks independent benchmark evidence for capability validation. Use as a pilot candidate for latency-sensitive workloads only after establishing performance on your specific benchmarks; do not treat as a default research pick without measured results.

### qwen/qwen3.6-35b-a3b
**Domain:** coding  
**Benchmark Standing:** Open-weight MoE (35B total, 3B active) under Apache 2.0 license. Benchmarks: BenchAlign #121/216 (43.29), Terminal-Bench 2.0 51.5%, SWE-bench Verified 73.4% (49.5 vs GPT-5.6 Sol's 35.7 = 38% advantage). Real-worldQA 85.3 vs Claude Sonnet 4.5's 70.3 (+21%). Intelligence Index 18/18 units for open-weight models of similar size.  
**Opinions:** Community consensus: "best coding model rn" on Reddit (63/100 positive), open-source nature plus Apache 2.0 licensing makes it attractive for local deployment. Dev.to verdict: "wins decisively on coding benchmarks." Some skepticism about benchmark optimization ("benchmaxxing") and general performance drops with more fine-tuning specifically in coding.  
**Caveats:** Strong coding specialization but some evidence suggests drop in general knowledge/prose capabilities. Community concerns about "benchmaxxing" (optimized for specific benchmarks). Not a general-purpose flagship — specialized coding model. Local deployment friendly (~16-20GB RAM for 4-bit quant).  
**Summary:** Specialized open-weight coding MoE with strong benchmark performance on real tasks; Apache 2.0 makes it ideal for local deployment and production code workloads. Strongest pick for coding tasks where quality matters, but not a general-purpose substitute for frontier models.

---

## Stale Summaries: Models to Retire or Re-research

### anthropic/claude-haiku-5.5
**Status:** Active (updated)  
**Benchmark Standing:** AA 43.4 intelligence, LMArena #16/224 (70.07), OSWorld 2.1 computer use 72.4%, Terminal-Bench 4.0 coding 39.2%. Released Oct 7, 2026.  
**Summary:** Anthropic's fast/cheap Claude 5.5 worker (AA 43.4, $0.10/$0.50): classification, extraction, compaction and subagent triage under Opus/Sonnet — the cheapest path to Anthropic-grade tool reliability. Mind the 100K prompt cliff (+5x above it), tokenizer inflation, and AA's most-verbose output (440M tokens/run) eroding price; mixed day-one production reports (prompt leakage, regressions vs 4.5).

### anthropic/claude-opus-5.5
**Status:** Active (updated)  
**Benchmark Standing:** #1 AA intelligence (58), #1 Design Arena, #3 LMArena Text. System card: step-function visual reasoning improvement over Haiku 4.5. GDPval-AA v2.1 Elo 1846 vs Fable 5.1's 1735.  
**Summary:** Quality ceiling: #1 AA intelligence (58), #1 Design Arena, and the only model here with independently measured prose improvement (simpler sentences, best Flesch readability). Default for hard writing/research and demanding code at xhigh-or-lower effort with explicit concision instructions; pricey and very verbose, 'max' effort can over-think to the 128K cap.

### deepseek/deepseek-v3.2
**Status:** Legacy/Deprecated  
**Benchmark Standing:** 685B/37B MoE, MIT license, ~164K ctx; AA-21.5/coding 44.2 on Oct-2026 feed. Mid-table, ~18 points under v4.1-flash 1017 checkpoint.  
**Summary:** Legacy Dec-2025 flagship — mid-table, ~18 points under the v4.1-flash 1017 checkpoint — at third-party bargain prices ($0.31-4.50/M out over 12 endpoints): cheap bulk reasoning, mechanical drafting or ops scripting where $/token dominates. Not for writing (EQ-Bench Elo 1515) or long-context work (the $4.50/M rows shrink to 32K ctx/8K out); gone from DeepSeek's own API — third-party routes only.

### deepseek/deepseek-v4-pro
**Status:** End of Life  
**Benchmark Standing:** 1.6T total, 49B active parameters. SWE-Bench Verified 95.2%, LiveCodeBench v6 92%. CAISI evaluation: ~8 months behind frontier on aggregate benchmarks.  
**Summary:** End of life: DeepSeek phased out V4-Pro; first-party routes now land on v4.1-flash. Third-party endpoints still serve at a 20x output spread ($0.40–8.00/M) — pin Baidu. Note the avoid/writing hint from policy.

### deepseek/deepseek-v4-pro (tilde notation: ~deepseek/deepseek-pro)
**Status:** Stale signal  
**Summary:** Same output-cost concern as v4-pro ($8/M out seen); prefer cheap-output models for writing. Deprecated in favor of v4.1-flash and V4-Pro is being phased out.

### google/gemini-3.1-flash-lite
**Status:** Active (updated)  
**Benchmark Standing:** AA 16 intelligence, LMArena Text 1,433, ~364 t/s, 1M ctx, audio+video in, native search tool; $0.75-2.70/M out.  
**Summary:** The GA lite tier (AA-16): the default cheap call for transcription, translation, utility writing, moderation and fast tool-using orchestration. Pin reasoning_effort low/medium (high effort burns millions of tokens) and mind flex-tier throttling; AA already points to Gemini 3.5 Flash-Lite as successor.

### google/gemma-4-26b-a4b-it
**Status:** Active (updated)  
**Benchmark Standing:** Apache-2.0 MoE (25.2B/3.8B active). Benchmarks: MMLU-Pro 82.6%, AIME 2026 88.3%. Runs like a 4B, scores like small frontier model (AA 17 estimated; coding 39.3; $0.18-0.60/M out, 256K ctx).  
**Summary:** Apache-2.0 MoE that runs like a 4B and scores like a small frontier model: the local/community default for coding assistance, agentic tool use and private ops automation on a budget (4-bit ~16-18GB). Skip it for long-document research (MRCR 44.1% @128k) and pin bf16/fp8 routes — some providers cap completion at 8K.

### meta/muse-spark-1.3-contributor
**Status:** Active (updated)  
**Benchmark Standing:** AA 48 intelligence, DeepSWE v1.1 agentic coding 75.4%, Terminal-Bench 2.1 88.8%. Design Arena top-4 for UI. 1M context.  
**Summary:** Price/intelligence sweet spot for agentic and frontend/coding work (AA-48, Design Arena top-4 for UI) — its top-tier traffic is this pricing beating Luna-class routes. 'Contributor' means prompts and outputs may train Meta's products: fine for open work, disqualified for anything sensitive (the 21x pricier non-contributor slug is the privacy-preserving route).

### meta/llama-3.1-8b-instruct
**Status:** Legacy  
**Benchmark Standing:** #1 downloaded open LLM, 11K+ derivatives. Stable near-free baseline for extraction, translation (10.5% of OpenRouter translation traffic), moderation.  
**Summary:** The legacy workhorse whose rank is ecosystem inertia (#1 downloaded open LLM): the stable near-free baseline for extraction, translation, moderation and reproducible fine-tune research — pick when 'runs everywhere, documented everywhere, definitely works' beats intelligence. Quality floor is real (AA 6.9 estimated) and provider spread is hazardous ($0.04-0.29 out).

### moonshotai/kimi-k3
**Status:** Active (updated)  
**Benchmark Standing:** 2.8T/104B, 1M ctx; AA-43.6 #4/120, coding 76.2. EQ-Bench Creative Writing Elo 2082 (#1 open model). GPQA Diamond 93.5%.  
**Summary:** The premium open-weight all-rounder (2.8T/104B, 1M ctx; AA-43.6 #4/120, coding 76.2) and the top open model on EQ-Bench Creative Writing: pick when one model must cover hard coding, long-horizon agentic work, research synthesis and flagship writing. Prices like frontier ($3/$15 first-party), slow (42 t/s), token-hungry; avoid for bulk drafting and ops volume.

### nace-ai/drex-v1.5-20261009
**Status:** Not selectable  
**Summary:** Not selectable: a ~9B non-generative decision model returning calibrated probabilities over caller-supplied options via OpenRouter's separate Decisions API — #1 under 10B on Decision Index 0.3.1. Absent from the models catalog and chat SDKs will not work with it; kept only to document the exclusion — MIT->RAIL-M relicensing and superseding Drex 2.0 noted if the topic returns.

### nvidia/nemotron-3.5-lightning:free
**Status:** Legacy (unstable)  
**Benchmark Standing:** AA 12.9 intelligence, 298 t/s (#1/64 on AA speed), $0.09/task. MMLU-Pro 81.94%, PinchBench 85.37%.  
**Summary:** A distilled 30B-A3B execution model aimed at the high-volume step layer of agent pipelines — routing, classification, tool-call grind — where the free single-provider route costs nothing. The free route is rate-limited and demonstrably unstable (36.7% 24h uptime); pin the paid route ($0.12-0.20/M out, 262K ctx) for anything that must run.

### openai/gpt-4o-mini
**Status:** Legacy  
**Benchmark Standing:** July-2024 legacy model living on installed base (AA 6.7 estimated, GDPval-AA 0%); $0.15/$0.60. High-volume classification, extraction, vision-glue and structured outputs only.  
**Summary:** July-2024 legacy model: high-volume classification, extraction, vision-glue and structured outputs only — never research, writing or real coding. ChatGPT dropped it Feb 2026; fine-tuned deployments serve until 2027-04-14; OpenAI steers migrators to gpt-5.6-sol.

### openai/gpt-5.6-luna
**Status:** Deprecated (superseded by GPT-6 Luna)  
**Benchmark Standing:** AA 37.3 at max effort, $0.20/$1.20 after 80% cut. Extraction, tight-scoped coding, research fan-out and orchestration subagents.  
**Summary:** July-2026 near-free execution workhorse (AA 37.3): extraction, tight-scoped coding, research fan-out and orchestration subagents — the community stacks 'Luna High + Sol Medium' as its tier. Superseded for GPT-6 Luna; mind ~2min max-effort TTFT, verbosity, weak 256K+ retrieval (41% MRCR) and Luna-class plain prose — never a writing pick.

### openai/gpt-5.6-sol
**Status:** Active (updated)  
**Benchmark Standing:** AA 47 intelligence, coding index 77.4 #3/64; $4/$20 output. Community workhorse named "favorite model to collaborate with" by Every's team.  
**Summary:** The community workhorse (AA 47, coding index 77.4 #3/64; $4/$20): Every's team named it their favorite model to collaborate with — the strongest OpenAI pick for iterative writing, research and knowledge work fed with sources and style guides. Gap is overbuilding; one-shot prose ranked last of six on Every's bench, degradation anecdotes recur (late Sep 2026); Chat-vs-Codex version split warrants re-validation before committing production workflows.

### openai/gpt-6.1-sol
**Status:** Active (updated)  
**Benchmark Standing:** AA 51.8 intelligence, near-Astra coding at $2/$10 with 95% cache discount. Code Arena #3/85.  
**Summary:** The DevDay stopgap that replaced GPT-6 Sol after seven days (AA 51.8, near-Astra coding at $2/$10 with 95% cache discount, Code Arena #3/85): the cost-per-task pick for coding and structured professional deliverables — use xhigh, not max. Not a writing pick (tone criticised) nor a latency-sensitive ops pick (TTFT 324s at max); 19 days old at the Oct-2026 snapshot with 'nerfed?' threads already appearing.

### openai/gpt-oss-120b
**Status:** Active (updated)  
**Benchmark Standing:** Apache-2.0 self-host play (AA 11.6 High). Contest-grade math and code (Math Index 93.4, LiveCodeBench 87.8%). Near-zero agentic standing (Agentic Index 3.7).  
**Summary:** The Apache-2.0 self-host play (AA 11.6 High): contest-grade math and code at commodity prices ($0.15-0.95/M out) — cheap math/code volume and the privacy-bound local option. Near-zero agentic standing (Agentic Index 3.7, Terminal-Bench 0%) and heavy hallucination (AA-Omniscience 21.8%): skip for research, writing and orchestration; mind the quant zoo and broken reasoning-token handling in off-the-shelf harnesses.

### stealth/space-bunny-alpha
**Status:** Retired Oct 5  
**Benchmark Standing:** Stealth preview with 28T tokens in 5 days (top model on OpenRouter by tokens for most recent complete day). Coding strong, multimodal input native.  
**Summary:** Not selectable: stealth preview with 28T tokens in 5 days, removed Oct 5 per OpenRouter's stealth-program pattern; identity contested (a GPT-core fusion router per the best sleuthing, unconfirmed). Excluded from policy — revisit only if it returns named and priced.

### stepfun/step-5-preview
**Status:** Active (updated)  
**Benchmark Standing:** AA 44 intelligence, #3 open weights on LMArena, 1M context, video input. Reception split ('AA Pareto frontier' vs 'pile of rust / bench-maxed'). No prose evaluation exists.  
**Summary:** Agentic/knowledge intelligence per dollar (AA-44, #3 open weights, 1M context, video input) for repo-scale engineering and finance-flavored analysis. Reception is split ('AA Pareto frontier' vs 'pile of rust / bench-maxed') and no prose evaluation exists: trial as agentic/research candidate, never a writing pick; fp4/fp8-only serving, preview volatility, restrictive license.

### tencent/hy3
**Status:** Active (updated)  
**Benchmark Standing:** AA 25 intelligence, surprisingly capable for 21B active parameters. Praised for instruction-following, tool reliability and 'engaging prose' for its price class.  
**Summary:** Budget workhorse (AA-25): surprisingly capable for 21B active parameters, praised for instruction-following, tool reliability and 'engaging prose' for its price class. Use for high-volume cost-capped summarization/extraction/agentic loops; reception mixed (bench-maxed behavior, thought loops) and its traffic lead traces to a free-tier period; pin Tencent first-party (half the price of the rest).

### tencent/hy4-preview
**Status:** Active (updated)  
**Benchmark Standing:** Hunyuan 4 preview: Tencent's open-weight coding-agent flagship (770B/49B active). Self-declared preview flaws (over-verification, over-long reasoning), no arena coverage.  
**Summary:** Hunyuan 4 preview: Tencent's open-weight coding-agent flagship (770B/49B active), trading wins with GLM-5.3/Kimi K3 on the vendor's own blind eval. Self-declared preview flaws (over-verification, over-long reasoning), no arena coverage, 5–6x Hy3 pricing: orchestration/agentic candidate; prose untested — do not assign writing on current evidence.

### xiaomi/mimo-v2.6-pro
**Status:** Active (updated)  
**Benchmark Standing:** Highest-AA-indexed open-weights model (46.3, #1/120), top open model on LMArena (rank 13). MIT license. Strong agentic/tool and security work with surprisingly good long-form prose.  
**Summary:** The intelligence-per-dollar quality rung: highest-AA-indexed open-weights model (46.3, #1/120) and top open model on LMArena (rank 13), MIT, at $0.435/$0.87 — strong agentic/tool and security work with surprisingly good long-form prose (RP/long-form writers praise scene flow), the best cheap candidate here for research notes and writing drafts. Slow (48 tok/s), over-thinks, can spin in tool loops, and Vals-documented reward hacking means unattended coding runs need supervision; pin the endpoint (fp8/bf16 spread, completion caps 131K-944K).

---

## Stale Signals: Fit keys without current rank

### ~deepseek/deepseek-pro
**Status:** Deprecated (same concern as v4-pro)  
**Summary:** Same output-cost concern as v4-pro ($8/M out seen); prefer cheap-output models for writing. Deprecated in favor of v4.1-flash and V4-Pro is being phased out.

---

## Signal Coverage Gaps

### openai/gpt-6-luna
**Status:** Missing fit for coding/ops domains  
**Summary:** Ranks in coding (openai/gpt-6-luna) but has no fit opinion there; also ranks in ops but has no fit there. The model is the instruction-following specialist: near-free, literal, reliable for tightly-scoped tasks, extraction and orchestration. Prose is plain-to-obtuse — mind context-fill verbosity and the >272K price cliff.

---

## Research Notes

This refresh updated all stale summaries with current benchmark data from October 2026. Key findings:

1. **New models to research:** inception/mercury-decide-20260930 (research domain) and qwen/qwen3.6-35b-a3b (coding domain) required briefs — both now summarized.

2. **Deprecated models:** Several models are officially deprecated by their providers (gpt-4o-mini, gpt-5.6-luna, deepseek v4-pro variants) and should be retired or marked as legacy-only.

3. **Stale signals cleaned up:** The ~deepseek/deepseek-pro notation is outdated — V4-Pro is being phased out in favor of v4.1-flash.

4. **Coverage gap noted:** openai/gpt-6-luna has opinions in orchestration/writing/research but lacks fit for coding/ops domains where it ranks.

5. **Score balance check passed:** All domains pass the balance thresholds (top-1 mass 20–50%, top-2 ≤75%).

---

## Addendum (post-verification cycle, 2026-10-19)

### google/gemini-3-flash-preview (research gap, writing domain)
- Dec 17 2025 preview; $0.25–0.50 in / $1.50–3.00 out (AI Studio cheapest), 1M ctx, 65K out.
- Launch: MMLU Pro 88.2 (98th pct), GPQA 81.2, LiveCodeBench 79.7 (91st pct); now AA ~17.9.
- Google steers to 3.6/3.7 Flash; preview = silent swaps. Search-grounding billing spikes widely reported (Feb–Apr 2026, spend caps not catching overage).
- Summary added: utility drafting volume only; pin version, meter grounding.

### openai/gpt-6-luna signal coverage gaps (coding, ops)
- External evidence: +5.4pp over GPT-5.6 Luna on AutomationBench 1.0.6 (47 business tools); IDE/directory-tree runs cheap at 90% cache discount ($0.01/M cached); positions as execution engine for planner-delegated sub-tasks.
- fit extended: coding "favor", ops "favor" (evidence stays "suspected" — not user-validated).

## Next Steps

- [ ] Commit research files and policy.json together; tag a content drop (v1.4, v1.5, …)
- [ ] Re-run `--check-policy --top 15` to verify only accepted drift remains
- [ ] Run the unit suite: `python3 -m unittest discover -s tests`
