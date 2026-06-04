import { Request, Response, NextFunction } from 'express';
import { logRequest, logResponse } from '../logger';

export function requestLoggerMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const start = Date.now();

  logRequest(req.method, req.path, req.body);

  res.on('finish', () => {
    const durationMs = Date.now() - start;
    logResponse(req.method, req.path, res.statusCode, durationMs);
  });

  next();
}