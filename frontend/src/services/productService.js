/**
 * Service API : produits, scraping, scoring.
 */
import apiClient from "./apiClient";

export async function listProducts(filters = {}) {
  const { data } = await apiClient.get("/products", { params: filters });
  return data;
}

export async function getProduct(productId) {
  const { data } = await apiClient.get(`/products/${productId}`);
  return data;
}

export async function launchScrape(url, options = {}) {
  const { data } = await apiClient.post("/scrape", {
    url,
    platform: options.platform || "auto",
    fetch_reviews: options.fetchReviews ?? true,
    max_reviews: options.maxReviews ?? 20,
  });
  return data;
}

export async function getProductScore(productId, forceRecompute = false) {
  const { data } = await apiClient.get(`/score/${productId}`, {
    params: { force_recompute: forceRecompute },
  });
  return data;
}
