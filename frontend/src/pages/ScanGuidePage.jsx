import React, { useEffect, useState } from "react";
import {
  Loader2,
  CheckCircle2,
  Circle,
  SkipForward,
  ListChecks,
  ArrowLeft,
  RotateCcw,
} from "lucide-react";
import clsx from "clsx";
import AnalysisResultCard from "../components/AnalysisResultCard";
import CaptureBreakdown from "../components/CaptureBreakdown";
import { getScanGuideSteps } from "../services/scanGuideService";
import { analyzeImagesGuided } from "../services/analysisService";
import {
  compressImageIfNeeded,
  assertBatchSizeIsSafe,
  formatBytes,
} from "../utils/imageCompression";

const CATEGORY_LABELS = {
  main_page: "Page principale",
  product_info: "Infos produit",
  shop: "Boutique",
  reviews: "Avis clients",
  shipping: "Livraison",
};

export default function ScanGuidePage() {
  const [steps, setSteps] = useState([]);
  const [loadingSteps, setLoadingSteps] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [currentIndex, setCurrentIndex] = useState(0);
  // capturesByStep: { [stepNumber]: { file, previewUrl, category } }
  const [capturesByStep, setCapturesByStep] = useState({});
  const [pendingFile, setPendingFile] = useState(null);
  const [pendingPreview, setPendingPreview] = useState(null);
  const [compressingStep, setCompressingStep] = useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getScanGuideSteps();
        if (!cancelled) setSteps(data);
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.data?.detail || err.message || "Impossible de charger les étapes du scan guidé."
          );
        }
      } finally {
        if (!cancelled) setLoadingSteps(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Quand on arrive sur une étape, pré-remplit avec la capture déjà faite (permet de
  // revenir en arrière et recapturer facilement sans perdre le contexte).
  useEffect(() => {
    const step = steps[currentIndex];
    if (step && capturesByStep[step.step]) {
      setPendingFile(capturesByStep[step.step].file);
      setPendingPreview(capturesByStep[step.step].previewUrl);
    } else {
      setPendingFile(null);
      setPendingPreview(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, steps]);

  const requiredSteps = steps.filter((s) => s.required);
  const allRequiredCaptured =
    requiredSteps.length > 0 && requiredSteps.every((s) => capturesByStep[s.step]);

  const wizardComplete = steps.length > 0 && currentIndex >= steps.length;
  const currentStep = !wizardComplete ? steps[currentIndex] : null;

  const orderedCaptures = steps
    .map((s) => ({ step: s, capture: capturesByStep[s.step] }))
    .filter((entry) => entry.capture);

  const resetPending = () => {
    setPendingFile(null);
    setPendingPreview(null);
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setCompressingStep(true);
    try {
      // Compression côté client avant tout (évite les 413 sur mobile — voir
      // frontend/src/utils/imageCompression.js pour le détail de la stratégie).
      const { file: compressed } = await compressImageIfNeeded(file);
      setPendingFile(compressed);
      setPendingPreview(URL.createObjectURL(compressed));
    } catch (err) {
      setError(err.message || "Impossible de traiter cette image.");
    } finally {
      setCompressingStep(false);
    }
  };

  const handleCaptureStep = () => {
    if (!currentStep || !pendingFile) return;
    setCapturesByStep((prev) => ({
      ...prev,
      [currentStep.step]: {
        file: pendingFile,
        previewUrl: pendingPreview,
        category: currentStep.category,
      },
    }));
    setCurrentIndex((idx) => idx + 1);
  };

  const handleSkipStep = () => {
    if (!currentStep || currentStep.required) return;
    setCurrentIndex((idx) => idx + 1);
  };

  const handlePrevious = () => {
    if (currentIndex === 0) return;
    setCurrentIndex((idx) => idx - 1);
  };

  const goToStep = (stepNumber) => {
    const idx = steps.findIndex((s) => s.step === stepNumber);
    if (idx === -1) return;
    setCurrentIndex(idx);
  };

  const handleAnalyze = async () => {
    setError(null);
    setResult(null);
    setAnalyzing(true);
    try {
      const ordered = steps.map((s) => capturesByStep[s.step]).filter(Boolean);
      const files = ordered.map((c) => c.file);
      const categories = ordered.map((c) => c.category);
      // Garde-fou final : chaque capture a déjà été compressée individuellement
      // à son étape, mais on revérifie le total avant l'envoi réseau plutôt que
      // de laisser la plateforme renvoyer un 413 brut.
      assertBatchSizeIsSafe(files);
      const data = await analyzeImagesGuided(files, categories);
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || "Une erreur est survenue lors de l'analyse."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRestart = () => {
    setCurrentIndex(0);
    setCapturesByStep({});
    resetPending();
    setResult(null);
    setError(null);
  };

  const displayStepNumber = wizardComplete ? steps.length : currentIndex + 1;
  const progressPercent = steps.length > 0 ? (orderedCaptures.length / steps.length) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Scan produit complet</h1>
        <p className="text-gray-500 mt-1">
          Un parcours guidé en jusqu'à 12 étapes pour capturer méthodiquement une fiche produit,
          au lieu d'envoyer des captures au hasard.
        </p>
      </div>

      {loadingSteps && (
        <div className="bg-white rounded-2xl border border-gray-200 p-10 flex items-center justify-center text-gray-500 gap-2">
          <Loader2 size={18} className="animate-spin" /> Chargement des étapes du scan guidé...
        </div>
      )}

      {loadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
          {loadError}
        </div>
      )}

      {!loadingSteps && !loadError && !result && (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-200 p-6 space-y-5">
            {/* Barre de progression */}
            <div>
              <div className="flex items-center justify-between text-sm font-medium text-gray-600 mb-1.5">
                <span>
                  Étape {displayStepNumber} / {steps.length}
                </span>
                <span>{orderedCaptures.length} capture(s) enregistrée(s)</span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full bg-brand-600 transition-all"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {!wizardComplete && currentStep && (
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="text-lg font-semibold text-gray-900">{currentStep.instruction}</h2>
                  <span
                    className={clsx(
                      "shrink-0 inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
                      currentStep.required
                        ? "bg-red-50 text-red-700 border-red-200"
                        : "bg-gray-100 text-gray-600 border-gray-200"
                    )}
                  >
                    {currentStep.required ? "Obligatoire" : "Optionnelle"}
                  </span>
                </div>
                <p className="text-sm text-gray-500">
                  Catégorie : <span className="font-medium">{CATEGORY_LABELS[currentStep.category]}</span>
                </p>

                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileSelect}
                  disabled={compressingStep}
                  className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-brand-50 file:text-brand-700 file:font-medium hover:file:bg-brand-100 disabled:opacity-60"
                />

                {compressingStep && (
                  <p className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 size={14} className="animate-spin" /> Compression de l'image en cours...
                  </p>
                )}

                {pendingPreview && (
                  <>
                    <img
                      src={pendingPreview}
                      alt={`Aperçu étape ${currentStep.step}`}
                      className="max-h-64 rounded-xl border border-gray-200 object-contain"
                    />
                    {pendingFile && (
                      <p className="text-xs text-gray-400">
                        Taille après compression : {formatBytes(pendingFile.size)}
                      </p>
                    )}
                  </>
                )}

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handlePrevious}
                    disabled={currentIndex === 0}
                    className="inline-flex items-center gap-2 rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ArrowLeft size={16} /> Précédent
                  </button>

                  <button
                    type="button"
                    onClick={handleCaptureStep}
                    disabled={!pendingFile || compressingStep}
                    className="inline-flex items-center gap-2 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-5 py-2.5 text-sm transition-colors"
                  >
                    <CheckCircle2 size={16} /> Capturer cette étape
                  </button>

                  {!currentStep.required && (
                    <button
                      type="button"
                      onClick={handleSkipStep}
                      className="inline-flex items-center gap-2 rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50"
                    >
                      <SkipForward size={16} /> Passer cette étape
                    </button>
                  )}
                </div>
              </div>
            )}

            {wizardComplete && (
              <div className="space-y-4 text-center py-6">
                <CheckCircle2 size={40} className="mx-auto text-green-600" />
                <h2 className="text-lg font-semibold text-gray-900">Parcours terminé !</h2>
                <p className="text-sm text-gray-500">
                  Vous avez complété les {steps.length} étapes du scan guidé ({orderedCaptures.length}{" "}
                  capture(s) au total). Vous pouvez lancer l'analyse dès maintenant.
                </p>
                <button
                  type="button"
                  onClick={handleAnalyze}
                  disabled={analyzing || !allRequiredCaptured}
                  className="inline-flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium px-6 py-3 rounded-xl transition-colors"
                >
                  {analyzing && <Loader2 size={16} className="animate-spin" />}
                  {analyzing ? "Analyse en cours..." : "Lancer l'analyse"}
                </button>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
                {error}
              </div>
            )}
          </div>

          {/* Résumé des captures + bouton de fin anticipée */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4 h-fit">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
              <ListChecks size={16} /> Captures ({orderedCaptures.length}/{steps.length})
            </h3>

            {!wizardComplete && (
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={!allRequiredCaptured || analyzing}
                className={clsx(
                  "w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors",
                  allRequiredCaptured
                    ? "bg-brand-600 hover:bg-brand-700 text-white"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                )}
              >
                {analyzing && <Loader2 size={16} className="animate-spin" />}
                Terminer et analyser maintenant
              </button>
            )}
            {!allRequiredCaptured && (
              <p className="text-xs text-gray-400">
                Les {requiredSteps.length} étapes obligatoires doivent être capturées avant de
                pouvoir terminer le scan.
              </p>
            )}

            {orderedCaptures.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Aucune capture pour le moment.</p>
            ) : (
              <ul className="space-y-2 max-h-96 overflow-y-auto">
                {orderedCaptures.map(({ step, capture }) => (
                  <li
                    key={step.step}
                    className="flex items-center gap-3 rounded-xl border border-gray-100 p-2"
                  >
                    <img
                      src={capture.previewUrl}
                      alt={`Étape ${step.step}`}
                      className="h-12 w-12 rounded-lg object-cover border border-gray-200 shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-gray-700">
                        Étape {step.step} {step.required && <span className="text-red-600">*</span>}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {CATEGORY_LABELS[step.category]} · {formatBytes(capture.file.size)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => goToStep(step.step)}
                      className="text-xs font-medium text-brand-600 hover:text-brand-700 shrink-0"
                    >
                      Revoir
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {requiredSteps.length > 0 && (
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 mb-1.5">Étapes obligatoires</p>
                <ul className="space-y-1">
                  {requiredSteps.map((s) => (
                    <li key={s.step} className="flex items-center gap-2 text-xs text-gray-600">
                      {capturesByStep[s.step] ? (
                        <CheckCircle2 size={14} className="text-green-600 shrink-0" />
                      ) : (
                        <Circle size={14} className="text-gray-300 shrink-0" />
                      )}
                      {CATEGORY_LABELS[s.category]}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleRestart}
              className="inline-flex items-center gap-2 rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50"
            >
              <RotateCcw size={16} /> Recommencer un scan
            </button>
          </div>
          <AnalysisResultCard result={result} />
          <CaptureBreakdown
            captures={result.captures}
            categoriesCovered={result.categories_covered}
            categoriesMissing={result.categories_missing}
          />
        </div>
      )}
    </div>
  );
}
