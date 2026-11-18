# Independent review split (empty by design)

No independently human-reviewed cases exist yet. This directory is reserved for
external reviewers following `docs/INDEPENDENT_VALIDATION_PROTOCOL.md`.

Do NOT add synthetic cases here. Cases placed here must carry
`provenance: independent-human-reviewed` plus `reviewer_id` and `review_date`;
the dataset loader rejects anything else.

Held-out label disputes awaiting adjudication are listed in
`docs/FAILURE_ANALYSIS.md`; the held-out dataset itself remains frozen.