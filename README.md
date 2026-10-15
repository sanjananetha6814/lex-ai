# LexAI

LexAI is a responsive AI-powered legal information prototype. It helps users get oriented with plain-language explanations, sample document analysis, multilingual answers and lawyer referrals. It is a front-end demo and does not provide legal advice.

## Run locally

```sh
npm install
npm run dev
```

Vite prints the local URL after startup. Create a production build with `npm run build`; run the configured lint check with `npm run lint`.

## Demo flows

- The landing page opens into a product dashboard from **Try LexAI**.
- Chat starts with an indemnity example. Ask a follow-up, switch response language, copy or save an answer, regenerate it, or open Sources.
- The Documents area accepts PDF/JPG/PNG uploads and includes a sample rental agreement. Processing and OCR states are simulated; the report uses illustrative mock data and does not inspect the uploaded file.
- Voice input simulates a transcript and submits a tenant-rights question. No microphone audio is captured.
- Lawyer Connect supports filtering the sample directory by practice area, name, location or language.
- Settings includes a response-language preference, theme toggle and privacy notes.

## Structure and integration seam

- `src/LexAI.jsx` contains the application shell, landing page and view-level interactions.
- `src/lexai.css` contains the responsive design system and view styles.
- `src/services/mockApi.js` is the async mock-service boundary for chat answers and document analysis. Replace these functions with typed API clients when a backend is available.
- `main.py` is an existing FastAPI stub; it is not required to run the frontend and is not connected to the mock client.

The intended production integration can route the client to FastAPI, with an approved model provider, retrieval over reviewed legal sources and an OCR pipeline. Legal references and lawyer profiles shown in this demo are examples, not verified live data. Production use requires jurisdiction-aware legal review, privacy/security review and clear consent before processing documents.

## Important limitation

**LexAI provides legal information, not legal advice. AI complements professional lawyers rather than replacing them.** The prototype's responses, sources, document findings and lawyer directory are mock data. Do not use them for legal decisions or deadlines.
