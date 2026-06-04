import winston from 'winston';
import { config } from '../config';

const { combine, timestamp, errors, json, colorize, simple } = winston.format;

const isDevelopment =
  config.nodeEnv === 'development' || config.nodeEnv === 'test';

const devFormat = combine(
  colorize(),
  timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  errors({ stack: true }),
  simple()
);

const prodFormat = combine(
  timestamp(),
  errors({ stack: true }),
  json()
);

export const logger = winston.createLogger({
  level: isDevelopment ? 'debug' : 'info',
  format: isDevelopment ? devFormat : prodFormat,
  defaultMeta: { service: 'ocr-microservice' },
  transports: [
    new winston.transports.Console({
      silent: config.nodeEnv === 'test',
    }),
  ],
});

export function logRequest(method: string, path: string, body: unknown): void {
  logger.info('Incoming request', { method, path, body });
}

export function logResponse(
  method: string,
  path: string,
  statusCode: number,
  durationMs: number
): void {
  logger.info('Outgoing response', { method, path, statusCode, durationMs });
}

export function logProviderSelection(
  provider: string,
  languages: string[]
): void {
  logger.info('OCR provider selected', { provider, languages });
}

export function logOcrExecution(
  provider: string,
  imageUrl: string,
  durationMs: number,
  blockCount: number
): void {
  logger.info('OCR execution complete', {
    provider,
    imageUrl,
    durationMs,
    blockCount,
  });
}

export function logOcrFailure(
  provider: string,
  imageUrl: string,
  error: unknown
): void {
  logger.error('OCR execution failed', {
    provider,
    imageUrl,
    error: error instanceof Error ? error.message : String(error),
    stack: error instanceof Error ? error.stack : undefined,
  });
}