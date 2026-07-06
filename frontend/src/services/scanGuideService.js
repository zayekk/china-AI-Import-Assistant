/**
 * Service API : étapes du scan guidé ("Scan produit complet").
 */
import apiClient from "./apiClient";

export async function getScanGuideSteps() {
  const { data } = await apiClient.get("/scan-guide/steps");
  return data;
}
