import { ReportWizard } from "@/components/caregiver/ReportWizard";

export default async function Page({ params }: { params: Promise<{ code: string }> }) {
  return <ReportWizard centreCode={(await params).code} assisted />;
}
