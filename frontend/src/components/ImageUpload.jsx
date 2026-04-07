import { useState, useRef } from "react";

export default function ImageUpload({ onUpload, loading }) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  function handleDrag(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) onUpload(e.dataTransfer.files[0]);
  }

  function handleChange(e) {
    if (e.target.files?.[0]) onUpload(e.target.files[0]);
  }

  return (
    <div className="upload-section">
      <div
        className={`drop-zone ${dragActive ? "active" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*,.pdf,application/pdf"
          onChange={handleChange}
          hidden
        />
        {loading ? (
          <div className="spinner-container">
            <div className="spinner" />
            <p>Processing image...</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-text">
              Drag & drop an image here, or <span className="link">browse</span>
            </p>
            <p className="upload-hint">Supports PNG, JPG, TIFF, BMP, PDF</p>
          </>
        )}
      </div>
    </div>
  );
}
