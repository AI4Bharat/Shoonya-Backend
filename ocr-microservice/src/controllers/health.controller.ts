import { Request, Response } from 'express';
import { HealthResponse } from '../types';
import { config } from '../config';

export function healthCheck(_req: Request, res: Response): void {
  const response: HealthResponse = {
    status: 'healthy',
    service: 'ocr-microservice',
    version: config.version,
  };
  res.status(200).json(response);
}