import { useState } from "react";
import { exportDocument, submitCorrections } from "../services/api";

export default function ExportPanel({ text, ocrResult }) {
  const [exporting, setExporting] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleExport(format) {
    setExporting(format);
    try {
      const blob = await exportDocument(text, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `document.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Export failed: " + err.message);
    } finally {
      setExporting(null);
    }
  }

  async function handleSubmitCorrections() {
    if (text === ocrResult.full_text) {
      alert("No changes detected. Edit the text first to submit corrections.");
      return;
    }

    const wordCorrections = [];
    const originalWords = ocrResult.full_text.split(/\s+/);
    const correctedWords = text.split(/\s+/);
    const minLen = Math.min(originalWords.length, correctedWords.length);

    let wordIdx = 0;
    for (let i = 0; i < minLen; i++) {
      if (originalWords[i] !== correctedWords[i] && wordIdx < ocrResult.words.length) {
        wordCorrections.push({
          bbox: ocrResult.words[wordIdx]?.bbox || { x: 0, y: 0, w: 0, h: 0 },
          original: originalWords[i],
          corrected: correctedWords[i],
        });
      }
      if (wordIdx < ocrResult.words.length) wordIdx++;
    }

    try {
      await submitCorrections({
        image_id: ocrResult.image_id,
        original_text: ocrResult.full_text,
        corrected_text: text,
        word_corrections: wordCorrections,
      });
      setSubmitted(true);
      setTimeout(() => setSubmitted(false), 3000);
    } catch (err) {
      alert("Failed to submit corrections: " + err.message);
    }
  }

  return (
    <div className="export-panel">
      <div className="export-buttons">
        <button
          className="btn btn-pdf"
          onClick={() => handleExport("pdf")}
          disabled={!!exporting}
        >
          {exporting === "pdf" ? "Exporting..." : "Export PDF"}
        </button>
        <button
          className="btn btn-docx"
          onClick={() => handleExport("docx")}
          disabled={!!exporting}
        >
          {exporting === "docx" ? "Exporting..." : "Export DOCX"}
        </button>
        <button
          className="btn btn-txt"
          onClick={() => handleExport("txt")}
          disabled={!!exporting}
        >
          {exporting === "txt" ? "Exporting..." : "Export TXT"}
        </button>
      </div>
      <button
        className={`btn btn-corrections ${submitted ? "submitted" : ""}`}
        onClick={handleSubmitCorrections}
      >
        {submitted ? "Corrections Saved!" : "Submit Corrections"}
      </button>
    </div>
  );
}
