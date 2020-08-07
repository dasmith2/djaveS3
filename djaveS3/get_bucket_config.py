from djaveS3.bucket_config import BucketConfig
from django.conf import settings


class GetBucketConfigException(Exception):
  pass


def get_bucket_config(bucket_config):
  if isinstance(bucket_config, BucketConfig):
    return bucket_config
  elif settings.TEST:
    raise GetBucketConfigException(
        'In tests, you should pass bucket objects around instead of using '
        'get_bucket_config which accesses global settings. Tests hate '
        'global settings because you can not replace them with test values.')
  if not hasattr(settings, 'S3_BUCKETS'):
    message = ''.join([
        'You need to configure your S3_BUCKETS in django.conf.settings. For '
        'example,\nfrom djaveS3.bucket_config import BucketConfig\n'
        'S3_BUCKETS = [BucketConfig(\'my_bucket_name\', '
        'my_access_key_id, my_secret_access_key, is_public=True)]'])
    raise GetBucketConfigException(message)
  if isinstance(bucket_config, str):
    got_bucket = None
    for next_bucket in settings.S3_BUCKETS:
      if next_bucket.name == bucket_config:
        got_bucket = next_bucket
    if got_bucket is None:
      raise GetBucketConfigException((
          'S3 bucket {} is not configured in S3_BUCKETS in '
          'django.conf.settings').format(bucket_config))
    if not isinstance(got_bucket, BucketConfig):
      raise GetBucketConfigException((
          'S3 bucket {} in S3_BUCKETS in django.conf.settings should be a '
          'BucketConfig, but it is a {}').format(
              bucket_config, got_bucket.__class__))
    return got_bucket
  raise GetBucketConfigException(
      'I am expecting a BucketConfig or a string. You gave me a {}'.format(
          bucket_config.__class__))
