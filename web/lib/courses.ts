import type { Course } from "@/lib/api";

/** A course's code as it appears in its URL: "MIT 6.006" → "MIT-6.006". */
export function courseSlug(code: string): string {
  return code.trim().replace(/\s+/g, "-");
}

export function coursePath(code: string, view: "" | "practice" | "upload" = ""): string {
  return "/c/" + encodeURIComponent(courseSlug(code)) + (view ? "/" + view : "");
}

/** The course a URL segment names, matched the way courseSlug builds it. */
export function findCourse(courses: Course[], slug: string): Course | undefined {
  const wanted = decodeURIComponent(slug).toLowerCase();
  return courses.find((c) => courseSlug(c.code).toLowerCase() === wanted);
}
