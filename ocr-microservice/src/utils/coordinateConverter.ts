import { OcrBlock, ShoonyaPrediction } from '../types';

/**
 * Converts absolute pixel coordinates from OCR output to percentage-based
 * coordinates required by the Shoonya annotation format.
 *
 * @param block       - OCR block with absolute pixel boundingBox
 * @param imageWidth  - Full width of the source image in pixels
 * @param imageHeight - Full height of the source image in pixels
 * @returns ShoonyaPrediction with percentage-based coordinates
 */
export function convertBlockToShoonya(
  block: OcrBlock,
  imageWidth: number,
  imageHeight: number
): ShoonyaPrediction {
  if (imageWidth <= 0 || imageHeight <= 0) {
    throw new Error(
      `Invalid image dimensions: width=${imageWidth}, height=${imageHeight}`
    );
  }

  const { x, y, width, height } = block.boundingBox;

  return {
    x: toPercentage(Math.abs(x), imageWidth),
    y: toPercentage(Math.abs(y), imageHeight),
    width: toPercentage(Math.abs(width), imageWidth),
    height: toPercentage(Math.abs(height), imageHeight),
    text: block.text,
    labels: [],
    rotation: 0,
    original_width: imageWidth,
    original_height: imageHeight,
  };
}

function toPercentage(absoluteValue: number, dimension: number): number {
  return (absoluteValue / dimension) * 100;
}