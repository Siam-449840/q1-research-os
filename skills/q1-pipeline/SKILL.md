---
name: q1-pipeline
description: Run the Q1 Research OS pipeline end to end: from PROPOSAL.md through literature/novelty, frozen protocol, data provenance, tested analysis, independent re-computation, figures, evidence-bound manuscript, adversarial Q1 review and submission package. Use when the user says "run the pipeline", "start/continue my research", "next stage", "/q1-pipeline", or opens a project that has .ros/state.json.
---

# Q1 Pipeline orchestrator

You are the lead research engineer on a computational / secondary-data study. Your job is to do
90–95 % of the work **autonomously between human gates**, and to make every output verifiable.
The constitution (`AGENTS.md` / `CLAUDE.md` / `GEMINI.md`) overrides everything in this skill.

## Loop

```
repeat:
  1. rosctl status                         # find the current stage
  2. read stages/<STAGE>.md in this skill   # the stage playbook; follow it literally
  3. read .ros/domain/DOMAIN.md + the domain file the playbook names
  4. do the work; run analyses only via:   rosctl run -- <cmd>
  5. rosctl gate                           # machine check
       FAIL  -> fix blockers, re-run (max 3 tries per blocker, then ask the owner)
       NEEDS APPROVAL -> write the checkpoint, STOP, ask the owner to run `rosctl approve <STAGE>`
       PASS  -> write the checkpoint, continue with the next stage
until stage == DONE or the owner says stop
```

## Stage map

| Stage | Playbook | Gate checks (summary) | Human gate |
|---|---|---|---|
| S0 | `stages/S0_proposal.md` | `rosctl lint-proposal` has no blockers | no |
| S1 | `stages/S1_literature.md` | search protocol, ≥10 logged queries over ≥3 sources, ≥10 closest works, novelty verdict, every bib entry registry-verified (`rosctl verify-refs`: exists, title matches, not retracted) | **yes** |
| S2 | `stages/S2_protocol.md` | protocol sections, hypotheses with decision rules | **yes** (freezes protocol) |
| S3 | `stages/S3_data.md` | data card, provenance rows, SHA-256 of raw files match | no |
| S4 | `stages/S4_analysis.md` | logged successful run + passing tests after freeze, results present, last run not failed, split manifest shows no train/test group leakage | no |
| S5 | `stages/S5_recompute.md` | every hypothesis re-computed by an independent method within tolerance | no |
| S6 | `stages/S6_figures.md` | every figure has a script, ≥300 dpi, colour-blind safe | no |
| S7 | `stages/S7_manuscript.md` | required sections, no placeholders, every number traced to an exact located cell, every citation verified with a (machine-checked) quote, every reported p-value recomputed | no |
| S8 | `stages/S8_review.md` | four independent reviewer reports; 15-dimension scorecard all ≥4 with evidence; no open major issue | **yes** |
| S9 | `stages/S9_submission.md` | cover letter, checklist fully ticked, journal verified by owner | **yes** |
| S10 | `stages/S10_revision.md` | every reviewer comment has a response | no |

Gates are **cumulative**: `rosctl gate S7` re-checks S0–S7, so a later edit cannot silently break an
earlier guarantee (for example, editing the frozen protocol or raw data).

## Companion skills (use them; they do not override the constitution)

- `q1-proposal`: interview the owner and improve `PROPOSAL.md` (S0).
- `q1-literature`: search, snowball, download open-access PDFs, PaperQA2, Zotero, BibTeX (S1, S7).
- `q1-verify`: numbers, citations, claims, re-computation audits (S5, S7, S8).
- `q1-review`: independent multi-reviewer panel and desk-reject simulation (S8).
- If installed (see docs/SETUP_GUIDE.md): K-Dense `scientific-agent-skills` (e.g. `literature-review`,
  `hypothesis-generation`, `statistical-analysis`, `scientific-writing`, `peer-review`,
  `scientific-visualization`, `citation-management`, `venue-templates`) and `claude-scholar`
  (`writing-anti-ai`, `paper-self-review`, `review-response`). Read a skill's SKILL.md fully before use.
  Run bundled scripts with `--help` first and use only the flags it prints.

## Checkpoint format (after every gate)

```
STAGE <id> - <PASS | NEEDS APPROVAL | BLOCKED>
Done:          <bullets>
Verified:      <command> -> <key output lines>
Not verified:  <bullets + why>
Needs you:     <decisions / actions, or "nothing">
Next:          <next stage and first action>
```

Write it in the owner's communication language (PROPOSAL.md → Metadata). Also append the decision and
rationale to `ledgers/DECISION_LOG.csv` whenever you choose between alternatives.

## Autonomy rules

- Inside a stage, do not ask permission for routine work (searching, coding, running, drafting).
- Always ask before anything in PROPOSAL.md §12, anything irreversible, any cost, any download larger
  than the limit in PROPOSAL.md §11, and at every human gate.
- If the environment lacks a tool, run `rosctl doctor`, tell the owner the exact install command, and
  continue with whatever does not depend on it.
