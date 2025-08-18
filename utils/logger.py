import logging
import colorlog

def setup_colored_logger(level=logging.INFO):
    """
    Thiết lập logger với màu sắc tùy chỉnh.
    Cho phép truyền vào mức log mặc định (INFO, DEBUG, ...).
    """
    logger = colorlog.getLogger()
    logger.setLevel(level)  # Giờ có thể chỉnh: logging.INFO, WARNING, etc.

    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s | %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    # 🔕 Tắt log DEBUG từ các thư viện bên thứ ba
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("haystack").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)

    return logger
