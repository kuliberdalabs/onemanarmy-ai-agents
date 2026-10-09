# Memory

Long-term memory for {{ASSISTANT_NAME}}. It holds lasting preferences and facts the owner has explicitly accepted, and nothing else.

## What goes in

- A preference or fact that will matter again.
- With the date, the source, and the basis on which {{OWNER_NAME}} accepted it.

## What stays out

- Secrets, credentials and raw personal data.
- Whole transcripts and confidential documents. Keep a short summary with a pointer to the original.
- Anything on the never-store list in `company.md`.

## Hypotheses

A pattern the agent noticed is written down as a hypothesis first. It becomes an active rule after the owner confirms it. Contradicting signals stay next to each other until the owner resolves them.

`onboarding-answers.md` in this folder is the record of the onboarding interview: the owner's answers by question, each marked `said`, `inferred` or `unknown`.
