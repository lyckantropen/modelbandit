# The Local roster is seeded once and never coupled

Local candidates' bands enter the pool only from the Local roster — the
author-owned judgment record, keyed by the harness's own model id, holding
Capability bands and prose and nothing else. What local models exist, their
ids, and how they are served belong to the harness that serves them (the
`lmstudio/` namespace and its listing); the roster never restates serving
facts. The roster is seeded once by an exporter that lives in a companion local-model benchmark
repository (which owns its own file structure) and writes gaps only: it creates missing
entries, stamps provenance, and never touches an entry the user owns.
Modelbandit itself never learns that tool's structure.

Considered: live sync of benchmark results into candidate data. Rejected
because benchmark numbers are evidence for a human band judgment, not policy;
the coupling would drag a second repo's schema churn into every deal and
quietly overwrite hand-tuned bands. Seed evidence is suspected until the user
edits the entry.
