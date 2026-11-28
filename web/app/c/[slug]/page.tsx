import { notFound } from "next/navigation";
import QuestionBank from "@/components/QuestionBank";
import { serverFindCourse, serverListQuestions, serverListTopics } from "@/lib/server-api";

/** The question bank: its first page of questions is loaded here, on the server. */
export default async function QuestionsPage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { topic?: string | string[] };
}) {
  const found = await serverFindCourse(params.slug);
  if (found && !found.course) notFound();
  const code = found?.course?.code;
  const topic = typeof searchParams.topic === "string" ? searchParams.topic : "";
  if (!code) return null; // the layout is showing that the API is starting
  const [topics, first] = await Promise.all([serverListTopics(code), serverListQuestions(code, topic || undefined)]);
  return (
    <>
      <h2 className="sr-note">Question bank</h2>
      <QuestionBank key={code + "|" + topic} course={code} topics={topics} topic={topic} initial={first} />
    </>
  );
}
