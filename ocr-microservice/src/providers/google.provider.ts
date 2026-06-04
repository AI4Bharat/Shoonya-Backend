import axios from 'axios';
import { IOcrProvider, OcrResult } from '../types';
import { OcrServiceError, ERROR_CODES } from '../middleware/errorHandler.middleware';
import { logger } from '../logger';
import { config } from '../config';

const GOOGLE_VISION_URL =
  'https://vision.googleapis.com/v1/images:annotate';

interface Vertex {
  x?: number;
  y?: number;
}

interface BoundingPoly {
  vertices: Vertex[];
}

interface GoogleSymbol {
  text: string;
}

interface GoogleWord {
  symbols: GoogleSymbol[];
}

interface GoogleParagraph {
  words: GoogleWord[];
  boundingBox: BoundingPoly;
  confidence?: number;
}

interface GoogleBlock {
  paragraphs: GoogleParagraph[];
  boundingBox: BoundingPoly;
  confidence?: number;
}

interface GooglePage {
  blocks: GoogleBlock[];
  width: number;
  height: number;
}

interface GoogleVisionResponse {
  responses: Array<{
    fullTextAnnotation?: {
      pages: GooglePage[];
      text?: string;
    };
    error?: {
      code: number;
      message: string;
    };
  }>;
}

function extractBoundingBox(poly: BoundingPoly): {
  x: number;
  y: number;
  width: number;
  height: number;
} {
  const vertices = poly.vertices;
  const xs = vertices.map((v) => v.x ?? 0);
  const ys = vertices.map((v) => v.y ?? 0);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

export class GoogleProvider implements IOcrProvider {
  public readonly name = 'google' as const;

  async process(
    imageBuffer: Buffer,
    _languages: string[],
    timeoutMs: number
  ): Promise<OcrResult> {
    if (!config.google.apiKey) {
      throw new OcrServiceError(
        ERROR_CODES.UNSUPPORTED_PROVIDER,
        'GOOGLE_API_KEY is not configured',
        500
      );
    }

    const base64Image = imageBuffer.toString('base64');

    logger.debug('Calling Google Vision API');

    let visionResponse: GoogleVisionResponse;
    try {
      const response = await axios.post<GoogleVisionResponse>(
        `${GOOGLE_VISION_URL}?key=${config.google.apiKey}`,
        {
          requests: [
            {
              image: { content: base64Image },
              features: [
                { type: 'DOCUMENT_TEXT_DETECTION', maxResults: 1 },
              ],
            },
          ],
        },
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: timeoutMs,
        }
      );
      visionResponse = response.data;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.code === 'ECONNABORTED') {
          throw new OcrServiceError(
            ERROR_CODES.OCR_TIMEOUT,
            `Google Vision OCR request timed out after ${timeoutMs}ms`,
            504
          );
        }
        const status = err.response?.status ?? 500;
        throw new OcrServiceError(
          ERROR_CODES.PROVIDER_FAILURE,
          `Google Vision API error (${status}): ${err.message}`,
          502
        );
      }
      throw new OcrServiceError(
        ERROR_CODES.PROVIDER_FAILURE,
        `Unexpected error calling Google Vision: ${String(err)}`,
        502
      );
    }

    return this.parseResponse(visionResponse);
  }

  private parseResponse(response: GoogleVisionResponse): OcrResult {
    const first = response.responses[0];
    if (!first) {
      throw new OcrServiceError(
        ERROR_CODES.PROVIDER_FAILURE,
        'Google Vision returned an empty response array',
        502
      );
    }

    if (first.error) {
      throw new OcrServiceError(
        ERROR_CODES.PROVIDER_FAILURE,
        `Google Vision error ${first.error.code}: ${first.error.message}`,
        502
      );
    }

    const annotation = first.fullTextAnnotation;
    if (!annotation || annotation.pages.length === 0) {
      return { text: '', confidence: 0, pages: [] };
    }

    const pages = annotation.pages.map((page, idx) => {
      const blocks = page.blocks.flatMap((block) =>
        block.paragraphs.map((para) => {
          const paragraphText = para.words
            .map((w) => w.symbols.map((s) => s.text).join(''))
            .join(' ');

          return {
            text: paragraphText,
            boundingBox: extractBoundingBox(para.boundingBox),
          };
        })
      );

      const pageConfidence =
        page.blocks.reduce((sum, b) => sum + (b.confidence ?? 0.9), 0) /
        Math.max(page.blocks.length, 1);

      return {
        pageNumber: idx + 1,
        text: blocks.map((b) => b.text).join('\n'),
        confidence: pageConfidence,
        blocks,
      };
    });

    const overallConfidence =
      pages.reduce((sum, p) => sum + p.confidence, 0) /
      Math.max(pages.length, 1);

    return {
      text: annotation.text ?? pages.map((p) => p.text).join('\n'),
      confidence: overallConfidence,
      pages,
    };
  }
}