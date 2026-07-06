/**
 * Service API : estimation du coût d'importation.
 */
import apiClient from "./apiClient";

export async function estimateImport(payload) {
  const { data } = await apiClient.post("/import-estimate", payload);
  return data;
}
