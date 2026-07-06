/**
 * Service API : endpoints d'analyse produit.
 */
import apiClient from "./apiClient";

export async function analyzeText(text) {
  const { data } = await apiClient.post("/analyze-text", { text });
  return data;
}

export async function analyzeImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post("/analyze-image", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzeImages(files) {
  const formData = new FormData();
  Array.from(files).forEach((file) => {
    formData.append("files", file);
  });
  const { data } = await apiClient.post("/analyze-images", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzeImagesGuided(files, categories) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  categories.forEach((category) => formData.append("categories", category));
  const { data } = await apiClient.post("/analyze-images", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzeUrl(url) {
  const { data } = await apiClient.post("/analyze-url", { url });
  return data;
}

export async function getMyAnalyses(limit = 50) {
  const { data } = await apiClient.get("/analyses", { params: { limit } });
  return data;
}
