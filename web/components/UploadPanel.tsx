"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AdminUnlock from "@/components/AdminUnlock";
import UploadForm from "@/components/UploadForm";
import { getClientId } from "@/lib/clientId";
import { coursePath } from "@/lib/courses";
import { useCanEdit } from "@/lib/useCanEdit";

export default function UploadPanel({ course }: { course: string }) {
  const router = useRouter();
  const { canEdit, unlock } = useCanEdit();
  const [clientId, setClientId] = useState("");
  useEffect(() => setClientId(getClientId()), []);

  if (!canEdit) return <AdminUnlock onUnlocked={unlock} />;
  return (
    <UploadForm
      course={course}
      clientId={clientId}
      onUploaded={() => router.refresh()}
      onViewQuestions={() => router.push(coursePath(course))}
    />
  );
}
