"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import CourseBar from "@/components/CourseBar";
import UploadForm from "@/components/UploadForm";
import AdminUnlock from "@/components/AdminUnlock";
import QuestionBank from "@/components/QuestionBank";
import ExamGenerator from "@/components/ExamGenerator";
import { errorMessage, getMode, listCourses, listTopics } from "@/lib/api";
import type { Course } from "@/lib/api";
import { getAdminKey } from "@/lib/adminKey";
import { useAccount } from "@/lib/account";
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
  const [topicsReady, setTopicsReady] = useState(false);
  const [uploads, setUploads] = useState(0);
  const [tab, setTab] = useState<TabId>("questions");
  const [slow, setSlow] = useState(false);
  // null until the API says; treated as read-only meanwhile so write controls never flash.
  const [readOnly, setReadOnly] = useState<boolean | null>(null);
  const [hasKey, setHasKey] = useState(false);
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const account = useAccount();
  const picked = useRef(false); // set once the visitor chooses a course themselves
  const [followBusy, setFollowBusy] = useState(false);

  useEffect(() => {
    setClientId(getClientId());
    setHasKey(getAdminKey() !== null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    getMode()
      .then((m) => {
        if (!cancelled) setReadOnly(m.read_only);
      })
      .catch(() => {
        if (!cancelled) setReadOnly(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const canEdit = readOnly === false || hasKey || account.me?.is_admin === true;

  // Signed-in visitors land on one of their own courses.
  useEffect(() => {
    const mine = account.me?.courses ?? [];
    if (picked.current || mine.length === 0) return;
    setSelected((cur) => (mine.some((c) => c.code === cur) ? cur : mine[0].code));
  }, [account.me]);

  const choose = useCallback((code: string) => {
    picked.current = true;
    setSelected(code);
  }, []);

  async function toggleFollow(code: string) {
    setFollowBusy(true);
    try {
      await account.follow(code, !account.following.has(code));
    } finally {
      setFollowBusy(false);
    }
  }

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

  // The free-tier API sleeps when idle; if courses take a while, explain why.
  useEffect(() => {
    if (!coursesLoading) return;
    const timer = setTimeout(() => setSlow(true), 2500);
    return () => clearTimeout(timer);
  }, [coursesLoading]);

  useEffect(() => {
    if (!selected) {
      setTopics([]);
      return;
    }
    let cancelled = false;
    setTopicsReady(false);
    listTopics(selected)
      .then((t) => {
        if (!cancelled) setTopics(t);
      })
      .catch(() => {
        if (!cancelled) setTopics([]);
      })
      .finally(() => {
        if (!cancelled) setTopicsReady(true);
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
    <>
      <a className="skip-link" href={tab === "questions" ? "#question-list" : "#main"}>
        Skip to {tab === "questions" ? "questions" : "content"}
      </a>
      <CourseBar
        courses={courses}
        selected={selected}
        loading={coursesLoading}
        error={coursesError}
        onSelect={choose}
        onCreated={onCreated}
        canEdit={canEdit}
        following={account.following}
      />
      <main className="main" id="main" tabIndex={-1}>
        {coursesLoading && slow && (
          <div className="waking" role="status">
            <p className="waking-title">Starting the server</p>
            <p>
              LearnIO&apos;s API runs on a free tier that sleeps after 15 minutes without visitors. The first request
              wakes it up, which takes 30 to 50 seconds. This page fills in by itself once it&apos;s ready.
            </p>
            <div className="waking-bar" aria-hidden="true">
              <span />
            </div>
          </div>
        )}
        {!course ? (
          !coursesLoading && (
            <div className="empty">
              {coursesError ? (
                <>
                  <p className="empty-title">The course list didn&apos;t load</p>
                  <p>{coursesError}. Check that the API is running, then reload this page.</p>
                </>
              ) : (
                <>
                  <p className="empty-title">{canEdit ? "Add your first course" : "No courses yet"}</p>
                  <p>
                    Each course keeps its own bank of questions, pulled from the past exams you upload.
                    {canEdit ? " Use Add course in the top bar." : ""}
                  </p>
                </>
              )}
            </div>
          )
        ) : (
          <>
            <header className="course-head no-print">
              <h1 className="course-code">{course.code}</h1>
              {course.name && <p className="course-name">{course.name}</p>}
              {account.status === "signed-in" && (
                <button
                  type="button"
                  className="btn-quiet btn-small follow-button"
                  aria-pressed={account.following.has(course.code)}
                  disabled={followBusy}
                  onClick={() => toggleFollow(course.code)}
                >
                  {account.following.has(course.code) ? "Following" : "Follow this course"}
                </button>
              )}
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
              <h2 className="sr-note">Question bank</h2>
              <QuestionBank course={selected} topics={topics} topicsReady={topicsReady} refreshKey={uploads} onUploadClick={showUpload} />
            </div>
            <div role="tabpanel" id="panel-practice" aria-labelledby="tab-practice" hidden={tab !== "practice"}>
              <h2 className="sr-note">Practice exam</h2>
              <ExamGenerator course={selected} topics={topics} clientId={clientId} />
            </div>
            <div
              role="tabpanel"
              id="panel-upload"
              aria-labelledby="tab-upload"
              hidden={tab !== "upload"}
              className="no-print"
            >
              {canEdit ? (
                <UploadForm course={selected} clientId={clientId} onUploaded={onUploaded} onViewQuestions={showQuestions} />
              ) : (
                <AdminUnlock onUnlocked={() => setHasKey(true)} />
              )}
            </div>
          </>
        )}
      </main>
    </>
  );
}
