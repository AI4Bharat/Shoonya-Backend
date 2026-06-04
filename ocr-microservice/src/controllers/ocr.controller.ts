import { Request, Response, NextFunction } from 'express';
import { processOcr } from '../services/ocr.service';
import { OcrProcessRequest } from '../types';

export async function processOcrController(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const request: OcrProcessRequest = {
      imageUrl: req.body.imageUrl,
      provider: req.body.provider,
      languages: req.body.languages,
    };

    const result = await processOcr(request);

    res.status(200).json(result);
  } catch (err) {
    next(err);
  }
}