import ApiWaking from "@/components/ApiWaking";
import CourseBar from "@/components/CourseBar";
import HomeCourses from "@/components/HomeCourses";
import SkipLink from "@/components/SkipLink";
import { headers } from "next/headers";
import { serverListCourses } from "@/lib/server-api";

export default async function Home() {
  // Render per request rather than at build time: a build while the API is
  // asleep would otherwise bake in the "waking up" page. The course list
  // itself is still cached for a minute (see server-api).
  headers();
  const courses = await serverListCourses();
  return (
    <>
      <SkipLink />
      <CourseBar courses={courses} />
      <main className="main" id="main" tabIndex={-1}>
        <header className="course-head">
          <h1 className="course-code">LearnIO</h1>
          <p className="course-name">Past exams, split into questions you can practise on.</p>
        </header>
        {courses === null ? (
          <ApiWaking />
        ) : courses.length === 0 ? (
          <div className="empty">
            <p className="empty-title">No courses yet</p>
            <p>Each course keeps its own bank of questions, pulled from the past exams you upload.</p>
          </div>
        ) : (
          <HomeCourses courses={courses} />
        )}
      </main>
    </>
  );
}
