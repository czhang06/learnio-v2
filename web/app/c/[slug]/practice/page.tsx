import { Suspense } from "react";
import { notFound } from "next/navigation";
import ExamGenerator from "@/components/ExamGenerator";
import { serverFindCourse, serverListTopics } from "@/lib/server-api";

export default async function PracticePage({ params }: { params: { slug: string } }) {
  const found = await serverFindCourse(params.slug);
  if (found && !found.course) notFound();
  const code = found?.course?.code;
  if (!code) return null;
  const topics = await serverListTopics(code);
  return (
    <>
      <h2 className="sr-note">Practice exam</h2>
      {/* ExamGenerator reads ?attempt= from the URL. */}
      <Suspense>
        <ExamGenerator course={code} topics={topics ?? []} />
      </Suspense>
    </>
  );
}
