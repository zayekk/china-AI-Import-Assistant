/**
 * Compression/redimensionnement d'images côté client avant upload.
 *
 * Pourquoi : Vercel impose une limite fixe de 4,5 Mo par requête serverless
 * (toutes plateformes/plans confondus), au-delà de laquelle la requête est
 * rejetée AVANT même d'atteindre notre backend (HTTP 413). Les captures d'écran
 * Android en pleine résolution (plusieurs Mo chacune) dépassent facilement ce
 * total dès qu'on en envoie plusieurs (scan multi-captures : 5 à 12 images).
 *
 * La compression se fait via l'API Canvas native du navigateur (aucune
 * dépendance tierce) : redimensionnement raisonnable + réencodage JPEG. On
 * réduit d'abord la qualité JPEG (les artefacts de compression gênent peu
 * l'OCR, y compris pour du chinois), et on ne réduit les dimensions qu'en
 * dernier recours pour ne pas perdre en lisibilité des caractères fins.
 */

// Limite dure de la plateforme Vercel (voir docs/vercel_deployment.md).
export const VERCEL_BODY_LIMIT_BYTES = 4.5 * 1024 * 1024;
// Marge de sécurité pour l'overhead multipart (frontières, en-têtes, champs de
// formulaire additionnels comme les catégories du scan guidé).
const SAFETY_MARGIN_BYTES = 0.5 * 1024 * 1024;
export const FINAL_SAFE_CEILING_BYTES = VERCEL_BODY_LIMIT_BYTES - SAFETY_MARGIN_BYTES; // 4 Mo

// Objectif visé lors de la compression d'un lot (plus conservateur que le
// plafond final, pour absorber les cas où un fichier ne compresse pas aussi
// bien que prévu sans dépasser la limite réelle).
export const BATCH_TARGET_TOTAL_BYTES = 3.5 * 1024 * 1024;
const MAX_BATCH_FILES = 12; // aligné sur la limite du scan multi-captures
export const DEFAULT_PER_FILE_TARGET_BYTES = Math.floor(BATCH_TARGET_TOTAL_BYTES / MAX_BATCH_FILES);
export const SINGLE_IMAGE_TARGET_BYTES = 1.5 * 1024 * 1024;

const MAX_DIMENSION_PX = 1920; // largement suffisant pour la lisibilité OCR
const MIN_DIMENSION_PX = 1000; // plancher : en dessous, risque réel de nuire à l'OCR
const DIMENSION_SHRINK_FACTOR = 0.85;
const INITIAL_QUALITY = 0.85;
const MIN_QUALITY = 0.5;
const QUALITY_STEP = 0.1;

// Si un fichier ne descend toujours pas sous ce seuil après compression
// maximale, on considère que le compresser davantage nuirait trop à l'OCR :
// on le rejette avec un message clair plutôt que de risquer un 413 silencieux.
const PER_FILE_HARD_MAX_BYTES = 2 * 1024 * 1024;

// En dessous de ce seuil, un fichier est déjà assez léger : inutile de le
// réencoder (évite une perte de qualité et un travail CPU superflus).
const SKIP_COMPRESSION_UNDER_BYTES = 250 * 1024;

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`;
}

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      resolve(img);
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`Impossible de lire l'image "${file.name}".`));
    };
    img.src = url;
  });
}

function canvasToBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Échec de l'encodage de l'image."))),
      "image/jpeg",
      quality
    );
  });
}

/**
 * Redimensionne et réencode `img` en JPEG en essayant de rester sous
 * `targetBytes`. Réduit d'abord la qualité (jusqu'à MIN_QUALITY), puis réduit
 * les dimensions et recommence, jusqu'à MIN_DIMENSION_PX. Retourne le
 * meilleur (plus petit) résultat obtenu même si la cible n'est jamais
 * atteinte — l'appelant décide si c'est acceptable.
 */
async function encodeUnderTarget(img, targetBytes) {
  let dimension = MAX_DIMENSION_PX;
  let bestBlob = null;

  while (true) {
    const scale = Math.min(1, dimension / Math.max(img.naturalWidth, img.naturalHeight, 1));
    const width = Math.max(1, Math.round(img.naturalWidth * scale));
    const height = Math.max(1, Math.round(img.naturalHeight * scale));

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, width, height);

    let quality = INITIAL_QUALITY;
    while (quality >= MIN_QUALITY - 1e-9) {
      // eslint-disable-next-line no-await-in-loop
      const blob = await canvasToBlob(canvas, quality);
      if (!bestBlob || blob.size < bestBlob.size) bestBlob = blob;
      if (blob.size <= targetBytes) {
        return blob;
      }
      quality -= QUALITY_STEP;
    }

    if (dimension <= MIN_DIMENSION_PX) {
      break;
    }
    dimension = Math.max(MIN_DIMENSION_PX, Math.round(dimension * DIMENSION_SHRINK_FACTOR));
  }

  return bestBlob;
}

function toJpegFile(blob, originalName) {
  const baseName = originalName.replace(/\.\w+$/, "") || "capture";
  return new File([blob], `${baseName}.jpg`, { type: "image/jpeg" });
}

/**
 * Compresse un fichier image si nécessaire pour rester sous `targetBytes`.
 * Retourne { file, wasCompressed, originalSize, finalSize }.
 * Lève une Error avec un message clair si le fichier reste trop volumineux
 * même après compression maximale.
 */
export async function compressImageIfNeeded(file, targetBytes = DEFAULT_PER_FILE_TARGET_BYTES) {
  if (file.size <= SKIP_COMPRESSION_UNDER_BYTES && file.size <= targetBytes) {
    return { file, wasCompressed: false, originalSize: file.size, finalSize: file.size };
  }

  const img = await loadImage(file);
  const blob = await encodeUnderTarget(img, targetBytes);

  if (blob.size > PER_FILE_HARD_MAX_BYTES) {
    throw new Error(
      `"${file.name}" reste trop volumineux même après compression (${formatBytes(blob.size)}). ` +
        `Essayez une capture d'écran standard plutôt qu'une capture longue/défilante, ou envoyez-en moins à la fois.`
    );
  }

  return {
    file: toJpegFile(blob, file.name),
    wasCompressed: true,
    originalSize: file.size,
    finalSize: blob.size,
  };
}

/**
 * Compresse un lot de fichiers pour rester sous le budget total sûr. La cible
 * par fichier s'adapte au nombre de fichiers du lot (plus il y a de fichiers,
 * plus la cible par fichier est stricte). `onProgress(done, total)` est
 * appelé avant chaque fichier traité.
 *
 * Retourne la liste des résultats (voir compressImageIfNeeded). Lève une
 * Error si la taille totale reste trop élevée après compression individuelle
 * de chaque fichier (garde-fou final avant l'envoi réseau).
 */
export async function compressBatch(files, onProgress) {
  const perFileTarget = Math.max(
    150 * 1024,
    Math.floor(BATCH_TARGET_TOTAL_BYTES / Math.max(1, files.length))
  );

  const results = [];
  for (let i = 0; i < files.length; i++) {
    onProgress?.(i, files.length);
    // eslint-disable-next-line no-await-in-loop
    results.push(await compressImageIfNeeded(files[i], perFileTarget));
  }
  onProgress?.(files.length, files.length);

  const totalSize = results.reduce((sum, r) => sum + r.finalSize, 0);
  if (totalSize > FINAL_SAFE_CEILING_BYTES) {
    throw new Error(
      `La taille totale des images (${formatBytes(totalSize)}) dépasse la limite autorisée ` +
        `(${formatBytes(FINAL_SAFE_CEILING_BYTES)}). Réduisez le nombre de captures envoyées en une fois.`
    );
  }

  return results;
}

/**
 * Garde-fou final : vérifie qu'un ensemble de fichiers déjà compressés reste
 * sous la limite sûre avant l'envoi (utilisé par le scan guidé, où chaque
 * capture est compressée indépendamment au fil des étapes).
 */
export function assertBatchSizeIsSafe(files) {
  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  if (totalSize > FINAL_SAFE_CEILING_BYTES) {
    throw new Error(
      `La taille totale des captures (${formatBytes(totalSize)}) dépasse la limite autorisée ` +
        `(${formatBytes(FINAL_SAFE_CEILING_BYTES)}). Retirez ou recapturez certaines étapes.`
    );
  }
}
