"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import CourseRail from "@/components/CourseRail";
import UploadForm from "@/components/UploadForm";
import QuestionBank from "@/components/QuestionBank";
import ExamGenerator from "@/components/ExamGenerator";
import { errorMessage, listCourses, listTopics } from "@/lib/api";
import type { Course } from "@/lib/api";
import { getClientId } from "@/lib/clientId";

const TABS = [
  { id: "questions", label: "Questions" },
  { id: "practice", label: "Practice exam" },
  { id: "upload", label: "Upload" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function Home() {
  const [clientId, setClientId] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const [selected, setSelected] = useState("");
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [topics, setTopics] = useState<string[]>([]);
  const [uploads, setUploads] = useState(0);
  const [tab, setTab] = useState<TabId>("questions");
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  useEffect(() => {
    setClientId(getClientId());
  }, []);

  useEffect(() => {
    let cancelled = false;
    listCourses()
      .then((list) => {
        if (cancelled) return;
        setCourses(list);
        setSelected((cur) => cur || (list.length > 0 ? list[0].code : ""));
      })
      .catch((err) => {
        if (!cancelled) setCoursesError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setCoursesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selected) {
      setTopics([]);
      return;
    }
    let cancelled = false;
    listTopics(selected)
      .then((t) => {
        if (!cancelled) setTopics(t);
      })
      .catch(() => {
        if (!cancelled) setTopics([]);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const onCreated = useCallback((course: Course) => {
    setCourses((prev) => prev.concat(course).sort((a, b) => a.code.localeCompare(b.code)));
    setSelected(course.code);
    setTab("upload");
  }, []);

  const onUploaded = useCallback(() => setUploads((n) => n + 1), []);
  const showQuestions = useCallback(() => setTab("questions"), []);
  const showUpload = useCallback(() => setTab("upload"), []);

  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const i = TABS.findIndex((t) => t.id === tab);
    const next = TABS[(i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length];
    setTab(next.id);
    tabRefs.current[next.id]?.focus();
  }

  const course = courses.find((c) => c.code === selected);

  return (
    <div className="app">
      <CourseRail
        courses={courses}
        selected={selected}
        loading={coursesLoading}
        error={coursesError}
        onSelect={setSelected}
        onCreated={onCreated}
      />
      <main className="main">
        <div className="main-inner">
          {!course ? (
            !coursesLoading && (
              <div className="sheet sheet-empty">
                {coursesError ? (
                  <>
                    <p>The course list did not load.</p>
                    <p>{coursesError}. Check that the API is running, then reload this page.</p>
                  </>
                ) : (
                  <>
                    <p>Start by adding a course.</p>
                    <p>
                      Each course keeps its own bank of questions, pulled from the past exams you upload. Use Add a
                      course in the course list.
                    </p>
                  </>
                )}
              </div>
            )
          ) : (
            <>
              <header className="no-print">
                <h1 className="course-title">{course.code}</h1>
                {course.name && <p className="course-subtitle">{course.name}</p>}
              </header>

              <div className="tabs no-print" role="tablist" aria-label={course.code} onKeyDown={onTabKey}>
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    ref={(el) => {
                      tabRefs.current[t.id] = el;
                    }}
                    type="button"
                    role="tab"
                    id={"tab-" + t.id}
                    aria-selected={tab === t.id}
                    aria-controls={"panel-" + t.id}
                    tabIndex={tab === t.id ? 0 : -1}
                    className="tab"
                    onClick={() => setTab(t.id)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Panels stay mounted so a generated exam survives a look at the bank. */}
              <div
                role="tabpanel"
                id="panel-questions"
                aria-labelledby="tab-questions"
                hidden={tab !== "questions"}
                className="no-print"
              >
                <QuestionBank course={selected} topics={topics} refreshKey={uploads} onUploadClick={showUpload} />
              </div>
              <div role="tabpanel" id="panel-practice" aria-labelledby="tab-practice" hidden={tab !== "practice"}>
                <ExamGenerator course={selected} topics={topics} clientId={clientId} />
              </div>
              <div
                role="tabpanel"
                id="panel-upload"
                aria-labelledby="tab-upload"
                hidden={tab !== "upload"}
                className="no-print"
              >
                <UploadForm
                  course={selected}
                  clientId={clientId}
                  onUploaded={onUploaded}
                  onViewQuestions={showQuestions}
                />
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
