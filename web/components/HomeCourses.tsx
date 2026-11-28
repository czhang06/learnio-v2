"use client";

import Link from "next/link";
import { useAccount } from "@/lib/account";
import type { Course } from "@/lib/api";
import { coursePath } from "@/lib/courses";

/** Every course, with the ones the signed-in visitor follows first. */
export default function HomeCourses({ courses }: { courses: Course[] }) {
  const { following } = useAccount();
  const mine = courses.filter((c) => following.has(c.code));
  const rest = courses.filter((c) => !following.has(c.code));
  return (
    <>
      {mine.length > 0 && (
        <section aria-labelledby="your-courses" className="home-section">
          <h2 id="your-courses" className="label">
            Your courses
          </h2>
          <CourseList courses={mine} />
        </section>
      )}
      <section aria-labelledby="all-courses" className="home-section">
        <h2 id="all-courses" className="label">
          {mine.length > 0 ? "More courses" : "Courses"}
        </h2>
        <CourseList courses={rest} />
      </section>
    </>
  );
}

function CourseList({ courses }: { courses: Course[] }) {
  return (
    <ul className="course-cards">
      {courses.map((c) => (
        <li key={c.id}>
          <Link href={coursePath(c.code)} className="course-card">
            <span className="course-card-code">{c.code}</span>
            {c.name && <span className="course-card-name">{c.name}</span>}
          </Link>
        </li>
      ))}
    </ul>
  );
}
