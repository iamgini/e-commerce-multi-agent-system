import logging

logging.basicConfig(
    filename="system_logs.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_event(message: str):
    logging.info(message)