"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiUrl } from "@/lib/api";

/** Shown when the server could not reach the API in time: the free tier
 * sleeps after 15 minutes idle. Polls until it answers, then reloads the data. */
export default function ApiWaking() {
  const router = useRouter();
  useEffect(() => {
    let stopped = false;
    async function poll() {
      while (!stopped) {
        try {
          const res = await fetch(apiUrl("/api/health"), { cache: "no-store" });
          if (res.ok) {
            router.refresh();
            return;
          }
        } catch {
          // still asleep
        }
        await new Promise((r) => setTimeout(r, 4000));
      }
    }
    void poll();
    return () => {
      stopped = true;
    };
  }, [router]);

  return (
    <div className="waking" role="status">
      <p className="waking-title">Starting the server</p>
      <p>
        LearnIO&apos;s API runs on a free tier that sleeps after 15 minutes without visitors. The first request wakes it
        up, which takes 30 to 50 seconds. This page fills in by itself once it&apos;s ready.
      </p>
      <div className="waking-bar" aria-hidden="true">
        <span />
      </div>
    </div>
  );
}
