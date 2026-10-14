import { AlertDetail } from "@/components/sector/AlertDetail";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  return <AlertDetail id={(await params).id} />;
}
