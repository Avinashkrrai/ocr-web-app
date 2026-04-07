import { useState } from "react";
import ImageUpload from "./components/ImageUpload";
import OCREditor from "./components/OCREditor";
import ExportPanel from "./components/ExportPanel";
import { performOCR } from "./services/api";
import "./App.css";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [editedText, setEditedText] = useState("");
  const [error, setError] = useState(null);
  const [isPdf, setIsPdf] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);

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
      const result = await performOCR(file);
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
      setError(err.response?.data?.detail || err.message);
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

  return (
    <div className="app">
      <header className="header">
        <h1>OCR Web Application</h1>
        <p className="subtitle">
          Extract editable text from images — export as PDF, DOCX, or TXT
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
          <ImageUpload onUpload={handleUpload} loading={loading} />
        ) : (
          <>
            <div className="toolbar">
              <button className="btn btn-secondary" onClick={handleReset}>
                &larr; Upload New Image
              </button>
            </div>
            <OCREditor
              ocrResult={ocrResult}
              imageUrl={imageUrl}
              isPdf={isPdf}
              pdfUrl={pdfUrl}
              onTextChange={setEditedText}
            />
            <ExportPanel text={editedText} ocrResult={ocrResult} />
          </>
        )}
      </main>
    </div>
  );
}
