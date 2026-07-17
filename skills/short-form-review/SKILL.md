---
name: short-form-review
description: Use when Id., short-case, statutory short form, supra, supra note, or hereinafter has an uncertain antecedent.
---

# Short-form and antecedent review

Call `resolve_short_form` and inspect the citation graph. A later citation cannot validate an earlier short form. Do not choose the highest-scoring candidate when multiple candidates remain legally possible. Return the resolved authority or `null`, method, candidates, confidence, disqualifying facts, profile, and review requirement. Never bypass an AutoCite abstention.
