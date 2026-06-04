import app from './app';
import { config } from './config';
import { logger } from './logger';

const server = app.listen(config.port, () => {
  logger.info('OCR Microservice started', {
    port: config.port,
    environment: config.nodeEnv,
    version: config.version,
    defaultProvider: config.defaultProvider,
  });
});

// ─── Graceful Shutdown ────────────────────────────────────────────────────────

function shutdown(signal: string): void {
  logger.info(`${signal} received. Shutting down gracefully...`);
  server.close(() => {
    logger.info('Server closed. Exiting process.');
    process.exit(0);
  });

  // Force exit if server hasn't closed in 10 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10_000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

process.on('uncaughtException', (err) => {
  logger.error('Uncaught exception', {
    error: err.message,
    stack: err.stack,
  });
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled rejection', { reason });
  process.exit(1);
});

export default server;