from djaveS3.models.bucket import get_bucket_config, Bucket
from djaveS3.models.signed_file import SignedFile


def generate_presigned_post(
    bucket_config, file_name, file_type, boto_client=None):
  """ This gets its own file because it knows about Buckets and SignedFiles.
  bucket_config can be the name of a bucket or a bucket config. """
  bucket = Bucket(get_bucket_config(bucket_config))
  boto_client = boto_client or bucket.boto_client
  SignedFile.objects.get_or_create(
      file_name=file_name, bucket_name=bucket.name())
  fields = {'Content-Type': file_type}
  conditions = [{'Content-Type': file_type}]
  """
  OK, so the S3 API describes how you can assign acls on a per-upload basis,
  and I swear that this used to work, but now it doesn't seem to. It's not
  until you also add an S3 -> your bucket_name -> security -> bucket policy
  that it becomes possible to publically read stuff out of a bucket.

  fields['acl'] = 'public-read'
  conditions.insert(0, {'acl': 'public-read'})
  """
  return boto_client.generate_presigned_post(
      Bucket=bucket.name(),
      Key=file_name,
      Fields=fields,
      Conditions=conditions,
      ExpiresIn=3600)
