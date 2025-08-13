import logging
import sys
import colorlog

def get_logger(name: str) -> logging.Logger:
    """
    Hàm khởi tạo và cấu hình một logger với màu sắc.
    - INFO: Xanh lá
    - WARNING: Vàng
    - ERROR: Đỏ
    - CRITICAL: Đỏ đậm
    - DEBUG: Xanh dương
    """
    # Lấy logger theo tên
    logger = colorlog.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Định nghĩa màu sắc cho từng cấp độ log
        log_colors = {
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
        # Tạo handler để log ra console
        handler = colorlog.StreamHandler(sys.stdout)
        # Tạo formatter với màu sắc
        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s',
            log_colors=log_colors,
            reset=True,
            style='%'
        )
        # Gán formatter cho handler
        handler.setFormatter(formatter)
        # Thêm handler vào logger
        logger.addHandler(handler)
    return logger