import "next-auth";

declare module "next-auth" {
  interface Session {
    /** Short-lived token for the LearnIO API, or null when accounts are not configured. */
    apiToken: string | null;
  }
}
