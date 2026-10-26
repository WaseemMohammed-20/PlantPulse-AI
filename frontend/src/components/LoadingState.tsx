import { LoaderCircle } from "lucide-react";

export function LoadingState({ label = "Loading analytics" }: { label?: string }) {
  return (
    <div className="page-state">
      <LoaderCircle className="spin" size={28} />
      <strong>{label}</strong>
      <span>Connecting to the PlantPulse API</span>
    </div>
  );
}
