""" BucketConfig has to stay separate from everything to avoid a circular
dependency. djaveS3 loads bucket configuration from settings, but settings uses
this BucketConfig definition. So any file that defines BucketConfig can't also
use settings.

You're probably looking for get_bucket_config in djaveS3.models.bucket

bucket_name is the name of the S3 bucket obviously. access_key_id
secret_access_key are from the Amazon IAm user. is_public is a boolean which
says whether or not random people on the internet can see the image. So lets
say you have a single IAm user with two buckets, one of which is publically
visible. Your django.conf.settings should have something like this in it:

IAM_ACCESS_KEY_ID = 'whatever'
IAM_SECRET_ACCESS_KEY = 'whatever else'
BUCKETS = [
    BucketConfig(
        'my_public_bucket', IAM_ACCESS_KEY_ID,
        IAM_SECRET_ACCESS_KEY, is_public=True),
    BucketConfig(
        'my_private_bucket', IAM_ACCESS_KEY_ID,
        IAM_SECRET_ACCESS_KEY, is_public=False)]

This configuration is basically so we know how to view an image given a bucket
name and a file name.
"""
from collections import namedtuple


BucketConfig = namedtuple(
    'BucketConfig', 'name access_key_id secret_access_key is_public')
