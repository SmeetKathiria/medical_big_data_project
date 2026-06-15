import { RagSearch } from "../../components/RagSearch";

export default function Page() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">MedIntel Lens</h1>
        <p className="page-subtitle">Review CMS coverage policy, FDA labeling, and PubMed literature with citation-backed briefs and transparent source rationale.</p>
      </div>
      <RagSearch />
    </div>
  );
}
