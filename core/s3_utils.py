import logging
import boto3
from django.conf import settings

logger = logging.getLogger(__name__)

def get_s3_client():
    kwargs = {}
    if getattr(settings, 'AWS_ACCESS_KEY_ID', None):
        kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
    if getattr(settings, 'AWS_SECRET_ACCESS_KEY', None):
        kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
    if getattr(settings, 'AWS_S3_REGION_NAME', None):
        kwargs['region_name'] = settings.AWS_S3_REGION_NAME
    endpoint_url = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
    if endpoint_url:
        kwargs['endpoint_url'] = endpoint_url
    return boto3.client('s3', **kwargs)





def upload_to_s3(file_obj, object_name):
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    if not bucket_name:
        logger.warning("AWS_STORAGE_BUCKET_NAME is not configured. Upload to S3 skipped.")
        return None
    try:
        s3 = get_s3_client()
        s3.upload_fileobj(
            file_obj,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': getattr(file_obj, 'content_type', 'image/jpeg')}
        )
        return object_name
    except Exception as e:
        logger.exception("S3 upload failed: %s", str(e))
        return None
