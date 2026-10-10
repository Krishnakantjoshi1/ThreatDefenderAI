import logging
import sys

_configured = False


def get_logger(name: str = "threatdefender") -> logging.Logger:
    global _configured
    if not _configured:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            stream=sys.stdout,
        )
        _configured = True
    return logging.getLogger(name)
