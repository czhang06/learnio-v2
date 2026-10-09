const API_URL: string = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Course {
  id: number;
  code: string;
  name: string;
}

export interface Question {
  id: number;
  text: string;
  difficulty: number;
  topics: string[];
}

export interface QuestionPage {
  items: Question[];
  next_cursor: number | null;
}

export interface DocumentOut {
  id: number;
  filename: string;
  status: string;
  question_count: number;
}

export interface Exam {
  course_code: string;
  questions: Question[];
}

export interface ExamParams {
  course_code: string;
  topics: string[];
  num_questions: number;
  min_difficulty: number;
  max_difficulty: number;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Turn a FastAPI error body ({detail: string | [{loc,msg}]}) into readable text. */
function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts: string[] = [];
    for (const d of detail) {
      if (d && typeof d === "object") {
        const rec = d as { loc?: unknown; msg?: unknown };
        const loc = Array.isArray(rec.loc) ? rec.loc.filter((x) => x !== "body").join(".") : "";
        const msg = typeof rec.msg === "string" ? rec.msg : "invalid value";
        parts.push(loc ? loc + ": " + msg : msg);
      }
    }
    return parts.length > 0 ? parts.join("; ") : null;
  }
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_URL + path, init);
  } catch {
    throw new ApiError("Could not reach the API at " + API_URL, 0);
  }
  if (!res.ok) {
    let message = "Request failed (" + res.status + ")";
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object") {
        const text = describeDetail((body as { detail?: unknown }).detail);
        if (text) message = text;
      }
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new ApiError(message, res.status);
  }
  return (await res.json()) as T;
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function listCourses(): Promise<Course[]> {
  return request<Course[]>("/api/courses");
}

export function createCourse(code: string, name: string, topics: string[]): Promise<Course> {
  return request<Course>("/api/courses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, name, topics }),
  });
}

export function listTopics(code: string): Promise<string[]> {
  return request<string[]>("/api/courses/" + encodeURIComponent(code) + "/topics");
}

export function uploadDocument(
  courseCode: string,
  kind: string,
  clientId: string,
  file: File
): Promise<DocumentOut> {
  const form = new FormData();
  form.append("course_code", courseCode);
  form.append("kind", kind);
  form.append("client_id", clientId);
  form.append("file", file);
  return request<DocumentOut>("/api/documents", { method: "POST", body: form });
}

export interface QuestionQuery {
  courseCode: string;
  topic?: string;
  difficulty?: number;
  after?: number | null;
  limit?: number;
}

export function listQuestions(q: QuestionQuery): Promise<QuestionPage> {
  const params = new URLSearchParams();
  params.set("course_code", q.courseCode);
  if (q.topic) params.set("topic", q.topic);
  if (q.difficulty) params.set("difficulty", String(q.difficulty));
  if (q.after !== undefined && q.after !== null) params.set("after", String(q.after));
  params.set("limit", String(q.limit ?? 20));
  return request<QuestionPage>("/api/questions?" + params.toString());
}

export function generateExam(params: ExamParams, clientId: string): Promise<Exam> {
  return request<Exam>("/api/exams?client_id=" + encodeURIComponent(clientId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}
