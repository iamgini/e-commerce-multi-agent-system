import logging
import logging.handlers
import queue
import os
import glob
import gzip
import shutil
import re
import boto3
from pathlib import Path
from datetime import datetime


# ── Custom Logger ──────────────────────────────────────────────────────────────

class S3RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Handler for compressing and uploading of log files 
    to S3 upon rotation of local logfiles
    """
    def __init__(self, client_params, filename, chunk_size, backupCount, s3_bucket, s3_prefix):
        super().__init__(filename, maxBytes=chunk_size, backupCount=backupCount, encoding='utf-8')
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix.lstrip("./")
        self.s3_client = boto3.client('s3', **client_params)

    def doRollover(self):
        # Perform standard local rotation first
        super().doRollover()
        
        # Identify all rotated segments in the directory and filter
        # for files that end with .number suffix
        # Active log file is excluded
        pattern = f"{self.baseFilename}.*"
        all_rotated = glob.glob(pattern)
        regex = re.compile(r'\.(\d+)$')
        segments = [f for f in all_rotated if regex.search(f)]

        # Sort by numeric suffix in DESCENDING order 
        segments.sort(key=lambda x: int(regex.search(x).group(1)), reverse=True)


        for log_file in segments:
            if os.path.exists(log_file):
                self._upload_to_s3(log_file)

    def _upload_to_s3(self, file_path):
        # Rename logs to format: backend_20260403_10_25_30.log 
        # Compress logs into log.gz before uploading into S3
        timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
        base_name = os.path.basename(file_path).rsplit('.', 2)[0]
        dir_path = os.path.dirname(file_path)
        
        gz_path = f"{dir_path}/{base_name}_{timestamp}.log.gz"
        s3_key = f"{self.s3_prefix}/{base_name}_{timestamp}.log.gz"
        
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            self.s3_client.upload_file(gz_path, self.s3_bucket, s3_key, ExtraArgs={'ContentEncoding': 'gzip'})
            os.remove(file_path)
            os.remove(gz_path)
            
        except Exception as e:
            print(f"CRITICAL: S3 Pipe Failed for {file_path}: {e}")


class AsyncS3PipeHandler(logging.handlers.QueueHandler):
    """
    Asynchronous handler that saves logs to local log directory.
    Files are stored in the ./log folder by default.
    Logs are rotated every time it reaches 2MB.
    """
    def __init__(self,
                 bucket_name: str="test-bucket",
                 log_dir: str="./logs",
                 filename="app.log",
                 chunk_size=2*1024*1024,
                 client_params=None
                 ):
        
        # Create log folder if does not exists
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        full_path = log_path / filename
        
        self.log_queue = queue.Queue(-1)
        super().__init__(self.log_queue)

        # Pass the s3 client configurations to the Rotating Handler
        s3_handler = S3RotatingFileHandler(
            filename=str(full_path),
            chunk_size=chunk_size,
            backupCount=2,
            s3_bucket=bucket_name,
            client_params=client_params,
            s3_prefix=log_dir,
        )
        
        s3_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        ))

        # Use listener to bridge the queue to the file
        self.listener = logging.handlers.QueueListener(
            self.log_queue,
            s3_handler, 
            # respect_handler_level=True
        )
        self.listener.start()

    def close(self):
        self.listener.stop()
        super().close()
