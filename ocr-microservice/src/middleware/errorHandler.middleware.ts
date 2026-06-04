import { Request, Response, NextFunction } from 'express';
import { ZodError } from 'zod';
import { logger } from '../logger';
import { OcrErrorResponse } from '../types';

export class OcrServiceError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = 'OcrServiceError';
  }
}

export const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_URL: 'INVALID_URL',
  IMAGE_DOWNLOAD_FAILED: 'IMAGE_DOWNLOAD_FAILED',
  IMAGE_PROCESSING_FAILED: 'IMAGE_PROCESSING_FAILED',
  PROVIDER_FAILURE: 'PROVIDER_FAILURE',
  OCR_TIMEOUT: 'OCR_TIMEOUT',
  EMPTY_OCR_RESULT: 'EMPTY_OCR_RESULT',
  UNSUPPORTED_PROVIDER: 'UNSUPPORTED_PROVIDER',
  OCR_PROCESSING_FAILED: 'OCR_PROCESSING_FAILED',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
} as const;

export function errorHandlerMiddleware(
  err: unknown,
  req: Request,
  res: Response,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _next: NextFunction
): void {
  logger.error('Unhandled error', {
    path: req.path,
    method: req.method,
    error: err instanceof Error ? err.message : String(err),
    stack: err instanceof Error ? err.stack : undefined,
  });

  if (err instanceof ZodError) {
    const response: OcrErrorResponse = {
      success: false,
      error: {
        code: ERROR_CODES.VALIDATION_ERROR,
        message: err.errors
          .map((e) => `${e.path.join('.')}: ${e.message}`)
          .join('; '),
      },
    };
    res.status(400).json(response);
    return;
  }

  if (err instanceof OcrServiceError) {
    const response: OcrErrorResponse = {
      success: false,
      error: {
        code: err.code,
        message: err.message,
      },
    };
    res.status(err.statusCode).json(response);
    return;
  }

  const response: OcrErrorResponse = {
    success: false,
    error: {
      code: ERROR_CODES.INTERNAL_ERROR,
      message: 'An unexpected error occurred',
    },
  };
  res.status(500).json(response);
}