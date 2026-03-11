import type { OCRResponse } from "../types/document";
import { apiClient } from "./client";

export async function uploadDocument(file: File): Promise<{ file_path: string; detected_type: string }> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post("/documents/upload", form);
  return data;
}

export async function runOCR(filePath: string, documentType: string): Promise<OCRResponse> {
  const { data } = await apiClient.post<OCRResponse>("/documents/ocr", {
    file_path: filePath,
    document_type: documentType,
  });
  return data;
}
