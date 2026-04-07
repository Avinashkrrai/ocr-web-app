import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export async function performOCR(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/ocr", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300_000,
  });
  return data;
}

export async function exportDocument(text, format, filename = "document") {
  const { data } = await api.post(
    "/export",
    { text, format, filename },
    { responseType: "blob" }
  );
  return data;
}

export async function submitCorrections(payload) {
  const { data } = await api.post("/corrections", payload);
  return data;
}
