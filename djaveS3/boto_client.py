""" boto3 does the heavy lifting of talking with S3. """
import boto3
import botocore
from django.conf import settings


s3_region_name = getattr(settings, 'S3_REGION_NAME', 'us-east-2')


# You need signature_version='s3v4' to avoid "The authorization mechanism you
# have provided is not supported. Please use AWS4-HMAC-SHA256
_s3_config = botocore.client.Config(
    signature_version='s3v4',
    region_name=s3_region_name)


def get_boto_client(access_key_id, secret_access_key):
  return boto3.client(
      's3',
      aws_access_key_id=access_key_id,
      aws_secret_access_key=secret_access_key,
      config=_s3_config)
