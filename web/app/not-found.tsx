import Link from "next/link";
import CourseBar from "@/components/CourseBar";
import SkipLink from "@/components/SkipLink";
import { serverListCourses } from "@/lib/server-api";

export const metadata = { title: "Not found · LearnIO" };

export default async function NotFound() {
  const courses = await serverListCourses();
  return (
    <>
      <SkipLink bank={false} />
      <CourseBar courses={courses} />
      <main className="main" id="main" tabIndex={-1}>
        <header className="course-head">
          <h1 className="course-code">Not found</h1>
          <p className="course-name">There is no course or page at this address.</p>
        </header>
        <p>
          <Link className="text-button" href="/">
            See all courses
          </Link>
        </p>
      </main>
    </>
  );
}
