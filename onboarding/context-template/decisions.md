# Decisions: {{OWNER_NAME}}

Append-only log. One line per decision, newest at the bottom. A decision enters this file only when {{OWNER_NAME}} said it is decided. Reversals get a new line that points at the old one; the old line stays.

Line format:

```
- YYYY-MM-DD | decision in one sentence | source (conversation, document, meeting) | confirmed by owner: yes
```

## Decisions

Written at onboarding on {{ONBOARDING_DATE}}:

{{CONFIRMED_DECISIONS}}

## Open items

Tasks and questions that were mentioned but not settled. Give each an owner and a due date when known.

{{OPEN_ITEMS}}

## Acceptance runs

One line per run of an acceptance case from `company.md`: date, case number, result (`pass`, `fail`, `partial`), and what the owner said.

None yet.
