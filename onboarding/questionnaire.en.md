# Onboarding interview (English)

For {{OWNER_NAME}}. Eighteen questions, asked one at a time. Ask a follow-up when an answer is general ("it depends", "all kinds of things"): a recent, concrete example is worth more than a description. Skip a question when an earlier answer already covers it, and say that you are skipping it. If the owner declines a question, record "declined" and move on.

Each question ends with a `Feeds:` line. It names the placeholders in `context-template/` that the answer fills. The line is for the interviewer and is not read aloud.

## Role and day

### 1. Which decisions are yours alone?
Follow-up: ask for the last two real decisions, and who else was involved in each.
Feeds: `{{DECISIONS_OWNED}}`

### 2. Walk me through a typical day, from the first message to the end of work.
Follow-up: where does time disappear, and what happens at fixed hours?
Feeds: `{{TYPICAL_DAY}}`

### 3. What breaks your focus, or sends you back to the same information again and again?
Follow-up: ask for the most recent example and where the answer was finally found.
Feeds: `{{INTERRUPTIONS}}`

## Projects and people

### 4. Which three projects matter most right now?
Follow-up: one sentence of status for each. What would "going well" look like in a month?
Feeds: `{{PROJECT_1_NAME}}`, `{{PROJECT_1_STATUS}}`, `{{PROJECT_2_NAME}}`, `{{PROJECT_2_STATUS}}`, `{{PROJECT_3_NAME}}`, `{{PROJECT_3_STATUS}}`

### 5. Who do you work with on each of them, and what do you expect from those people?
Follow-up: who is waiting on you, and who are you waiting on?
Feeds: `{{PROJECT_1_PEOPLE}}`, `{{PROJECT_2_PEOPLE}}`, `{{PROJECT_3_PEOPLE}}`

### 6. Where do you record decisions, deadlines and meeting outcomes today?
Follow-up: what gets lost between the meeting and that place?
Feeds: `{{RECORDING_TODAY}}`

## Documents and sources of truth

### 7. Which types of documents do you work with most often?
Follow-up: which of them do you write, and which do you only read?
Feeds: `{{DOCUMENT_TYPES}}`

### 8. Which folders or systems are the source of truth, and which hold copies or old versions?
Follow-up: when two versions disagree, which one wins, and who decides?
Feeds: `{{SOURCES_OF_TRUTH}}`, `{{COPIES_AND_STALE}}`

### 9. What data is sensitive and must stay out of the assistant's memory?
Follow-up: name categories (people, money, health, credentials, client material) and any specific folders. Do not ask the owner to paste the sensitive data itself.
Feeds: `{{NEVER_STORE}}`

## Outputs

### 10. What does a good morning brief look like?
Follow-up: length, order, and the one thing it must never leave out.
Feeds: `{{MORNING_BRIEF}}`

### 11. After a voice note, what do you want back: a report, decisions, tasks, a draft message, or all of them?
Follow-up: in what order, and where should it be delivered?
Feeds: `{{VOICE_NOTE_OUTPUT}}`

### 12. Show me five real cases we can use to judge the first version.
Follow-up: pick cases that already happened, so the owner knows what a good answer looks like. Ask for the expected result in a sentence for each.
Feeds: `{{ACCEPTANCE_CASE_1}}`, `{{ACCEPTANCE_CASE_2}}`, `{{ACCEPTANCE_CASE_3}}`, `{{ACCEPTANCE_CASE_4}}`, `{{ACCEPTANCE_CASE_5}}`

## Autonomy

### 13. What may the assistant write or change on its own?
Follow-up: files, folders, notes, drafts. Which of those can be undone, and how?
Feeds: `{{AUTONOMY_ALONE}}`

### 14. Which actions must always wait for your confirmation?
Follow-up: sending anything to another person, publishing, deleting, spending money, anything outside the workspace.
Feeds: `{{AUTONOMY_CONFIRM}}`

### 15. How fast, and in what form, should the assistant report an error or a conflict between sources?
Follow-up: what counts as urgent enough to interrupt you?
Feeds: `{{ERROR_REPORTING}}`

## Style

### 16. Show me two messages or documents written in a style you like.
Follow-up: what exactly do you like about them? If the samples are confidential, ask the owner to describe the style instead of sharing the files.
Feeds: `{{STYLE_SAMPLES}}`

### 17. What tone and formats do you not want to see?
Follow-up: phrases, emoji, long preambles, tables, bullet lists, anything else that annoys.
Feeds: `{{STYLE_AVOID}}`

### 18. What will you call your assistant?
Follow-up: none needed. A working name is fine and can change later.
Feeds: `{{ASSISTANT_NAME}}`
