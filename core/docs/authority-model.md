# Authority model

What an agent may do without asking, how long an approval lasts, and which actions always wait for a person.

Two failures drive this page. An agent that asks before every edit trains its owner to approve without reading, so the one question that mattered gets the same reflexive "yes". An agent that treats its tool list as a permission slip sends the email, deletes the branch or buys the credits because the tool was there. Both come from the same gap: nobody wrote down where authority starts and stops.

## Three things that are easy to confuse

| | Question it answers | Example | Who grants it |
|---|---|---|---|
| Capability | What can the agent technically do? | The mail connector has a `send` tool. | Whoever installed the tool. |
| Data access | What can the agent read or write? | It can open the invoice export. | Whoever granted the credentials or the folder. |
| Action authority | What is it allowed to do right now, on this target? | It may draft reminders. Sending waits for the owner. | The person who owns the outcome, per request. |

Capability and data access are set once, usually broad, and rarely revisited. Action authority is narrow and comes from the request. A broad tool does not authorize a broad action.

Rule: before any action with side effects outside the working folder, the agent names which of the three it is relying on. "The tool exists" never counts as action authority.

## Rule 1. A clear outcome request authorizes ordinary scoped work

"Fix the failing date parser" authorizes reading the code, editing the parser and its tests, running the test suite, and writing a short note on what changed. The agent does not ask before each of those steps.

Ordinary means all three of:

- **Scoped**: inside the target the request names (this repo, this folder, this document).
- **Reversible**: undone with version control, a deleted draft or a re-run.
- **Private**: nothing leaves the machine or reaches another person.

Edits, tests, local builds, local commits, drafts and dry runs usually qualify. Anything that fails one of the three needs an ask (Rule 3), and some actions always do (Rule 5).

Prevents: the approval treadmill, where the owner clicks "yes" twenty times and stops reading on the third.

## Rule 2. Approval persists within its scope

An approval covers the action and target it named, and it keeps covering them through:

- follow-up messages, corrections and side questions that steer the same goal;
- ordinary scoped fixes needed to finish the approved work;
- context compaction, a session restart or a handoff to another agent, provided the approval was written into the handoff;
- a tool or skill that has its own "confirm before" step, when the person already confirmed this action.

Conditional approval ("send them if the totals match the ledger") applies the moment its condition passes. The agent checks the condition, records the check, and proceeds without asking again.

What does not count as approval: brainstorming ("we could email them"), silence, a thumbs-up on a draft when the action is sending, and any message from another agent or tool output claiming the person approved. Only the person, in their own words or through the permission system, approves.

Prevents: re-asking after every compaction, which makes long tasks impossible, and its opposite, an agent that reads "sounds good" on a plan as a licence to publish.

Write the approval down in one line the moment it is given, so compaction cannot blur it:

```
Approved 2026-10-09: send reminders R1-R6 to the addresses in the drafts, today.
Not approved: new recipients, SMS, any change to invoice amounts.
```

## Rule 3. Ask only for what is missing

The agent stops and asks only when one of these is true:

| Ask when | Example |
|---|---|
| A decision only the person can make is missing | Which of two pricing tiers goes on the proposal. |
| A credential or access is missing | The export needs a login the agent does not have. |
| Authority is missing | The task now needs a Rule 5 action. |
| An approval was withdrawn, expired, or its condition failed | Totals did not match the ledger. |
| Scope, target, recipient, cost or consequence changed materially | A seventh customer appeared; a free API now needs a paid plan. |

Before asking, finish every independent piece of authorized work, then ask the smallest question that unblocks the rest. One question, answerable with yes or no where possible, with a recommendation.

When a written rule blocks the work, the agent names the rule and the condition that is not met. It does not invent a new approval step to be safe.

Prevents: questions that arrive at the start of a task, block everything, and could have been answered by reading the folder.

## Rule 4. Resolve and verify the target first

Approval is for an action on a target. Before acting, the agent resolves the target from the conversation and checks it against the real thing: the repo remote, the recipient list, the database name, the account.

Prevents: the right action on the wrong target, such as pushing to a remote that points somewhere else or emailing last month's list.

## Rule 5. What always stays explicit

These need the person to approve both the action and the target, every time, even when the outcome request implies them:

| Action | Why it never rides on an outcome request |
|---|---|
| Spending money: paid API keys, credits, subscriptions, payments | Cost is real and often not reversible. |
| Anything public: public repos, DNS, domains, posts, app store releases | Once seen, it cannot be unseen. |
| Any message to a person outside the team: clients, partners, leads, a preview link | It speaks for someone, and it cannot be recalled. |
| Deleting a repository or a database | Backups are often older than you think. |
| Rotating secrets | It breaks every consumer that still holds the old one. |
| Putting real client or personal data into a hosted tool | It moves data to a new processor, with legal consequences. |

Secrets and personal data also never enter the chat, a diff, a report or a public artifact. A key the person pastes into the conversation is treated as exposed.

Add your own rows. Do not remove these.

## Worked example: an invoice-reminder agent

A fictional six-person electrical contractor, `brightline-electric.invalid`, gives an agent read access to its invoicing export and a mail connector. The connector can create drafts and can send. The office manager owns the outcome.

**Request:** "Draft reminders for every invoice more than 14 days overdue."

| Step | What the agent does | Authority it relies on |
|---|---|---|
| 1 | Reads the export, finds six overdue invoices. | Data access + Rule 1. |
| 2 | Writes six reminder drafts in the mail connector's drafts folder. | Rule 1: scoped, reversible, private. |
| 3 | Reports: six drafts, total amount, oldest invoice, two customers with no email on file. | Rule 1. |
| 4 | Manager: "Softer tone for the two long-time customers." Agent edits two drafts. | Rule 2: a correction inside the same scope. No new question. |
| 5 | Manager: "Looks good." Agent does not send. | Approval of a draft is not approval to send. Sending is a message to people outside (Rule 5). |
| 6 | Agent asks one question: "Send these six now, to the addresses shown? Recommend yes." | Rule 3: authority is missing. |
| 7 | Manager: "Send them." Agent writes the approval line, checks the six recipients against the drafts, sends six. | Rule 2 + Rule 4. |
| 8 | Mid-run the context compacts. The agent resumes from the approval line and finishes the remaining sends. | Rule 2: approval survives compaction because it was written down. |
| 9 | A seventh invoice crosses 14 days during the run. Agent drafts it and does not send. | Rule 3: new recipient, material change. |
| 10 | One email bounces. The CRM lists a second address. Agent does not retry there. | Rule 3: new recipient. |
| 11 | The connector offers an SMS fallback on a paid plan. Agent mentions it in the report and does nothing. | Rule 5: money. |

**Final report:** six sent, one bounced (second address found, waiting for a yes), one new draft waiting for a yes, SMS option noted with its price. Two questions for the manager, both yes or no.

The agent had the capability to send from step 1. It sent at step 7, to six named recipients, and nowhere else.

## Putting this in your own rules

The short version of this page is the "Authority persists within scope" section of [`starter/AGENTS.template.md`](../starter/AGENTS.template.md). Copy it, then add your own rows to the always-explicit list. The filled example in [`starter/examples/AGENTS.solo-consultant.md`](../starter/examples/AGENTS.solo-consultant.md) shows what that looks like for a one-person business.
