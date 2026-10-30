# LexAI Workspace Guidance

- This repository is a Vite + React JavaScript prototype. Start from `src/main.jsx`; the app is implemented in `src/LexAI.jsx` and styled in `src/lexai.css`.
- Keep mock network behavior behind the async functions in `src/services/mockApi.js`. Replace those functions with API clients when the FastAPI contract is ready; do not add API keys to the frontend.
- Treat legal responses, sources, document analysis and lawyer-directory entries as illustrative mock data. Preserve the disclaimer: LexAI provides legal information, not legal advice, and AI complements professional lawyers rather than replacing them.
- Preserve accessible labels, loading/error/empty states and responsive behavior when changing interactions.
- Run `npm run build` and `npm run lint` from this directory after code changes.
