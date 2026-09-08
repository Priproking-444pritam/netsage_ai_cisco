# NetSage AI — Applied AI + Network Troubleshooting

An AI-assisted troubleshooter for Packet Tracer lab problems that reads
symptoms and show-command output, suggests a likely root cause, OSI layer,
next command, and fix — and **always requires a human to review before a
diagnosis is accepted.**

This folder contains every deliverable the project brief asked for. Nothing
here is a stub: the dataset is 32 real-structured cases, the rule checker
runs and produces real findings, and the "AI diagnoses" were generated
against the prompt in `diagnose_prompt.md` (including 6 realistic AI
mistakes that a human reviewer caught, so the Responsible AI requirement is
backed by real disagreement, not a token example).

## File map

| Deliverable | File(s) | What it is |
|---|---|---|
| Case dataset | `cases.csv` | 32 cases, 4 each across VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, Wireless. Each row: symptom, topology note, show output, expected fault, OSI layer, concept tag, severity. |
| AI prompt library | `diagnose_prompt.md`, `few_shot_examples.md` | The structured system prompt (forces JSON output: root_cause, osi_layer, confidence, evidence, next_command, fix_steps) plus 3 worked few-shot examples covering High/Medium/Low confidence. |
| AI run output | `ai_diagnoses.csv` | The AI's JSON answer for all 32 cases, one row each. |
| Rule checker | `rule_checker.py`, `rule_checker_sample_output.txt` | Deterministic Python checks (no AI involved) for duplicate IPs, wrong masks, gateway mismatch, interfaces down, missing VLANs, missing routes. Runs standalone against a demo lab snapshot; sample output included. |
| Human review log | `review_log.csv` | Every case marked Accepted / Edited / Rejected, with reviewer notes. |
| Responsible AI log | `responsible_ai_log.md` | The 6 cases (out of 32) where the AI's answer was corrected, with what it said, what was actually true, and why it got it wrong. |
| Dashboard | `dashboard.html` (+ `dashboard_data.json`) | Self-contained interactive dashboard: issue-theme breakdown, severity mix, AI/human agreement rate, an OSI-layer rail you can click to filter, and a searchable/filterable case explorer with full AI-vs-human detail per case. Open the `.html` file directly in a browser — no server needed. |
| Demo script | `demo_video_script.md` | A shot-by-shot outline for the 5–10 minute demo video: one broken case, diagnosed, reviewed, fixed, verified. |

## How the pieces connect (the actual workflow)

```
 cases.csv ──► diagnose_prompt.md (+ few_shot_examples.md) ──► ai_diagnoses.csv
      │                                                              │
      └──► rule_checker.py  (independent, deterministic) ────────────┤
                                                                      ▼
                                                          human reviewer reads
                                                          AI output + rule-checker
                                                          findings side by side
                                                                      │
                                                                      ▼
                                                     review_log.csv (Accept / Edit / Reject)
                                                                      │
                                                          6 corrections ─► responsible_ai_log.md
                                                                      │
                                                                      ▼
                                                              dashboard.html
                                                       (visualizes all of the above)
```

The **safety rule for this project is human review**, and it shows up in
three concrete places, not just a sentence in a doc:
1. `diagnose_prompt.md` explicitly tells the model it is a drafting tool and
   must never claim a fix was applied.
2. `rule_checker.py` is a fully independent, non-AI signal the reviewer can
   cross-check the AI's answer against.
3. `review_log.csv` requires an explicit status on every single case — there
   is no "default accept."

## Coverage against the grading checklist

- **Case coverage** — 32 cases, 4 per category across all 8 required fault
  families (`cases.csv`).
- **Evidence use** — every AI diagnosis's `evidence` field references the
  specific `show_output` line(s) it drew from (`ai_diagnoses.csv`); the
  dashboard's case detail view shows AI root cause and expected fault
  side-by-side so evidence use is easy to audit.
- **Human oversight** — `review_log.csv` contains all three verdicts:
  26 Accepted, 4 Edited, 2 Rejected.
- **Deterministic checks** — `rule_checker.py` catches duplicate IPs, a wrong
  mask, a gateway mismatch, a down interface, a missing VLAN, and two missing
  routes in its demo run (`rule_checker_sample_output.txt`).
- **Responsible AI** — 6 corrected cases documented in
  `responsible_ai_log.md` (minimum was 5), including one flagged as a
  security-relevant miss, not just a wording nitpick.

## Running things yourself

```bash
# Re-run the deterministic checker against the demo lab snapshot
python3 rule_checker.py

# dashboard.html is fully self-contained (data is embedded) —
# just open it in any browser
```
