# NetSage AI — Backend Proxy (Gemini edition)

This is the piece that makes the "Live AI Diagnosis" button work for
**anyone**, on any device, without them needing Claude at all. It's a
tiny server with one job: hold your API key privately and forward
diagnosis requests to Gemini on the frontend's behalf.

```
Browser (netsage_live.html)  --POST-->  This server  --your key-->  Gemini API
                              <--JSON---              <--JSON------
```

The key never leaves this server. The HTML file only ever talks to
*your* backend's URL — never to Google directly.

## 1. Get a free API key

1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key**. Free tier, no credit card required.
3. Copy it somewhere safe — you'll paste it into an environment variable, never into the frontend code.

## 2. Run it locally first (recommended, 2 minutes)

```bash
cd backend
npm install
cp .env.example .env
# open .env and paste your real key in place of "paste_your_gemini_key_here"
npm start
```

You should see:
```
NetSage AI proxy listening on port 3000
GEMINI_API_KEY set: true
Using model: gemini-3.6-flash
```

Test it works — easiest way is the app itself: open `netsage_live.html`,
click the **Backend** button, enter `http://localhost:3000/api/diagnose`,
click **Save & test**.

Or from the command line (Mac/Linux/WSL):
```bash
curl -X POST http://localhost:3000/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"symptom":"PC lost network connection, interface FastEthernet0/1 is down","cliOutput":"Interface FastEthernet0/1 changed state to administratively down","category":"Other"}'
```
On Windows Command Prompt, put it all on one line instead (no `\` line
continuations, and avoid `%` in the test text — `cmd.exe` treats it
specially):
```
curl -X POST http://localhost:3000/api/diagnose -H "Content-Type: application/json" -d "{\"symptom\":\"PC lost network connection, interface FastEthernet0/1 is down\",\"cliOutput\":\"Interface FastEthernet0/1 changed state to administratively down\",\"category\":\"Other\"}"
```
You should get back a JSON object with `root_cause`, `osi_layer`, `confidence`, `evidence`, `next_command`, `fix_steps`.

## 3. Deploy it somewhere free

**Render.com** is the simplest option for this size of project:

1. Push this `backend/` folder to a GitHub repo (or the whole project — Render lets you set the root directory).
2. On https://render.com, click **New → Web Service**, connect your GitHub repo.
3. Settings:
   - **Root directory:** `backend` (if you pushed the whole project)
   - **Build command:** `npm install`
   - **Start command:** `npm start`
   - **Instance type:** Free
4. Under **Environment**, add `GEMINI_API_KEY` with your real key. Do **not** put it in the code or commit it.
5. Deploy. Render gives you a public URL like `https://netsage-proxy-xxxx.onrender.com`.
6. Your diagnose endpoint is `https://netsage-proxy-xxxx.onrender.com/api/diagnose`.

Other free options that work the same way: **Railway**, **Fly.io**, or a **Cloudflare Worker** (needs a small rewrite since Workers don't run Express, ask if you want that version instead).

Note: Render's free tier sleeps after inactivity — the first request after idle can take ~30-50 seconds to wake up. Fine for a class demo; if that matters for real use, a paid tier or Railway avoids it.

## 4. Point the frontend at it

Open `netsage_live.html` (in Claude, in a browser, anywhere) — no code
editing needed:

1. Click the **Backend** button in the top-right of the header.
2. Paste your deployed URL, e.g. `https://netsage-proxy-xxxx.onrender.com/api/diagnose`.
3. Click **Save & test**. It sends a real test request and tells you immediately if it worked.

Once connected, every "Run Live AI Diagnosis" click goes to your
backend first. The browser remembers the URL (saved locally), so you
only do this once per browser/device.

## Troubleshooting

- **"Could not reach that URL"** — check the deployed service is awake (visit the base URL in a browser, e.g. `https://netsage-proxy-xxxx.onrender.com/` should return `{"ok":true,...}`), and that the path ends in `/api/diagnose`.
- **CORS errors in the browser console** — the server already sends permissive CORS headers via the `cors` package; if you changed that, make sure your frontend's origin is allowed.
- **500 error mentioning GEMINI_API_KEY** — the environment variable isn't set on your host, or it's named wrong. Re-check step 3.4 and that it's exactly `GEMINI_API_KEY`, not `GOOGLE_API_KEY` or similar.
- **502 error, check your terminal** — the real reason is printed there via `console.error("Gemini API error:", ...)`. Common causes:
  - **A key from the wrong product.** Gemini keys only work with Gemini's API. A Groq, OpenAI, or Anthropic key will fail here — get a fresh key specifically from aistudio.google.com/apikey.
  - **Model not found** — Google does retire model IDs. If `gemini-3.6-flash` stops working, check https://ai.google.dev/gemini-api/docs/models for the current stable model and set `GEMINI_MODEL` as an env var to override it without touching code.
  - **Blocked by safety filters** — rare for network troubleshooting text, but if it happens the error will say `Gemini blocked this request (...)` with the reason.

## Switching providers later

Everything provider-specific lives in `server.js`'s `/api/diagnose`
route — the request to Gemini's `generateContent` endpoint and the
`GEMINI_API_KEY` env var. To swap to a different provider, change the
URL, the auth header, and the request/response shape in that one
function; the frontend doesn't need to know or care which provider is
behind your backend.
