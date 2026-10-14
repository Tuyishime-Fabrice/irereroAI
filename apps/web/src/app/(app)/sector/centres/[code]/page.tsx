import { CentreDetail } from "@/components/sector/CentreDetail";

export default async function Page({ params }: { params: Promise<{ code: string }> }) {
  return <CentreDetail code={(await params).code} />;
}
