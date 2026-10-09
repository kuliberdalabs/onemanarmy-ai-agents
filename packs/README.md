# packs

A pack is a capability lane: the skills, playbooks and worked examples that let an agent do one kind of job well, such as writing Polish marketing copy or building n8n workflows. Packs build on the rules and tools in core.

Packs are private for now. This folder holds the entry rule and the list of planned lanes, and no pack has entered yet.

## Planned lanes

| Lane | The job |
|---|---|
| `marketing-pl` | Marketing copy in Polish for small service firms: posts, newsletters, landing page sections |
| `local-seo-pl` | Local search for Polish businesses: business profiles, local landing pages, review replies |
| `ads` | Google Ads and Meta ads: campaign structure, ad copy, reading the results back |
| `motion` | Short-form video built in code: scripts, captions, typography, sound |
| `n8n` | Automations in n8n: workflow design, error handling, handover to the owner |

The list will change. A lane that fails its eval stays out, however useful it looks.

## The entry rule

A pack enters this folder, and goes to a client's setup, only when all four hold:

1. **Dogfooded.** We used it in our own daily work on real tasks for at least two weeks, and the tasks are named in the changelog. The problems that turned up are fixed or written down as limits.
2. **Beats the bare model.** An eval runs the same tasks twice, once with the pack and once with the same model and no pack, with the pass criterion written before the first run. Where a person reads the output, blind judges score both without knowing which is which. The pack enters only if it wins on the tasks it claims, and the eval note with its ledger goes to [`evals/`](../evals/SCHEMA.md) under the same rules as the worker evals.
3. **Has a changelog.** Every entry carries the version, the writing model, the judge and the date. Every change after entry is dated, with the eval that justified it when the change affects output.
4. **Passes an independent audit.** A fresh reader goes through the whole pack and checks it for invented facts, leaks from other packs or from our internal work, contradictions and wrong arithmetic in the examples. A fail blocks entry until the findings are fixed and the pack is audited again.

The second point exists because of a measurement. On 2026-10-09 a cheap model's Polish posts passed our mechanical text gate and still scored 4.4 out of 10 from blind judges (details in the [root README](../README.md#why-trust-it)). A pack can make output longer, more formatted and more on-brand without making it better. Without a comparison against the bare model, a pack is extra tokens with a good description.

## How a pack meets your company

A pack is written for nobody in particular. It says "write the weekly post"; it does not know your offer, your clients or the words you never use. That knowledge comes from the context folder that [onboarding](../onboarding/README.md) produces, and the pack reads it at run time. The pack stays generic so it can be evaluated once and reused, and the company context stays with the company.
