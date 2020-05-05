from django.db import models
from djaveS3.models.bucket import Bucket, get_bucket_config


class SignedFile(models.Model):
  """ In order to upload a file, your server must first sign it. djaveS3 takes
  that opportunity to keep track of all the files that get signed and uploaded
  so it can circle back around later and delete anything that didn't end up in
  the Files table, which is the list of files that are actually getting used
  for anything. """
  # It's a little aggressive to put a unique constraint on file_name because
  # it's totally possible for different buckets to have files with the same
  # name. But this will solve some problems ahead of time, and djaveS3
  # purposefully renames every file to something random, so I think it's worth
  # it.
  file_name = models.CharField(
      max_length=200, db_index=True, unique=True, null=False, blank=False)
  bucket_name = models.CharField(max_length=200)
  created_at = models.DateTimeField(auto_now_add=True)

  def delete_file(self, bucket=None):
    bucket = bucket or Bucket(get_bucket_config(self.bucket_name))
    bucket.delete(self.file_name)

  def __repr__(self):
    return '<SignedFile {}: {}>'.format(self.pk, self.file_name)
