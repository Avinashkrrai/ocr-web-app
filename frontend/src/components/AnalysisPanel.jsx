import { useState } from "react";
import { analyzeDocument } from "../services/api";

function FieldRow({ label, value }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="field-row">
      <span className="field-label">{label}</span>
      <span className="field-value">
        {Array.isArray(value) ? value.join(", ") || "—" : String(value)}
      </span>
    </div>
  );
}

function BoundaryTable({ boundaries }) {
  if (!boundaries) return null;
  const dirs = ["north", "south", "east", "west"];
  const hasBoundaries = dirs.some((d) => boundaries[d]);
  if (!hasBoundaries) return null;

  return (
    <div className="boundary-table">
      <span className="field-label">Boundaries</span>
      <table>
        <tbody>
          {dirs.map((d) =>
            boundaries[d] ? (
              <tr key={d}>
                <td className="dir-label">{d.charAt(0).toUpperCase() + d.slice(1)}</td>
                <td>{boundaries[d]}</td>
              </tr>
            ) : null
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function AnalysisPanel({ imageId }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeDocument(imageId);
      setAnalysis(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!analysis && !loading) {
    return (
      <div className="analysis-trigger">
        <button className="btn btn-analyze" onClick={handleAnalyze} disabled={loading}>
          Analyze Document
        </button>
        <span className="analysis-hint">
          Extract structured fields (owner, survey no., area, boundaries...)
        </span>
        {error && <p className="analysis-error">{error}</p>}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="analysis-trigger">
        <div className="spinner" />
        <p>Analyzing document structure...</p>
      </div>
    );
  }

  const f = analysis.fields || {};
  const conf = Math.round((analysis.confidence || 0) * 100);

  return (
    <div className="analysis-panel">
      <div className="analysis-header">
        <h3>Document Analysis</h3>
        <div className={`confidence-badge ${conf >= 80 ? "high" : conf >= 50 ? "mid" : "low"}`}>
          {conf}% confidence
        </div>
      </div>

      <div className="analysis-meta">
        <span className="meta-chip">{analysis.document_type}</span>
        {analysis.language && analysis.language !== "Unknown" && (
          <span className="meta-chip">{analysis.language}</span>
        )}
        {analysis.estimated_date && (
          <span className="meta-chip">{analysis.estimated_date}</span>
        )}
      </div>

      {analysis.summary && (
        <p className="analysis-summary">{analysis.summary}</p>
      )}

      <div className="analysis-fields">
        <FieldRow label="Owner / Party Names" value={f.owner_names} />
        <FieldRow label="Survey / Khasra No." value={f.survey_number} />
        <FieldRow label="Plot / Khata No." value={f.plot_number} />
        <FieldRow label="Area" value={f.area} />
        <FieldRow label="Location" value={f.location} />
        <BoundaryTable boundaries={f.boundaries} />
        <FieldRow label="Registration No." value={f.registration_number} />
        <FieldRow label="Consideration Amount" value={f.consideration_amount} />
        <FieldRow label="Witnesses" value={f.witnesses} />
        <FieldRow label="Additional Details" value={f.additional_details} />
      </div>

      {analysis.uncertain_sections?.length > 0 && (
        <div className="uncertain-sections">
          <h4>Uncertain Sections</h4>
          <ul>
            {analysis.uncertain_sections.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      <button className="btn btn-secondary btn-sm" onClick={handleAnalyze}>
        Re-analyze
      </button>
    </div>
  );
}
