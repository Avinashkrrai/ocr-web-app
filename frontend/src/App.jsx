import { useState, useEffect } from "react";
import ImageUpload from "./components/ImageUpload";
import OCREditor from "./components/OCREditor";
import ExportPanel from "./components/ExportPanel";
import AnalysisPanel from "./components/AnalysisPanel";
import { performOCR, getEngines } from "./services/api";
import "./App.css";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [editedText, setEditedText] = useState("");
  const [error, setError] = useState(null);
  const [isPdf, setIsPdf] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);

  const [engines, setEngines] = useState([]);
  const [engine, setEngine] = useState("auto");
  const [docTypes, setDocTypes] = useState([]);
  const [docType, setDocType] = useState("general");
  const [enhance, setEnhance] = useState(false);

  useEffect(() => {
    getEngines()
      .then((data) => {
        setEngines(data.engines || []);
        setEngine(data.default || "auto");
        setDocTypes(data.doc_types || []);
      })
      .catch(() => {});
  }, []);

  async function handleUpload(file) {
    setError(null);
    setLoading(true);
    setOcrResult(null);
    setIsPdf(false);
    setPdfUrl(null);

    const uploadIsPdf = file.type === "application/pdf" || file.name?.endsWith(".pdf");
    if (!uploadIsPdf) {
      setImageUrl(URL.createObjectURL(file));
    }

    try {
      const result = await performOCR(file, engine, docType, enhance);
      setOcrResult(result);
      setEditedText(result.full_text);
      setIsPdf(result.is_pdf || false);
      if (result.is_pdf && result.original_pdf_url) {
        setPdfUrl(result.original_pdf_url);
      }
      if (result.preview_url) {
        setImageUrl(result.preview_url);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      const code = err.response?.status;
      if (code === 502 || code === 503) {
        setError("Server is starting up — please wait 30 seconds and try again.");
      } else if (err.code === "ECONNABORTED") {
        setError("OCR is taking too long — try a smaller image or fewer pages.");
      } else {
        setError(detail || err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setOcrResult(null);
    setImageUrl(null);
    setEditedText("");
    setError(null);
    setIsPdf(false);
    setPdfUrl(null);
  }

  const engineLabel = ocrResult?.engine === "gemini" ? "Gemini 2.5 Flash" : "Tesseract";
  const docLabel = ocrResult?.doc_type === "land_document" ? "Land Record" : "General";

  return (
    <div className="app">
      <header className="header">
        <h1>OCR Web Application</h1>
        <p className="subtitle">
          Extract editable text from images &amp; PDFs — export as PDF, DOCX, or TXT
        </p>
      </header>

      <main className="main">
        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError(null)}>&times;</button>
          </div>
        )}

        {!ocrResult ? (
          <ImageUpload
            onUpload={handleUpload}
            loading={loading}
            engines={engines}
            engine={engine}
            onEngineChange={setEngine}
            docTypes={docTypes}
            docType={docType}
            onDocTypeChange={setDocType}
            enhance={enhance}
            onEnhanceChange={setEnhance}
          />
        ) : (
          <>
            <div className="toolbar">
              <button className="btn btn-secondary" onClick={handleReset}>
                &larr; Upload New
              </button>
              <span className="engine-badge">{engineLabel}</span>
              <span className="engine-badge doc-badge">{docLabel}</span>
            </div>

            <OCREditor
              ocrResult={ocrResult}
              imageUrl={imageUrl}
              isPdf={isPdf}
              pdfUrl={pdfUrl}
              onTextChange={setEditedText}
            />

            {ocrResult.doc_type === "land_document" && (
              <AnalysisPanel imageId={ocrResult.image_id} />
            )}

            <ExportPanel text={editedText} ocrResult={ocrResult} />
          </>
        )}
      </main>
    </div>
  );
}
