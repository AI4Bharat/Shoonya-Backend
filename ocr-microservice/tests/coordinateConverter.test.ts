import { describe, it, expect } from '@jest/globals';
import { convertBlockToShoonya } from '../src/utils/coordinateConverter';
import { OcrBlock } from '../src/types';

describe('convertBlockToShoonya', () => {
  const imageWidth = 1200;
  const imageHeight = 1800;

  it('converts absolute pixel coordinates to percentages', () => {
    const block: OcrBlock = {
      text: 'Hello',
      boundingBox: { x: 120, y: 180, width: 360, height: 90 },
    };

    const result = convertBlockToShoonya(block, imageWidth, imageHeight);

    expect(result.x).toBeCloseTo(10);
    expect(result.y).toBeCloseTo(10);
    expect(result.width).toBeCloseTo(30);
    expect(result.height).toBeCloseTo(5);
  });

  it('sets correct Shoonya metadata fields', () => {
    const block: OcrBlock = {
      text: 'Test',
      boundingBox: { x: 0, y: 0, width: 100, height: 100 },
    };

    const result = convertBlockToShoonya(block, imageWidth, imageHeight);

    expect(result.text).toBe('Test');
    expect(result.labels).toEqual([]);
    expect(result.rotation).toBe(0);
    expect(result.original_width).toBe(imageWidth);
    expect(result.original_height).toBe(imageHeight);
  });

  it('handles negative coordinates using Math.abs', () => {
    const block: OcrBlock = {
      text: 'Negative',
      boundingBox: { x: -120, y: -180, width: -360, height: -90 },
    };

    const result = convertBlockToShoonya(block, imageWidth, imageHeight);

    expect(result.x).toBeCloseTo(10);
    expect(result.y).toBeCloseTo(10);
    expect(result.width).toBeCloseTo(30);
    expect(result.height).toBeCloseTo(5);
  });

  it('handles full image block (100%)', () => {
    const block: OcrBlock = {
      text: 'Full',
      boundingBox: { x: 0, y: 0, width: 1200, height: 1800 },
    };

    const result = convertBlockToShoonya(block, imageWidth, imageHeight);

    expect(result.x).toBe(0);
    expect(result.y).toBe(0);
    expect(result.width).toBe(100);
    expect(result.height).toBe(100);
  });

  it('throws on invalid image dimensions', () => {
    const block: OcrBlock = {
      text: 'Error',
      boundingBox: { x: 10, y: 10, width: 100, height: 100 },
    };

    expect(() => convertBlockToShoonya(block, 0, 1800)).toThrow(
      'Invalid image dimensions'
    );
    expect(() => convertBlockToShoonya(block, 1200, 0)).toThrow(
      'Invalid image dimensions'
    );
  });
});