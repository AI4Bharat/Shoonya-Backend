import express, { Application, Request, Response } from 'express';
import { requestLoggerMiddleware } from './middleware/requestLogger.middleware';
import { errorHandlerMiddleware } from './middleware/errorHandler.middleware';
import healthRouter from './routes/health.routes';
import ocrRouter from './routes/ocr.routes';

const app: Application = express();

// ─── Core Middleware ──────────────────────────────────────────────────────────
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(requestLoggerMiddleware);

// ─── Routes ───────────────────────────────────────────────────────────────────
app.use('/health', healthRouter);
app.use('/ocr', ocrRouter);

// ─── 404 Handler ─────────────────────────────────────────────────────────────
app.use((_req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: {
      code: 'NOT_FOUND',
      message: 'The requested endpoint does not exist',
    },
  });
});

// ─── Global Error Handler ─────────────────────────────────────────────────────
app.use(errorHandlerMiddleware);

export default app;