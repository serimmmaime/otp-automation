from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def build_logger(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("kakao_otp_autofill")
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    app_root = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parents[1]
    )
    log_dir = app_root / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
