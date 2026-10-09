"use client";

import { useCallback, useEffect, useState } from "react";
import CoursePicker from "@/components/CoursePicker";
import UploadForm from "@/components/UploadForm";
import QuestionBank from "@/components/QuestionBank";
import ExamGenerator from "@/components/ExamGenerator";
import { errorMessage, listCourses, listTopics } from "@/lib/api";
import type { Course } from "@/lib/api";
import { getClientId } from "@/lib/clientId";

export default function Home() {
  const [clientId, setClientId] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const [selected, setSelected] = useState("");
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [topics, setTopics] = useState<string[]>([]);
  const [uploads, setUploads] = useState(0);

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
  }, []);

  const onUploaded = useCallback(() => setUploads((n) => n + 1), []);

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <header className="no-print">
        <h1 className="text-2xl font-bold">LearnIO</h1>
        <p className="muted text-sm">Upload past exams, browse the question bank, and generate practice exams.</p>
      </header>
      <CoursePicker
        courses={courses}
        selected={selected}
        loading={coursesLoading}
        error={coursesError}
        onSelect={setSelected}
        onCreated={onCreated}
      />
      <UploadForm courses={courses} selected={selected} clientId={clientId} onUploaded={onUploaded} />
      <QuestionBank course={selected} topics={topics} refreshKey={uploads} />
      <ExamGenerator course={selected} topics={topics} clientId={clientId} />
    </main>
  );
}
