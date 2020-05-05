import base64
import os
import re

from django.conf import settings
from djavError.models import log_error
from djaveS3.boto_client import get_boto_client
from djaveS3.bucket_config import BucketConfig


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
          'BucketConfig, but it is a {}').format(got_bucket.__class__))
    return got_bucket
  raise GetBucketConfigException(
      'I am expecting a BucketConfig or a string. You gave me a {}'.format(
          bucket_config.__class__))


def public_file_url(bucket_config, file_name):
  # bucket_config can be a bucket name or a BucketConfig
  bucket_config = get_bucket_config(bucket_config)
  if bucket_config.is_sensitive:
    raise Exception(
        'There is no public file url for files in sensitive buckets')
  return 'https://{}.s3.amazonaws.com/{}'.format(
      bucket_config.name, file_name)


""" Why isn't there a sensitive_file_url(bucket_config, file_name) function?
That's because sensitive files require security checks, and I don't know what
business rules your organization has, so I can't write a view for you that will
display a sensitive file, so I don't know what view to reverse, so I can't
calculate a sensitive_file_url for you. See sensitive_file_response in
djaveS3.views which explains how to write just such a view. """


class Bucket(object):
  def __init__(self, bucket_config, boto_client=None):
    # bucket_config can be a bucket name or a bucket_config object.
    # boto_client can be overridden for the sake of tests.
    self.bucket_config = get_bucket_config(bucket_config)
    if settings.TEST and not boto_client:
      raise Exception(
          'You should use a mock boto3 client in unit tests so your tests do '
          'not attempt to contact Amazon servers because that could slow your '
          'tests down and put test files on Amazon servers.')
    self.boto_client = boto_client or get_boto_client(
        self.bucket_config.access_key_id, self.bucket_config.secret_access_key)

  def name(self):
    return self.bucket_config.name

  def list(self):
    """ [('blahblahblah.jpg', datetime(2018, 6, 28, 21)),
         (file name, last modified)] """
    to_return = []
    # You don't have to can_read_net here. __init__ forces tests to pass in an
    # s3_override, and  dev and stage use the dev s3 buckets.
    lookup_result = self.boto_client.list_objects_v2(
        Bucket=self.bucket_config.name)
    # If the bucket_name is empty they omit the Contents entirely.
    if 'Contents' in lookup_result:
      for obj in lookup_result['Contents']:
        to_return.append((obj['Key'], obj['LastModified']))
    return to_return

  def download(self, file_name, local_file_name=None):
    local_file_name = local_file_name or file_name
    self.boto_client.download_file(
        self.bucket_config.name, file_name, local_file_name)

  def rm_download(self, local_file_name):
    os.remove(local_file_name)

  def file_bytes(self, file_name):
    """
    return HttpResponse(
        Bucket('StevesBucket').file_bytes(file_name),
        content_type='image/jpeg')
    """
    if re.compile(r'[\/\\]').search(file_name):
      raise Exception(
          'I\'m expecting simply a file_name I can download, '
          'not a path to a file that\'s already downloaded.')
    for tries in range(3):
      if not os.path.exists(file_name):  # More or less always.
        # This throws an exception if the file doesn't exist on Bucket.
        self.download(file_name)
      # So if we get here, we know the file exists on Bucket. So far so good.
      # But one time, this open call here triggered a FileNotFoundError. Now, I
      # could see that happening if somebody opens a pile of tabs that all try
      # to load this image at once, and then there's a race where
      # os.path.exists at first but then before open gets called, a different
      # thread runs os.remove. My answer is to take 3 tries to load an image.
      try:
        f = open(file_name, 'rb')
      except FileNotFoundError:
        continue
      read = f.read()
      f.close()
      self.rm_download(file_name)
      return read
    log_error('Never able to download and read an image', (
        'I tried 3 times to download and read {}').format(file_name))

  def utf8_encoded_image(self, file_name):
    return base64.b64encode(self.file_bytes(file_name)).decode('utf-8')

  def upload(self, file_name, remote_file_name=None):
    remote_file_name = remote_file_name or file_name
    self.boto_client.upload_file(
        file_name, self.bucket_config.name, remote_file_name)

  def delete(self, file_name):
    """ Regardless of whether file_name exists or not in the bucket, this will
    return a 204. """
    got = self.boto_client.delete_object(
        Bucket=self.bucket_config.name, Key=file_name)
    return got['ResponseMetadata']['HTTPStatusCode'] == 204
