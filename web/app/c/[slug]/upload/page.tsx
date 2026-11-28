import { notFound } from "next/navigation";
import UploadPanel from "@/components/UploadPanel";
import { serverFindCourse } from "@/lib/server-api";

export default async function UploadPage({ params }: { params: { slug: string } }) {
  const found = await serverFindCourse(params.slug);
  if (found && !found.course) notFound();
  const code = found?.course?.code;
  if (!code) return null;
  return (
    <>
      <h2 className="sr-note">Upload</h2>
      <UploadPanel course={code} />
    </>
  );
}
