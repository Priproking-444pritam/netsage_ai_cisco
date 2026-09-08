// NetSage AI — backend proxy (Gemini edition)
// ---------------------------------------------------------------
// Holds your Gemini API key server-side and exposes one endpoint,
// POST /api/diagnose, that the frontend (netsage_live.html) calls
// instead of ever touching Google's API directly. This is the ONLY
// safe place for a real API key to live — never in the HTML/JS that
// ships to a browser.
//
// Uses Gemini's native generateContent REST API with responseSchema
// to force valid, well-shaped JSON back — no markdown-fence stripping
// needed. Default model is gemini-3.6-flash (Google's current stable
// GA Flash model as of Aug 2026 — check
// https://ai.google.dev/gemini-api/docs/models if this ever stops
// working, model IDs do change; gemini-3.7-flash is newer but may be
// gated to paid tiers).
// ---------------------------------------------------------------

require("dotenv").config(); // no-op if there's no .env file (e.g. on a host using dashboard env vars)

const express = require("express");
const cors = require("cors");

const app = express();
app.use(cors());              // for a class project, wide-open CORS is fine;
                               // tighten with { origin: "https://your-site.com" } if you want.
app.use(express.json({ limit: "200kb" }));

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-3.6-flash";
const PORT = process.env.PORT || 3000;

const SYSTEM_PROMPT = `You are NetSage AI, a troubleshooting assistant for Cisco-style Packet Tracer lab networks. You help junior network engineers connect a symptom to its real root cause. You are a DRAFTING tool, not an authority: every answer you give is reviewed, and may be edited or rejected, by a human network engineer before anyone acts on it.

RULES:
1. Base root_cause ONLY on evidence present in the provided symptom/show output. Never invent config lines, interface names, or IP addresses that were not given to you.
2. evidence must directly quote or closely paraphrase the specific part of the show output that supports root_cause. If nothing supports a theory, do not propose it.
3. Identify the OSI layer most responsible (L1 Physical, L2 Data Link, L3 Network, L4 Transport, L7 Application).
4. confidence is "Low", "Medium", or "High" depending on how directly the evidence supports the conclusion.
5. next_command is a single real Cisco IOS show command (or client-side command) that would gather the next best evidence.
6. fix_steps must be concrete and specific, not generic advice.
7. If evidence is ambiguous, say so honestly and lower confidence rather than guessing with false certainty.
8. Never state that a fix has been applied — you only recommend; a human applies and verifies it.`;

// Few-shot examples as Gemini chat turns (role "model" instead of "assistant")
const FEWSHOT = [
  { role: "user", parts: [{ text: "CASE ID: EX-01\nCATEGORY: VLAN\nSYMPTOM: PC1 (VLAN 10) cannot ping PC2, both on switch SW1, same subnet.\nTOPOLOGY NOTE: SW1 Fa0/2->PC1, Fa0/3->PC2. Both should be VLAN 10.\nSHOW OUTPUT:\nSW1# show vlan brief | VLAN10 ACCTG active Fa0/2 | VLAN20 SALES active Fa0/3" }] },
  { role: "model", parts: [{ text: JSON.stringify({
    root_cause: "PC2's switch port (Fa0/3) is assigned to VLAN 20 instead of VLAN 10, so it is on a different broadcast domain than PC1.",
    osi_layer: "L2", confidence: "High",
    evidence: "show vlan brief lists Fa0/3 under VLAN20 SALES, not VLAN10 ACCTG where Fa0/2 (PC1) sits.",
    next_command: "show running-config interface Fa0/3",
    fix_steps: "On SW1, enter interface Fa0/3 and run 'switchport access vlan 10' to move PC2 into VLAN 10, then verify with 'show vlan brief'."
  }) }] },
  { role: "user", parts: [{ text: "CASE ID: EX-03\nCATEGORY: Wireless\nSYMPTOM: Wireless clients near two APs experience high latency and frequent disconnects in the overlap zone.\nTOPOLOGY NOTE: AP1 and AP2 cover adjoining rooms with overlapping coverage.\nSHOW OUTPUT:\nAP1# show interface dot11radio0 | Channel: 6 || AP2# show interface dot11radio0 | Channel: 6" }] },
  { role: "model", parts: [{ text: JSON.stringify({
    root_cause: "Both APs are broadcasting on the same 2.4GHz channel (6) in an overlapping coverage area, consistent with co-channel interference, though signal/interference readings have not been captured yet.",
    osi_layer: "L1", confidence: "Low",
    evidence: "AP1 and AP2 both report Channel: 6 on dot11radio0.",
    next_command: "show interface dot11radio0 statistics",
    fix_steps: "Move AP2 to a non-overlapping channel (e.g. 1 or 11) and monitor client disconnect rate before confirming the fix resolved the issue."
  }) }] },
];

const RESPONSE_SCHEMA = {
  type: "OBJECT",
  properties: {
    root_cause: { type: "STRING" },
    osi_layer: { type: "STRING" },
    confidence: { type: "STRING" },
    evidence: { type: "STRING" },
    next_command: { type: "STRING" },
    fix_steps: { type: "STRING" },
  },
  required: ["root_cause", "osi_layer", "confidence", "evidence", "next_command", "fix_steps"],
};

app.get("/", (req, res) => {
  res.json({ ok: true, service: "netsage-ai-proxy", model: GEMINI_MODEL });
});

app.post("/api/diagnose", async (req, res) => {
  if (!GEMINI_API_KEY) {
    return res.status(500).json({ error: "GEMINI_API_KEY is not set on the server. Add it as an environment variable and redeploy." });
  }

  const { symptom, cliOutput, category } = req.body || {};
  if (!symptom || !cliOutput) {
    return res.status(400).json({ error: "Both 'symptom' and 'cliOutput' are required." });
  }

  const userContent = `CASE ID: LIVE-${Date.now()}\nCATEGORY: ${category || "Unspecified"}\nSYMPTOM: ${symptom}\nTOPOLOGY NOTE: (not provided — client-submitted live case)\nSHOW OUTPUT:\n${cliOutput}\n\nDiagnose this case following your system instructions.`;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;

  try {
    const geminiRes = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
      },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents: [...FEWSHOT, { role: "user", parts: [{ text: userContent }] }],
        generationConfig: {
          responseMimeType: "application/json",
          responseSchema: RESPONSE_SCHEMA,
          maxOutputTokens: 2000,
        },
      }),
    });

    if (!geminiRes.ok) {
      const errText = await geminiRes.text();
      console.error("Gemini API error:", geminiRes.status, errText);
      return res.status(502).json({ error: `Gemini API responded ${geminiRes.status}` });
    }

    const data = await geminiRes.json();

    const blockReason = data.promptFeedback?.blockReason;
    if (blockReason) {
      console.error("Gemini blocked the request:", blockReason);
      return res.status(502).json({ error: `Gemini blocked this request (${blockReason}).` });
    }

    const raw = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!raw) {
      console.error("Gemini response had no text, full response:", JSON.stringify(data));
      return res.status(502).json({ error: "Gemini response had no content — it may have hit the output token limit or a safety filter." });
    }

    // responseSchema should guarantee clean JSON, but strip fences defensively anyway
    const clean = raw.trim().replace(/^```json/i, "").replace(/^```/, "").replace(/```$/, "").trim();
    const diagnosis = JSON.parse(clean);

    const required = ["root_cause", "osi_layer", "confidence", "evidence", "next_command", "fix_steps"];
    for (const key of required) {
      if (!(key in diagnosis)) {
        return res.status(502).json({ error: `Model response missing '${key}'.` });
      }
    }

    return res.json(diagnosis);
  } catch (err) {
    console.error("Diagnose route failed:", err);
    return res.status(500).json({ error: "Server error while contacting the AI provider: " + err.message });
  }
});

app.listen(PORT, () => {
  console.log(`NetSage AI proxy listening on port ${PORT}`);
  console.log(`GEMINI_API_KEY set: ${Boolean(GEMINI_API_KEY)}`);
  console.log(`Using model: ${GEMINI_MODEL}`);
});
