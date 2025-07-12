from loguru import logger as loguru_logger


def setup_logger(log_file: str = "logs/app.log", level: str = "DEBUG"):
    loguru_logger.add(log_file,
                      format='{time} {level} {message}',
                      level=level,
                      rotation='5 MB',  # "1 week" | "10.00"
                      compression='zip')

    return loguru_logger


logger = setup_logger()
