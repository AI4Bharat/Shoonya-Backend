import dotenv from 'dotenv';
import { OcrProvider } from '../types';

dotenv.config();

function getEnv(key: string, defaultValue: string): string {
  return process.env[key] ?? defaultValue;
}

function parsePort(raw: string): number {
  const port = parseInt(raw, 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid PORT value: ${raw}`);
  }
  return port;
}

function parseProvider(raw: string): OcrProvider {
  if (raw === 'openai' || raw === 'google') return raw;
  throw new Error(
    `Invalid DEFAULT_PROVIDER: ${raw}. Must be 'openai' or 'google'`
  );
}

export const config = {
  port: parsePort(getEnv('PORT', '3000')),
  nodeEnv: getEnv('NODE_ENV', 'development'),
  version: '1.0.0',

  openai: {
    apiKey: process.env['OPENAI_API_KEY'] ?? '',
  },

  google: {
    apiKey: process.env['GOOGLE_API_KEY'] ?? '',
  },

  defaultProvider: parseProvider(getEnv('DEFAULT_PROVIDER', 'openai')),

  ocr: {
    timeoutMs: parseInt(getEnv('OCR_TIMEOUT_MS', '30000'), 10),
  },
} as const;

export type Config = typeof config;

export function validateProviderConfig(provider: OcrProvider): void {
  if (provider === 'openai' && !config.openai.apiKey) {
    throw new Error(
      'OPENAI_API_KEY is required when using the openai provider'
    );
  }
  if (provider === 'google' && !config.google.apiKey) {
    throw new Error(
      'GOOGLE_API_KEY is required when using the google provider'
    );
  }
}