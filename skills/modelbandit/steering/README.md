# Steering — brief material for dealt local rows

Prompt files for implementer runs on local models. When the deal assigns a
local row (`lmstudio/*`) and a ticket is dispatched to it, the spawn brief is
composed from this directory:

1. `operating-discipline.md` — the shared skeleton: edit discipline, the
   evidence-per-criterion report shape, environment workarounds, and the
   orchestrator's stop rules. Paste it into every local-run brief.
2. `<model>.md` — one file per served local model: its observed failure
   modes and the clauses that answer them, plus its prompting and serving
   facts. Splice the model's block in after the skeleton.

Prompts are files, never prose: change steering by editing these files and
say in the run record which revision the brief carried.

## Provenance

Every clause traces to evidence, named in the file that carries it:

- **Run evidence** — the spec #75 transcript post-mortem (2026-11-16):
  twelve implementer transcripts across five local models on real spec
  tickets, plus the two unaided passes (#83 mimo, #84-pinfinish qwen36)
  that prove which clauses work. The per-model files cite the run ids
  (`…-***REMOVED***` and siblings) recorded in the local-llm-bench dossiers.
- **Bench evidence** — the local-llm-bench benchmark and its dossiers
  (sampling, load config, artifact quality).
- **Community evidence** — cited in the dossiers (`community_findings`);
  carried here only where it changes how the model must be prompted or
  served.

## Maintenance

Clause updates land here from the summaries-refresh procedure
(`research/README.md`): dated, cited, per model. A new incident adds its
clause to the model's file before that model is redealt.
