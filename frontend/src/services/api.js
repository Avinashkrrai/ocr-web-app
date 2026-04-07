import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export async function getEngines() {
  const { data } = await api.get("/engines");
  return data;
}

export async function performOCR(file, engine = "auto", docType = "general", enhance = false) {
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams({ engine, doc_type: docType, enhance });
  const { data } = await api.post(`/ocr?${params}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300_000,
  });
  return data;
}

export async function analyzeDocument(imageId) {
  const { data } = await api.post(
    "/analyze",
    { image_id: imageId },
    { timeout: 120_000 },
  );
  return data;
}

export async function exportDocument(text, format, filename = "document") {
  const { data } = await api.post(
    "/export",
    { text, format, filename },
    { responseType: "blob" },
  );
  return data;
}

export async function submitCorrections(payload) {
  const { data } = await api.post("/corrections", payload);
  return data;
}
