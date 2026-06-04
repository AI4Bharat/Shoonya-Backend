import { Router } from 'express';
import { processOcrController } from '../controllers/ocr.controller';
import { validateBody } from '../middleware/validate.middleware';
import { OcrProcessRequestSchema } from '../validators/ocr.validator';

const router = Router();

router.post(
  '/process',
  validateBody(OcrProcessRequestSchema),
  processOcrController
);

export default router;