import logging
import colorlog


def setup_colored_logger():
    """
    Thiết lập logger với màu sắc tùy chỉnh.
    """
    # Lấy logger chính (root logger)
    logger = colorlog.getLogger()
    logger.setLevel(logging.DEBUG)  # Đặt mức log thấp nhất để bắt tất cả các level

    # Định dạng của log message
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

    # Tạo handler để xuất log ra console
    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)

    # Xóa các handler cũ và thêm handler mới để tránh log trùng lặp
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    return logger


# --- Sử dụng logger ---
if __name__ == "__main__":
    # Thiết lập logger một lần duy nhất khi chương trình bắt đầu
    logger = setup_colored_logger()

    logger.debug("Đây là một thông điệp debug.")
    logger.info("Hệ thống đã khởi động thành công.")
    logger.warning("Cảnh báo: Bộ nhớ sắp đầy.")
    logger.error("Đã xảy ra lỗi khi kết nối tới cơ sở dữ liệu.")
    logger.critical("Lỗi nghiêm trọng: Hệ thống không thể tiếp tục hoạt động.")