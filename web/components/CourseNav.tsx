"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { coursePath } from "@/lib/courses";

/** The course's three pages. Real links: each has its own URL. */
export default function CourseNav({ code }: { code: string }) {
  const pathname = usePathname();
  const links = [
    { href: coursePath(code), label: "Questions" },
    { href: coursePath(code, "practice"), label: "Practice exam" },
    { href: coursePath(code, "upload"), label: "Upload" },
  ];
  const current = decodeURIComponent(pathname);
  return (
    <nav className="tabs no-print" aria-label={code}>
      {links.map((l) => (
        <Link key={l.href} href={l.href} className="tab" aria-current={decodeURIComponent(l.href) === current ? "page" : undefined}>
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
