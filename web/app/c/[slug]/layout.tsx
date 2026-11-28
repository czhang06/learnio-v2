import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import ApiWaking from "@/components/ApiWaking";
import CourseBar from "@/components/CourseBar";
import CourseNav from "@/components/CourseNav";
import FollowButton from "@/components/FollowButton";
import SkipLink from "@/components/SkipLink";
import { CourseStateProvider } from "@/lib/courseState";
import { serverFindCourse } from "@/lib/server-api";

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const found = await serverFindCourse(params.slug);
  return { title: found?.course ? `${found.course.code} · LearnIO` : "LearnIO" };
}

/** Shared by a course's pages. It stays mounted while you move between them,
 * so a practice exam in progress survives a look at the question bank. */
export default async function CourseLayout({ children, params }: { children: ReactNode; params: { slug: string } }) {
  const found = await serverFindCourse(params.slug);
  if (found === null) {
    return (
      <>
        <SkipLink bank={false} />
        <CourseBar courses={null} />
        <main className="main" id="main" tabIndex={-1}>
          <ApiWaking />
        </main>
      </>
    );
  }
  const { course, courses } = found;
  if (!course) notFound();
  return (
    <CourseStateProvider>
      <SkipLink />
      <CourseBar courses={courses} selected={course.code} />
      <main className="main" id="main" tabIndex={-1}>
        <header className="course-head no-print">
          <h1 className="course-code">{course.code}</h1>
          {course.name && <p className="course-name">{course.name}</p>}
          <FollowButton code={course.code} />
        </header>
        <CourseNav code={course.code} />
        {children}
      </main>
    </CourseStateProvider>
  );
}
