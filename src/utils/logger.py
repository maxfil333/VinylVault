import sys

from loguru import logger as loguru_logger

from src.config import cfg

LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"


def setup_logger():
    loguru_logger.remove()
    loguru_logger.add(sys.stderr, format=LOG_FORMAT, level=cfg.LOG_LEVEL)

    try:
        cfg.LOG_DIR.mkdir(parents=True, exist_ok=True)
        loguru_logger.add(
            cfg.LOG_DIR / "app.log",
            format=LOG_FORMAT,
            level=cfg.LOG_LEVEL,
            rotation=cfg.LOG_ROTATION,
            retention=cfg.LOG_RETENTION,
            compression="zip",
            enqueue=True,
        )
    except OSError as exc:
        loguru_logger.warning(f"Логи в файл отключены ({cfg.LOG_DIR}): {exc}")

    return loguru_logger


logger = setup_logger()
