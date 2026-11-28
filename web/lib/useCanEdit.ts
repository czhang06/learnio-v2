"use client";

import { useEffect, useState } from "react";
import { useAccount } from "@/lib/account";
import { getAdminKey } from "@/lib/adminKey";
import { getMode } from "@/lib/api";

/** Whether this visitor may add courses and upload: the API is open (local
 * development), they unlocked it with the admin key, or they are an admin. */
export function useCanEdit(): { canEdit: boolean; unlock: () => void } {
  const account = useAccount();
  const [readOnly, setReadOnly] = useState<boolean | null>(null);
  const [hasKey, setHasKey] = useState(false);

  useEffect(() => {
    setHasKey(getAdminKey() !== null);
    let cancelled = false;
    getMode()
      .then((m) => !cancelled && setReadOnly(m.read_only))
      .catch(() => !cancelled && setReadOnly(true));
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    canEdit: readOnly === false || hasKey || account.me?.is_admin === true,
    unlock: () => setHasKey(true),
  };
}
