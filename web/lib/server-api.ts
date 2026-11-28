import "server-only";
import type { Course, QuestionPage } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Seconds a response is reused across visitors (Next.js data cache). */
const REVALIDATE = 60;
/** The free API sleeps when idle and takes ~50 s to wake. Rather than hold the
 * page, give up after this long; the browser then loads the data itself. */
const TIMEOUT_MS = 6000;

async function get<T>(path: string, fresh = false): Promise<T | null> {
  try {
    const res = await fetch(API_URL + path, {
      ...(fresh ? { cache: "no-store" as const } : { next: { revalidate: REVALIDATE } }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

export const serverListCourses = () => get<Course[]>("/api/courses");

/** The course a URL names. A course added in the last minute may be missing
 * from the cached list, so look again, uncached, before giving up. Returns
 * undefined for no such course, null when the API did not answer. */
export async function serverFindCourse(slug: string): Promise<{ course?: Course; courses: Course[] } | null> {
  const { findCourse } = await import("@/lib/courses");
  const courses = await serverListCourses();
  if (courses === null) return null;
  const course = findCourse(courses, slug);
  if (course) return { course, courses };
  const fresh = await get<Course[]>("/api/courses", true);
  return fresh === null ? { courses } : { course: findCourse(fresh, slug), courses: fresh };
}

export const serverListTopics = (code: string) =>
  get<string[]>("/api/courses/" + encodeURIComponent(code) + "/topics");

export function serverListQuestions(code: string, topic: string | undefined) {
  const params = new URLSearchParams({ course_code: code, limit: "20" });
  if (topic) params.set("topic", topic);
  return get<QuestionPage>("/api/questions?" + params.toString());
}
