# The Local roster is seeded once and never coupled

Local candidates enter the pool only from the Local roster — the author-owned
record of local models, their serving facts, and their Capability bands,
maintained by hand. The roster is seeded once by an exporter that lives in
local-llm-bench (which owns its own file structure) and writes gaps only: it
creates missing entries, stamps provenance, and never touches an entry the
user owns. Modelbandit itself never learns local-llm-bench's structure.

Considered: live sync of benchmark results into candidate data. Rejected
because benchmark numbers are evidence for a human band judgment, not policy;
the coupling would drag a second repo's schema churn into every deal and
quietly overwrite hand-tuned bands. Seed evidence is suspected until the user
edits the entry.
