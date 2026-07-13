/**
 * Sélecteur de langue du rapport d'analyse IA (FR/EN). Ne traduit PAS l'interface
 * statique (menus, boutons, titres de page) — uniquement le contenu généré par l'IA
 * (voir ai_engine/prompts/product_prompts.py::build_system_prompt), transmis via
 * l'en-tête HTTP X-Language injecté par apiClient.js sur chaque appel.
 */
const STORAGE_KEY = "analysis_language";

export const SUPPORTED_LANGUAGES = [
  { code: "fr", label: "FR" },
  { code: "en", label: "EN" },
];

const DEFAULT_LANGUAGE = "fr";

export function getLanguage() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return SUPPORTED_LANGUAGES.some((l) => l.code === stored) ? stored : DEFAULT_LANGUAGE;
}

export function setLanguage(code) {
  if (!SUPPORTED_LANGUAGES.some((l) => l.code === code)) return;
  localStorage.setItem(STORAGE_KEY, code);
}
