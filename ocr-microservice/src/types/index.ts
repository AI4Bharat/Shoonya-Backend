// ─── OCR Package Output Types ────────────────────────────────────────────────
import type { Buffer } from 'buffer';

export interface OcrBlock {
  text: string;
  boundingBox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface OcrPage {
  pageNumber: number;
  text: string;
  confidence: number;
  blocks: OcrBlock[];
}

export interface OcrResult {
  text: string;
  confidence: number;
  pages: OcrPage[];
}

// ─── Shoonya Format ──────────────────────────────────────────────────────────

export interface ShoonyaPrediction {
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
  labels: string[];
  rotation: number;
  original_width: number;
  original_height: number;
}

// ─── API Request / Response Types ────────────────────────────────────────────

export type OcrProvider = 'openai' | 'google';

export interface OcrProcessRequest {
  imageUrl: string;
  provider?: OcrProvider;
  languages?: string[];
}

export interface OcrProcessResponse {
  success: true;
  provider: OcrProvider;
  processingTimeMs: number;
  confidence: number;
  prediction: ShoonyaPrediction[];
}

export interface OcrErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

// ─── Image Dimensions ────────────────────────────────────────────────────────

export interface ImageDimensions {
  width: number;
  height: number;
}

// ─── Provider Interface ───────────────────────────────────────────────────────

export interface IOcrProvider {
  readonly name: OcrProvider;
  process(
    imageBuffer: Buffer,
    languages: string[],
    timeoutMs: number
  ): Promise<OcrResult>;
}

// ─── Health Response ─────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}