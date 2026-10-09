# LearnIO web

Next.js 14 (App Router) + TypeScript + Tailwind frontend for the LearnIO API.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
```

The API must allow CORS from the web origin. All API calls live in `lib/api.ts`.
A random `client_id` is created once and stored in `localStorage`; it is sent with uploads and exam generation.

Question pagination uses a keyset cursor: `GET /api/questions?after=<next_cursor>`, stopping when `next_cursor` is null.
