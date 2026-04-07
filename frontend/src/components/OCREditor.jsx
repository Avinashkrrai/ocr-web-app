import { useState, useRef, useEffect } from "react";

export default function OCREditor({ ocrResult, imageUrl, isPdf, pdfUrl, onTextChange }) {
  const [text, setText] = useState(ocrResult.full_text);
  const [viewMode, setViewMode] = useState(isPdf ? "pdf" : "image");
  const canvasRef = useRef(null);
  const imgRef = useRef(null);

  useEffect(() => {
    setText(ocrResult.full_text);
  }, [ocrResult]);

  useEffect(() => {
    setViewMode(isPdf ? "pdf" : "image");
  }, [isPdf]);

  useEffect(() => {
    if (viewMode === "image") drawOverlay();
  });

  function drawOverlay() {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !img.naturalWidth) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const word of ocrResult.words) {
      const { x, y, w, h } = word.bbox;
      if (word.confidence >= 90) {
        ctx.strokeStyle = "rgba(34, 197, 94, 0.6)";
        ctx.fillStyle = "rgba(34, 197, 94, 0.08)";
      } else if (word.confidence >= 70) {
        ctx.strokeStyle = "rgba(234, 179, 8, 0.7)";
        ctx.fillStyle = "rgba(234, 179, 8, 0.1)";
      } else {
        ctx.strokeStyle = "rgba(239, 68, 68, 0.8)";
        ctx.fillStyle = "rgba(239, 68, 68, 0.12)";
      }
      ctx.lineWidth = 2;
      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);
    }
  }

  function handleTextChange(e) {
    setText(e.target.value);
    onTextChange(e.target.value);
  }

  return (
    <div className="editor-container">
      <div className="editor-panel image-panel">
        <div className="panel-header">
          <h3>Original Document</h3>
          {isPdf && imageUrl && (
            <div className="view-toggle">
              <button
                className={`toggle-btn ${viewMode === "pdf" ? "active" : ""}`}
                onClick={() => setViewMode("pdf")}
              >
                PDF View
              </button>
              <button
                className={`toggle-btn ${viewMode === "image" ? "active" : ""}`}
                onClick={() => setViewMode("image")}
              >
                OCR Analysis
              </button>
            </div>
          )}
        </div>

        {viewMode === "pdf" && pdfUrl ? (
          <div className="pdf-wrapper">
            <iframe
              src={pdfUrl}
              title="Original PDF"
              className="pdf-frame"
            />
          </div>
        ) : (
          <>
            <div className="image-wrapper">
              <img
                ref={imgRef}
                src={imageUrl}
                alt="Uploaded"
                onLoad={drawOverlay}
              />
              <canvas ref={canvasRef} className="overlay-canvas" />
            </div>
            <div className="legend">
              <span className="legend-item">
                <span className="dot green" /> High confidence (&ge;90%)
              </span>
              <span className="legend-item">
                <span className="dot yellow" /> Medium (70-90%)
              </span>
              <span className="legend-item">
                <span className="dot red" /> Low (&lt;70%)
              </span>
            </div>
          </>
        )}
      </div>

      <div className="editor-panel text-panel">
        <h3>Extracted Text</h3>
        <textarea
          value={text}
          onChange={handleTextChange}
          spellCheck={false}
        />
        <p className="word-count">
          {ocrResult.words.length} words detected &middot;{" "}
          {ocrResult.words.filter((w) => w.confidence < 70).length} low-confidence
          {ocrResult.page_count > 1 && ` \u00b7 ${ocrResult.page_count} pages`}
        </p>
      </div>
    </div>
  );
}
