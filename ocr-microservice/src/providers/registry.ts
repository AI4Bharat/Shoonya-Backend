import { IOcrProvider, OcrProvider } from '../types';
import { OpenAIProvider } from './openai.provider';
import { GoogleProvider } from './google.provider';
import { OcrServiceError, ERROR_CODES } from '../middleware/errorHandler.middleware';

const registry = new Map<OcrProvider, IOcrProvider>([
  ['openai', new OpenAIProvider()],
  ['google', new GoogleProvider()],
]);

export function getProvider(name: OcrProvider): IOcrProvider {
  const provider = registry.get(name);
  if (!provider) {
    throw new OcrServiceError(
      ERROR_CODES.UNSUPPORTED_PROVIDER,
      `Unsupported OCR provider: '${name}'. Supported providers: ${[...registry.keys()].join(', ')}`,
      400
    );
  }
  return provider;
}

export function getSupportedProviders(): OcrProvider[] {
  return [...registry.keys()];
}