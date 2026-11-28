/** Lifetime of the API token in a session (minted server-side in lib/auth.ts). */
export const API_TOKEN_MINUTES = 15;

/** How often the browser refreshes its session, in seconds: well before tokens expire. */
export const SESSION_REFRESH_SECONDS = (API_TOKEN_MINUTES - 5) * 60;
