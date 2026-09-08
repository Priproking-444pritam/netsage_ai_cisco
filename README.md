# NetSage AI — Applied AI + Network Troubleshooting

An AI-assisted troubleshooting console for Cisco-style Packet Tracer lab
networks. It reads a symptom and real show-command output, runs a
deterministic rule check *and* a live AI diagnosis side by side, and
**never lets either one act on its own** — every case is Accepted,
Manually Overridden, or Rejected by a human before it counts as resolved.

Built as a solo project for a Cisco/KIIT applied-AI networking assignment.

---

## What's in this repo

| Path | What it is |
|---|---|
| `netsage_live.html` | The interactive console — paste real CLI output, get a rule-engine finding + live AI diagnosis, review it, browse the full case log, view the analytics dashboard. Single self-contained file, no build step. |
| `dashboard.html` | A static analytics dashboard over the 32-case reference dataset. |
| `cases.csv` | 32 troubleshooting cases across VLAN, Gateway, DHCP, DNS, Routing, ACL, NAT, and Wireless — symptom, topology note, show output, expected fault, OSI layer, concept tag, severity. |
| `ai_diagnoses.csv` | The AI's structured JSON-style answer for every case. |
| `review_log.csv` | Human reviewer verdict (Accepted / Manual Override / Rejected) for every case. |
| `responsible_ai_log.md` | Detailed writeup of every case where a human corrected the AI, including one security-relevant miss. |
| `diagnose_prompt.md`, `few_shot_examples.md` | The structured prompt library — forces JSON output (`root_cause`, `osi_layer`, `confidence`, `evidence`, `next_command`, `fix_steps`) with worked examples. |
| `rule_checker.py`, `rule_checker_sample_output.txt` | A deterministic, non-AI Python script that independently flags duplicate IPs, wrong masks, gateway mismatches, down interfaces, missing VLANs, and missing routes. |
| `backend/` | An optional Node/Express proxy so the live console works for anyone, not just inside Claude — see below. |

## Why it's built this way

Three layers stand between a symptom and a "resolved" label:

1. **Deterministic rule engine** — pure pattern matching against show output, no AI involved, fully explainable.
2. **Structured, evidence-grounded AI diagnosis** — a constrained prompt that forces the model to cite its evidence, state honest confidence, and never claim a fix was applied.
3. **Mandatory human review** — every case gets Accepted, Manually Overridden, or Rejected, with the reasoning logged. Six of the 32 reference cases were corrected by a human reviewer, including one where the AI's confident diagnosis missed a real security-boundary issue entirely.

## Quickstart

### Just want to try the console?
Open `netsage_live.html` in a browser. The rule engine and the whole
UI work immediately, no setup. Live AI diagnosis works out of the box
if you're viewing it inside Claude; for a standalone deploy, see the
backend section below.

### Run the backend proxy (enables live AI anywhere)
The proxy keeps your AI provider's API key server-side — it's never
in the HTML/JS that ships to a browser.

```bash
cd backend
npm install
cp .env.example .env
# open .env and paste your real Gemini key in place of the placeholder
npm start
```

You should see:
```
NetSage AI proxy listening on port 3000
GEMINI_API_KEY set: true
Using model: gemini-3.6-flash
```

Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — no credit card required.

Then open `netsage_live.html`, click **Backend** (top right), enter
`http://localhost:3000/api/diagnose`, click **Save & test**. Once it
says "Connected," every diagnosis in the console goes through your
own backend.

Full deployment instructions (Render, Railway, troubleshooting) are in
[`backend/README.md`](backend/README.md).

### Run the rule checker standalone
```bash
python3 rule_checker.py
```
No dependencies beyond the Python standard library.

## Tech stack

Python · HTML/CSS/JavaScript · Node.js/Express · Chart.js · Google Gemini API (Anthropic Claude API as an in-Claude fallback path)

## Project deliverables checklist

- [x] 32 troubleshooting cases (≥30 required) across 8 fault categories
- [x] Structured AI prompt library with 3 worked few-shot examples
- [x] Deterministic Python rule checker with sample output
- [x] Human review log (Accepted / Manual Override / Rejected on every case)
- [x] Responsible AI log — 6 corrected cases (≥5 required), including a security-relevant miss
- [x] Analytics dashboard — issue themes, severity, AI/human agreement rate
- [x] Live interactive console with real AI calls and a deployable backend

## License

Built for coursework. No license asserted; ask before reuse.
