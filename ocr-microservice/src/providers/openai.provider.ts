import axios from 'axios';
import { IOcrProvider, OcrResult } from '../types';
import { OcrServiceError, ERROR_CODES } from '../middleware/errorHandler.middleware';
import { logger } from '../logger';
import { config } from '../config';

const OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions';

interface OpenAIMessage {
  role: string;
  content: Array<{
    type: string;
    text?: string;
    image_url?: { url: string; detail: string };
  }>;
}

interface OpenAIResponse {
  choices: Array<{
    message: {
      content: string;
    };
  }>;
}

interface OpenAIBlock {
  text: string;
  boundingBox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence?: number;
}

interface OpenAIOcrStructured {
  text: string;
  confidence: number;
  width: number;
  height: number;
  blocks: OpenAIBlock[];
}

export class OpenAIProvider implements IOcrProvider {
  public readonly name = 'openai' as const;

  private buildSystemPrompt(languages: string[]): string {
    const langHint =
      languages.length > 0
        ? `The image may contain text in: ${languages.join(', ')}.`
        : 'The image may contain text in any language.';

    return (
      `You are an OCR engine. ${langHint} ` +
      'Extract ALL text from the image and return ONLY valid JSON in this exact schema:\n' +
      '{\n' +
      '  "text": "<full concatenated text>",\n' +
      '  "confidence": <0.0-1.0>,\n' +
      '  "width": <image width in pixels>,\n' +
      '  "height": <image height in pixels>,\n' +
      '  "blocks": [\n' +
      '    {\n' +
      '      "text": "<block text>",\n' +
      '      "confidence": <0.0-1.0>,\n' +
      '      "boundingBox": { "x": <int>, "y": <int>, "width": <int>, "height": <int> }\n' +
      '    }\n' +
      '  ]\n' +
      '}\n' +
      'Rules:\n' +
      '- boundingBox values are ABSOLUTE PIXEL coordinates\n' +
      '- x,y = top-left corner of the block\n' +
      '- Return empty blocks array if no text found\n' +
      '- Return ONLY the JSON object, no markdown, no explanation'
    );
  }

  async process(
    imageBuffer: Buffer,
    languages: string[],
    timeoutMs: number
  ): Promise<OcrResult> {
    if (!config.openai.apiKey) {
      throw new OcrServiceError(
        ERROR_CODES.UNSUPPORTED_PROVIDER,
        'OPENAI_API_KEY is not configured',
        500
      );
    }

    const base64Image = imageBuffer.toString('base64');
    const dataUrl = `data:image/jpeg;base64,${base64Image}`;

    const messages: OpenAIMessage[] = [
      {
        role: 'user',
        content: [
          {
            type: 'image_url',
            image_url: { url: dataUrl, detail: 'high' },
          },
          {
            type: 'text',
            text: this.buildSystemPrompt(languages),
          },
        ],
      },
    ];

    logger.debug('Calling OpenAI Vision API');

    let rawContent: string;
    try {
      const response = await axios.post<OpenAIResponse>(
        OPENAI_API_URL,
        {
          model: 'gpt-4o',
          messages,
          max_tokens: 4096,
          temperature: 0,
        },
        {
          headers: {
            Authorization: `Bearer ${config.openai.apiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: timeoutMs,
        }
      );

      rawContent = response.data.choices[0]?.message?.content ?? '';
    } catch (err) {
      if (axios.isAxiosError(err)) {
        if (err.code === 'ECONNABORTED') {
          throw new OcrServiceError(
            ERROR_CODES.OCR_TIMEOUT,
            `OpenAI OCR request timed out after ${timeoutMs}ms`,
            504
          );
        }
        const status = err.response?.status ?? 500;
        const msg =
          (err.response?.data as { error?: { message?: string } })?.error
            ?.message ?? err.message;
        throw new OcrServiceError(
          ERROR_CODES.PROVIDER_FAILURE,
          `OpenAI API error (${status}): ${msg}`,
          502
        );
      }
      throw new OcrServiceError(
        ERROR_CODES.PROVIDER_FAILURE,
        `Unexpected error calling OpenAI: ${String(err)}`,
        502
      );
    }

    return this.parseResponse(rawContent);
  }

  private parseResponse(raw: string): OcrResult {
    const cleaned = raw
      .replace(/```json\n?/g, '')
      .replace(/```\n?/g, '')
      .trim();

    let parsed: OpenAIOcrStructured;
    try {
      parsed = JSON.parse(cleaned) as OpenAIOcrStructured;
    } catch {
      throw new OcrServiceError(
        ERROR_CODES.PROVIDER_FAILURE,
        `OpenAI returned non-JSON response: ${cleaned.slice(0, 200)}`,
        502
      );
    }

    if (!Array.isArray(parsed.blocks)) {
      throw new OcrServiceError(
        ERROR_CODES.PROVIDER_FAILURE,
        'OpenAI response missing blocks array',
        502
      );
    }

    return {
      text: parsed.text ?? '',
      confidence: parsed.confidence ?? 0.9,
      pages: [
        {
          pageNumber: 1,
          text: parsed.text ?? '',
          confidence: parsed.confidence ?? 0.9,
          blocks: parsed.blocks.map((b) => ({
            text: b.text,
            boundingBox: {
              x: b.boundingBox.x,
              y: b.boundingBox.y,
              width: b.boundingBox.width,
              height: b.boundingBox.height,
            },
          })),
        },
      ],
    };
  }
}