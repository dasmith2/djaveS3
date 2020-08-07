from djaveS3.get_bucket_config import get_bucket_config


def public_file_url(bucket_config, file_name):
  return public_file_url_root(bucket_config) + file_name


def public_file_url_root(bucket_config):
  # bucket_config can be a bucket name or a BucketConfig
  bucket_config = get_bucket_config(bucket_config)
  if not bucket_config.is_public:
    raise Exception(
        'There is no public file url for files in sensitive buckets')
  return 'https://{}.s3.amazonaws.com/'.format(bucket_config.name)
