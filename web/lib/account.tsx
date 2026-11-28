"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { SessionProvider, signIn, signOut, useSession } from "next-auth/react";
import { getMe, listSaved, setApiToken, setFollowing, setSaved } from "@/lib/api";
import type { Me } from "@/lib/api";
import { SESSION_REFRESH_SECONDS } from "@/lib/session";

interface Account {
  /** "loading" until the session is known; "guest" also when accounts are not set up. */
  status: "loading" | "guest" | "signed-in";
  me: Me | null;
  following: Set<string>;
  saved: Set<number>;
  follow: (code: string, on: boolean) => Promise<void>;
  save: (questionId: number, on: boolean) => Promise<void>;
  signIn: () => void;
  signOut: () => void;
}

const AccountContext = createContext<Account | null>(null);

export function useAccount(): Account {
  const account = useContext(AccountContext);
  if (!account) throw new Error("useAccount needs <Providers> above it");
  return account;
}

function AccountProvider({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const token = session?.apiToken ?? null;
  // Set during render, not in an effect: children's effects run before ours,
  // and their first requests should already carry the token.
  setApiToken(token);

  const [me, setMe] = useState<Me | null>(null);
  const [saved, setSavedIds] = useState<Set<number>>(new Set());
  const signedIn = status === "authenticated" && token !== null;

  useEffect(() => {
    if (!signedIn) {
      setMe(null);
      setSavedIds(new Set());
      return;
    }
    let cancelled = false;
    getMe()
      .then((m) => !cancelled && setMe(m))
      .catch(() => !cancelled && setMe(null));
    listSaved()
      .then((qs) => !cancelled && setSavedIds(new Set(qs.map((q) => q.id))))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // Re-run only when the person changes, not on every token refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signedIn, session?.user?.email]);

  const follow = useCallback(async (code: string, on: boolean) => {
    await setFollowing(code, on);
    setMe(await getMe());
  }, []);

  const save = useCallback(async (questionId: number, on: boolean) => {
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(questionId);
      else next.delete(questionId);
      return next;
    });
    try {
      await setSaved(questionId, on);
    } catch (err) {
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (on) next.delete(questionId);
        else next.add(questionId);
        return next;
      });
      throw err;
    }
  }, []);

  const value = useMemo<Account>(
    () => ({
      status: status === "loading" ? "loading" : signedIn ? "signed-in" : "guest",
      me,
      following: new Set((me?.courses ?? []).map((c) => c.code)),
      saved,
      follow,
      save,
      signIn: () => void signIn(),
      signOut: () => void signOut(),
    }),
    [status, signedIn, me, saved, follow, save]
  );
  return <AccountContext.Provider value={value}>{children}</AccountContext.Provider>;
}

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider refetchInterval={SESSION_REFRESH_SECONDS} refetchOnWindowFocus>
      <AccountProvider>{children}</AccountProvider>
    </SessionProvider>
  );
}
