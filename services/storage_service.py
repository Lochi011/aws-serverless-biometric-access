import boto3
import uuid
import os
_s3 = boto3.client("s3")
_BUCKET = os.environ["S3_BUCKET"]


def upload_jpeg(image_bytes: bytes) -> str:
    key = f"access_users/{uuid.uuid4()}.jpg"
    _s3.put_object(Bucket=_BUCKET, Key=key, Body=image_bytes,
                   ContentType="image/jpeg")
    return f"https://{_BUCKET}.s3.amazonaws.com/{key}"
