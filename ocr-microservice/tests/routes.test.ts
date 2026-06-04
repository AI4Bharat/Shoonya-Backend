import request from 'supertest';
import app from '../src/app';
import * as ocrService from '../src/services/ocr.service';

jest.mock('../src/services/ocr.service');

const mockProcessOcr = ocrService.processOcr as jest.Mock;

describe('GET /health', () => {
  it('returns healthy status', async () => {
    const res = await request(app).get('/health');

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('healthy');
    expect(res.body.service).toBe('ocr-microservice');
    expect(res.body.version).toBeDefined();
  });
});

describe('POST /ocr/process', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns 200 with valid request', async () => {
    mockProcessOcr.mockResolvedValue({
      success: true,
      provider: 'openai',
      processingTimeMs: 500,
      confidence: 0.95,
      prediction: [
        {
          x: 10,
          y: 10,
          width: 30,
          height: 5,
          text: 'Hello',
          labels: [],
          rotation: 0,
          original_width: 1200,
          original_height: 1800,
        },
      ],
    });

    const res = await request(app)
      .post('/ocr/process')
      .send({
        imageUrl: 'https://example.com/image.jpg',
        provider: 'openai',
        languages: ['hi'],
      });

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.prediction).toHaveLength(1);
  });

  it('returns 400 when imageUrl is missing', async () => {
    const res = await request(app)
      .post('/ocr/process')
      .send({ provider: 'openai' });

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
  });

  it('returns 400 when imageUrl is not a valid URL', async () => {
    const res = await request(app)
      .post('/ocr/process')
      .send({ imageUrl: 'not-a-url' });

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
  });

  it('returns 400 when provider is invalid', async () => {
    const res = await request(app)
      .post('/ocr/process')
      .send({
        imageUrl: 'https://example.com/image.jpg',
        provider: 'invalid-provider',
      });

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.error.code).toBe('VALIDATION_ERROR');
  });

  it('returns 404 for unknown routes', async () => {
    const res = await request(app).get('/unknown-route');

    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe('NOT_FOUND');
  });
});