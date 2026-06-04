import axios from 'axios';
import sharp from 'sharp';
import { ImageDimensions } from '../types';
import { OcrServiceError, ERROR_CODES } from '../middleware/errorHandler.middleware';
import { logger } from '../logger';

const DOWNLOAD_TIMEOUT_MS = 15_000;
const MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

export async function downloadImage(imageUrl: string): Promise<Buffer> {
  logger.debug('Downloading image', { imageUrl });

  let response;
  try {
    response = await axios.get<Buffer>(imageUrl, {
      responseType: 'arraybuffer',
      timeout: DOWNLOAD_TIMEOUT_MS,
      maxContentLength: MAX_IMAGE_SIZE_BYTES,
      headers: {
        Accept: 'image/*',
      },
    });
  } catch (err) {
    if (axios.isAxiosError(err)) {
      if (err.code === 'ECONNABORTED') {
        throw new OcrServiceError(
          ERROR_CODES.IMAGE_DOWNLOAD_FAILED,
          `Image download timed out after ${DOWNLOAD_TIMEOUT_MS}ms: ${imageUrl}`,
          502
        );
      }
      throw new OcrServiceError(
        ERROR_CODES.IMAGE_DOWNLOAD_FAILED,
        `Failed to download image from ${imageUrl}: ${err.message}`,
        502
      );
    }
    throw new OcrServiceError(
      ERROR_CODES.IMAGE_DOWNLOAD_FAILED,
      `Unexpected error downloading image: ${String(err)}`,
      502
    );
  }

  const buffer = Buffer.from(response.data);
  logger.debug('Image downloaded', { imageUrl, sizeBytes: buffer.length });
  return buffer;
}

export async function getImageDimensions(
  buffer: Buffer
): Promise<ImageDimensions> {
  try {
    const metadata = await sharp(buffer).metadata();
    if (!metadata.width || !metadata.height) {
      throw new OcrServiceError(
        ERROR_CODES.IMAGE_PROCESSING_FAILED,
        'Could not read image dimensions: metadata missing width or height',
        422
      );
    }
    return { width: metadata.width, height: metadata.height };
  } catch (err) {
    if (err instanceof OcrServiceError) throw err;
    throw new OcrServiceError(
      ERROR_CODES.IMAGE_PROCESSING_FAILED,
      `Failed to process image: ${err instanceof Error ? err.message : String(err)}`,
      422
    );
  }
}