import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import { SignJWT } from "jose";

/**
 * Sign-in runs here, in the Next.js app. The FastAPI backend lives on another
 * domain and cannot read NextAuth's cookie, so each session also carries a
 * short-lived token for the API, signed with AUTH_API_SECRET, which the API
 * shares and verifies. The browser sends it as `Authorization: Bearer`.
 */

import { API_TOKEN_MINUTES } from "@/lib/session";

/**
 * A username-only login for local testing of several accounts. Only in
 * `next dev` with AUTH_DEV_LOGIN=1, so it can never be enabled in production.
 */
export const devLoginEnabled = process.env.NODE_ENV === "development" && process.env.AUTH_DEV_LOGIN === "1";

function providers(): NextAuthOptions["providers"] {
  const list: NextAuthOptions["providers"] = [];
  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    list.push(
      GoogleProvider({
        clientId: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      })
    );
  }
  if (devLoginEnabled) {
    list.push(
      CredentialsProvider({
        id: "dev",
        name: "a test account",
        credentials: { username: { label: "Username", type: "text", placeholder: "ada" } },
        async authorize(credentials) {
          const name = (credentials?.username || "").trim().toLowerCase().replace(/[^a-z0-9-]/g, "");
          if (!name) return null;
          return { id: "dev-" + name, name, email: name + "@example.test" };
        },
      })
    );
  }
  return list;
}

async function apiToken(claims: { sub?: string; email?: string | null; name?: string | null; picture?: string | null }) {
  const secret = process.env.AUTH_API_SECRET;
  if (!secret || !claims.sub) return null;
  return new SignJWT({ email: claims.email || "", name: claims.name || "", picture: claims.picture || "" })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(claims.sub)
    .setIssuer("learnio-web")
    .setAudience("learnio-api")
    .setIssuedAt()
    .setExpirationTime(API_TOKEN_MINUTES + "m")
    .sign(new TextEncoder().encode(secret));
}

export const authOptions: NextAuthOptions = {
  providers: providers(),
  session: { strategy: "jwt" },
  callbacks: {
    async session({ session, token }) {
      // Called each time the browser reads the session, so the API token is
      // always fresh; the client re-reads it well before it expires.
      session.apiToken = await apiToken(token);
      return session;
    },
  },
};
