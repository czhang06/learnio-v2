"use client";

import { useAccount } from "@/lib/account";

/** Sign in, or the signed-in person's name and a way out. */
export default function AccountMenu() {
  const account = useAccount();
  if (account.status === "loading") return null;
  if (account.status === "guest") {
    return (
      <button type="button" className="btn-quiet btn-small" onClick={account.signIn}>
        Sign in
      </button>
    );
  }
  const name = account.me?.name || account.me?.email || "Account";
  return (
    <div className="account">
      {account.me?.picture ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img className="avatar" src={account.me.picture} alt="" width={24} height={24} referrerPolicy="no-referrer" />
      ) : (
        <span className="avatar avatar-initial" aria-hidden="true">
          {name.slice(0, 1).toUpperCase()}
        </span>
      )}
      <span className="account-name wide-only">{name}</span>
      <button type="button" className="text-button" onClick={account.signOut}>
        Sign out
      </button>
    </div>
  );
}
