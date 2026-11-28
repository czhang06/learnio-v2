"use client";

import { createContext, useContext, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { Attempt, Exam, Result } from "@/lib/api";

/** A practice exam in progress. It lives in the course layout, which stays
 * mounted while you move between a course's pages, so looking at the question
 * bank does not throw away a generated exam. */
export interface ExamState {
  exam: Exam | null;
  marks: Record<number, Result | null>;
  results: Attempt | null;
}

const empty: ExamState = { exam: null, marks: {}, results: null };
const CourseStateContext = createContext<[ExamState, Dispatch<SetStateAction<ExamState>>] | null>(null);

export function CourseStateProvider({ children }: { children: ReactNode }) {
  const state = useState<ExamState>(empty);
  return <CourseStateContext.Provider value={state}>{children}</CourseStateContext.Provider>;
}

export function useExamState(): [ExamState, Dispatch<SetStateAction<ExamState>>] {
  const value = useContext(CourseStateContext);
  if (!value) throw new Error("useExamState needs <CourseStateProvider> above it");
  return value;
}
