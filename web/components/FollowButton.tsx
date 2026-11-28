"use client";

import { useState } from "react";
import { useAccount } from "@/lib/account";

export default function FollowButton({ code }: { code: string }) {
  const account = useAccount();
  const [busy, setBusy] = useState(false);
  if (account.status !== "signed-in") return null;
  const following = account.following.has(code);

  async function toggle() {
    setBusy(true);
    try {
      await account.follow(code, !following);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button type="button" className="btn-quiet btn-small follow-button" aria-pressed={following} disabled={busy} onClick={toggle}>
      {following ? "Following" : "Follow this course"}
    </button>
  );
}
