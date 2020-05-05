from django.db import models

from djaveS3.models.photo import Photo
from djaveS3.bucket_config import BucketConfig


SENSITIVE_BUCKET_NAME = 'my_sensitive_bucket'
SENSITIVE_BUCKET_CONFIG = BucketConfig(
    SENSITIVE_BUCKET_NAME, 'test_sensitive_access_key_id',
    'test_sensitive_secret_access_key', is_public=False)
PUBLIC_BUCKET_NAME = 'my_public_bucket'
PUBLIC_BUCKET_CONFIG = BucketConfig(
    PUBLIC_BUCKET_NAME, 'test_public_access_key_id',
    'test_public_secret_access_key', is_public=True)


class TestPhoto(Photo):
  """ I need a child class to write tests against. """
  bucket_name = models.CharField(max_length=200)
  next_keep_until = models.DateTimeField(null=True)
  why_no_need_for_file = models.CharField(
      max_length=200, default='', blank=True)

  def explain_why_can_delete(self):
    return self.why_no_need_for_file

  def calc_and_set_keep(self, nnow=None):
    self.keep_until = self.next_keep_until

  def bucket_config(self):
    if self.bucket_name == SENSITIVE_BUCKET_NAME:
      return SENSITIVE_BUCKET_CONFIG
    elif self.bucket_name == PUBLIC_BUCKET_NAME:
      return PUBLIC_BUCKET_CONFIG
    raise Exception(self.bucket_name)
