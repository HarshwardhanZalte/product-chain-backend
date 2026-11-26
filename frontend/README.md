# Product Chain frontend

Responsive React/TypeScript frontend for the existing Product Chain Django REST API.

## Local development

1. Start the Django backend at `http://127.0.0.1:8000` and ensure its required environment and database settings are configured.
2. From this directory, copy `.env.example` to `.env`. Adjust `VITE_BACKEND_URL` if Django runs elsewhere. Leave `VITE_API_BASE_URL` empty for the Vite proxy.
3. Install dependencies and start Vite:

   ```sh
   npm install
   npm run dev
   ```

Vite proxies `/api`, `/panel`, and `/media` to the backend. `VITE_API_BASE_URL` can instead point to a deployed API; configure backend CORS for that frontend origin.

For browser-based consumer verification, set the backend's `PRODUCT_VERIFICATION_FRONTEND_URL` to this frontend's public origin (for example `https://your-frontend.onrender.com`). New QR codes then open the React verification page; regenerate existing QR codes from the Factory product view after changing this setting.

## Build and checks

```sh
npm run build
npm run lint
```

The production build is written to `dist/`. Client routes require the hosting platform to serve `index.html` for SPA paths.

## Backend boundaries

- Participant authentication uses the existing JWT endpoints. Administrator access links to the existing Django session panel at `/panel/login/`.
- Public QR scanning and verification use the existing product verification API. Certificates remain behind the backend's private download route.
- Organization creation, selection, and onboarding are removed. Users complete only their role profile; old organization links are optional backend legacy data. The frontend does not add blockchain behavior or simulated business data.
