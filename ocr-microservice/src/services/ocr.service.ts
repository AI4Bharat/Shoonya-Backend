import { OcrProcessRequest, OcrProcessResponse, ShoonyaPrediction } from '../types';
import { config } from '../config';
import { getProvider } from '../providers/registry';
import { downloadImage, getImageDimensions } from '../utils/imageDownloader';
import { convertBlockToShoonya } from '../utils/coordinateConverter';
import { OcrServiceError, ERROR_CODES } from '../middleware/errorHandler.middleware';
import {
  logger,
  logProviderSelection,
  logOcrExecution,
  logOcrFailure,
} from '../logger';

export async function processOcr(
  request: OcrProcessRequest
): Promise<OcrProcessResponse> {
  const startTime = Date.now();
  const provider = request.provider ?? config.defaultProvider;
  const languages = request.languages ?? [];

  // 1. Log provider selection
  logProviderSelection(provider, languages);

  // 2. Get provider instance
  const ocrProvider = getProvider(provider);

  // 3. Download image
  logger.debug('Downloading image', { imageUrl: request.imageUrl });
  const imageBuffer = await downloadImage(request.imageUrl);

  // 4. Read image dimensions
  const dimensions = await getImageDimensions(imageBuffer);
  logger.debug('Image dimensions resolved', dimensions);

  // 5. Execute OCR
  let ocrResult;
  try {
    ocrResult = await ocrProvider.process(
      imageBuffer,
      languages,
      config.ocr.timeoutMs
    );
  } catch (err) {
    logOcrFailure(provider, request.imageUrl, err);
    throw err;
  }

  // 6. Check for empty result
  const allBlocks = ocrResult.pages.flatMap((p) => p.blocks);
  if (allBlocks.length === 0 && !ocrResult.text) {
    logger.warn('OCR returned empty result', {
      provider,
      imageUrl: request.imageUrl,
    });
    throw new OcrServiceError(
      ERROR_CODES.EMPTY_OCR_RESULT,
      'OCR processing returned no text blocks for the provided image',
      422
    );
  }

  // 7. Convert absolute coordinates to Shoonya percentage format
  const predictions: ShoonyaPrediction[] = allBlocks.map((block) =>
    convertBlockToShoonya(block, dimensions.width, dimensions.height)
  );

  const processingTimeMs = Date.now() - startTime;

  logOcrExecution(provider, request.imageUrl, processingTimeMs, predictions.length);

  // 8. Return Shoonya-compatible response
  return {
    success: true,
    provider,
    processingTimeMs,
    confidence: ocrResult.confidence,
    prediction: predictions,
  };
}