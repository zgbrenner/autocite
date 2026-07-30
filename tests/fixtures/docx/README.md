# DOCX preservation fixtures

Preservation tests generate their DOCX inputs in memory with `python-docx` and, where necessary, narrowly modify the resulting XML. This keeps the suite reproducible and avoids committing client documents, copyrighted legal filings, personal information, or opaque binary fixtures.

A committed binary fixture is permitted only when all of the following are documented next to it:

- the file is original test material or has a redistribution-compatible license;
- it contains no confidential, privileged, personal, or client information;
- the exact Word structure cannot be reproduced reliably in a small fixture builder;
- its SHA-256 fingerprint and expected structural assertions are recorded;
- a reviewer has confirmed that the fixture is necessary.

Real-document evaluation uses the separate manifest-driven harness and locally mounted permissioned documents. Those source documents must not be committed to the repository.