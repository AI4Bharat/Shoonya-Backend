/// <reference types="jest" />
import { processOcr } from '../src/services/ocr.service';
import * as registry from '../src/providers/registry';
import * as imageDownloader from '../src/utils/imageDownloader';
import { OcrResult } from '../src/types';

jest.mock('../src/providers/registry');
jest.mock('../src/utils/imageDownloader');

const mockGetProvider = registry.getProvider as jest.Mock;
const mockDownloadImage = imageDownloader.downloadImage as jest.Mock;
const mockGetImageDimensions = imageDownloader.getImageDimensions as jest.Mock;

const mockOcrResult: OcrResult = {
  text: 'Hello World',
  confidence: 0.95,
  pages: [
    {
      pageNumber: 1,
      text: 'Hello World',
      confidence: 0.95,
      blocks: [
        {
          text: 'Hello',
          boundingBox: { x: 120, y: 180, width: 360, height: 90 },
        },
        {
          text: 'World',
          boundingBox: { x: 120, y: 300, width: 300, height: 90 },
        },
      ],
    },
  ],
};

describe('processOcr', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockDownloadImage.mockResolvedValue(Buffer.from('fake-image'));
    mockGetImageDimensions.mockResolvedValue({ width: 1200, height: 1800 });
    mockGetProvider.mockReturnValue({
      name: 'openai',
      process: jest.fn().mockResolvedValue(mockOcrResult),
    });
  });

  it('returns a valid Shoonya-formatted response', async () => {
    const result = await processOcr({
      imageUrl: 'https://example.com/image.jpg',
      provider: 'openai',
      languages: ['hi'],
    });

    expect(result.success).toBe(true);
    expect(result.provider).toBe('openai');
    expect(result.confidence).toBe(0.95);
    expect(result.prediction).toHaveLength(2);
    expect(result.processingTimeMs).toBeGreaterThanOrEqual(0);
  });

  it('converts coordinates to percentages correctly', async () => {
    const result = await processOcr({
      imageUrl: 'https://example.com/image.jpg',
      provider: 'openai',
      languages: ['hi'],
    });

    const first = result.prediction[0];
    expect(first.x).toBeCloseTo(10);
    expect(first.y).toBeCloseTo(10);
    expect(first.width).toBeCloseTo(30);
    expect(first.height).toBeCloseTo(5);
    expect(first.original_width).toBe(1200);
    expect(first.original_height).toBe(1800);
  });

  it('uses default provider when none specified', async () => {
    await processOcr({
      imageUrl: 'https://example.com/image.jpg',
    });

    expect(mockGetProvider).toHaveBeenCalled();
  });

  it('throws EMPTY_OCR_RESULT when no blocks returned', async () => {
    mockGetProvider.mockReturnValue({
      name: 'openai',
      process: jest.fn().mockResolvedValue({
        text: '',
        confidence: 0,
        pages: [],
      }),
    });

    await expect(
      processOcr({
        imageUrl: 'https://example.com/image.jpg',
        provider: 'openai',
      })
    ).rejects.toMatchObject({
      code: 'EMPTY_OCR_RESULT',
    });
  });

  it('propagates provider errors', async () => {
    mockGetProvider.mockReturnValue({
      name: 'openai',
      process: jest.fn().mockRejectedValue(new Error('Provider failed')),
    });

    await expect(
      processOcr({
        imageUrl: 'https://example.com/image.jpg',
        provider: 'openai',
      })
    ).rejects.toThrow('Provider failed');
  });
});