import React, { useState } from "react";
import { Image as ImageIcon, Link2, Type, Loader2, Layers } from "lucide-react";
import clsx from "clsx";
import AnalysisResultCard from "../components/AnalysisResultCard";
import CaptureBreakdown from "../components/CaptureBreakdown";
import { analyzeText, analyzeImage, analyzeImages, analyzeUrl } from "../services/analysisService";

const TABS = [
  { id: "text", label: "Texte", icon: Type },
  { id: "url", label: "Lien produit", icon: Link2 },
  { id: "image", label: "Capture d'écran", icon: ImageIcon },
  { id: "multi", label: "Scan multi-captures", icon: Layers },
];

const MULTI_CAPTURE_MIN = 5;
const MULTI_CAPTURE_MAX = 12;
const MULTI_CAPTURE_RECOMMENDED = 8;

export default function AnalyzePage() {
  const [activeTab, setActiveTab] = useState("text");
  const [textInput, setTextInput] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [multiFiles, setMultiFiles] = useState([]);
  const [multiPreviews, setMultiPreviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleMultiFilesChange = (e) => {
    const files = Array.from(e.target.files || []);
    setMultiFiles(files);
    setMultiPreviews(files.map((file) => URL.createObjectURL(file)));
  };

  const multiCount = multiFiles.length;
  const multiCountValid = multiCount >= MULTI_CAPTURE_MIN && multiCount <= MULTI_CAPTURE_MAX;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      let data;
      if (activeTab === "text") {
        if (!textInput.trim()) throw new Error("Veuillez saisir un texte produit.");
        data = await analyzeText(textInput);
      } else if (activeTab === "url") {
        if (!urlInput.trim()) throw new Error("Veuillez saisir un lien produit.");
        data = await analyzeUrl(urlInput);
      } else if (activeTab === "image") {
        if (!imageFile) throw new Error("Veuillez sélectionner une image.");
        data = await analyzeImage(imageFile);
      } else if (activeTab === "multi") {
        if (!multiCountValid) {
          throw new Error(
            `Veuillez sélectionner entre ${MULTI_CAPTURE_MIN} et ${MULTI_CAPTURE_MAX} captures (${MULTI_CAPTURE_RECOMMENDED} recommandé).`
          );
        }
        data = await analyzeImages(multiFiles);
      }
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || "Une erreur est survenue lors de l'analyse."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analyser un produit</h1>
        <p className="text-gray-500 mt-1">
          Collez un texte, un lien produit ou envoyez une capture d'écran pour détecter les
          pièges avant achat.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex gap-2 mb-5 border-b border-gray-100 pb-4">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                setActiveTab(id);
                setResult(null);
                setError(null);
              }}
              title={label}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                activeTab === id
                  ? "bg-brand-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {activeTab === "text" && (
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder='Ex: "Cooltech CP25 protective case only"'
              rows={5}
              className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          )}

          {activeTab === "url" && (
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://item.taobao.com/item.htm?id=..."
              className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          )}

          {activeTab === "image" && (
            <div>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleImageChange}
                className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-brand-50 file:text-brand-700 file:font-medium hover:file:bg-brand-100"
              />
              {imagePreview && (
                <img
                  src={imagePreview}
                  alt="Aperçu"
                  className="mt-4 max-h-64 rounded-xl border border-gray-200 object-contain"
                />
              )}
            </div>
          )}

          {activeTab === "multi" && (
            <div>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={handleMultiFilesChange}
                className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-brand-50 file:text-brand-700 file:font-medium hover:file:bg-brand-100"
              />

              <p
                className={clsx(
                  "mt-2 text-sm",
                  multiCount === 0
                    ? "text-gray-500"
                    : multiCountValid
                    ? "text-green-600"
                    : "text-red-600"
                )}
              >
                Minimum {MULTI_CAPTURE_MIN}, recommandé {MULTI_CAPTURE_RECOMMENDED}, maximum{" "}
                {MULTI_CAPTURE_MAX} — vous en avez sélectionné {multiCount}.
                {multiCount > 0 && !multiCountValid && (
                  <>
                    {" "}
                    {multiCount < MULTI_CAPTURE_MIN
                      ? `Ajoutez encore au moins ${MULTI_CAPTURE_MIN - multiCount} capture(s).`
                      : `Retirez au moins ${multiCount - MULTI_CAPTURE_MAX} capture(s).`}
                  </>
                )}
              </p>

              {multiPreviews.length > 0 && (
                <div className="mt-4 grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
                  {multiPreviews.map((src, idx) => (
                    <div key={idx} className="relative">
                      <img
                        src={src}
                        alt={`Capture ${idx + 1}`}
                        className="h-20 w-full rounded-lg border border-gray-200 object-cover"
                      />
                      <span className="absolute top-1 left-1 rounded bg-black/60 text-white text-[10px] px-1.5 py-0.5">
                        {idx + 1}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || (activeTab === "multi" && !multiCountValid)}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium px-6 py-3 rounded-xl transition-colors"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {loading ? "Analyse en cours..." : "Analyser"}
          </button>
        </form>

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
            {error}
          </div>
        )}
      </div>

      {result && <AnalysisResultCard result={result} />}
      {result && result.captures && (
        <CaptureBreakdown
          captures={result.captures}
          categoriesCovered={result.categories_covered}
          categoriesMissing={result.categories_missing}
        />
      )}
    </div>
  );
}
