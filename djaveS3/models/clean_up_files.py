from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from djaveDT import now
from djaveS3.models.bucket import public_file_url, Bucket
from djaveS3.models.file import File
from djaveS3.models.signed_file import SignedFile
from djaveThread.background_command import background_command


@background_command
def clean_up_never_used(nnow=None, bucket=None):
  """ I find out about every file that users upload because the server has to
  sign them. But WHY they're being used doesn't become clear until somebody
  creates a File object, and then the child class explains everything. So
  whatever SignedFiles exist without File objects are files that got uploaded,
  but we never found out why. So just delete them. This is quite common. People
  might change their minds and upload a different file, or they may just never
  submit the form that says why they uploaded that file.

  Once we know whether or not a file is used, we no longer need the
  SignedFile. """
  nnow = nnow or now()
  # It may take a moment for the background thread to catch up and use a file,
  # or it may take the user a while to submit the form that says how to use the
  # file they just uploaded. So give it a day for the reason for the upload to
  # show up, and if it doesn't, chuck the upload.
  for signed in SignedFile.objects.filter(
      created_at__lte=nnow - timedelta(days=1)).order_by('pk'):
    if not signed_file_is_used(signed):
      signed.delete_file(bucket=bucket)
    signed.delete()


def signed_file_is_used(signed_file):
  for name_match in File.objects.filter(
      file_name=signed_file.file_name):
    # we gotta make sure it's also a bucket match because different buckets can
    # have files with the same name.
    next_bucket_name = name_match.as_child_class().bucket_config().name
    if next_bucket_name == signed_file.bucket_name:
      return True
  return False


@background_command
def clean_up_no_longer_needed(nnow=None, bucket=None):
  """ Files have to describe when they can be thrown out. bucket is just used
  in tests to inject dependencies, but in case anybody actually tries to just
  clean_up_no_longer_needed in a specific bucket, I only deal with files in
  bucket if provided. """
  nnow = nnow or now()
  # Sometimes a single empty file name slips into the database. There's a
  # unique constraint, so only 1 empty file_name is allowed haha Anyway
  # obviously you can't delete a file with no name.
  for file in File.objects.filter(
      ~Q(file_name=''), keep_until__lt=nnow):
    file = file.as_child_class()
    if bucket and bucket.name() != file.bucket_config().name:
      continue
    if file.explain_why_can_delete():
      file.delete(bucket=bucket)
    else:
      file.calc_and_set_keep(nnow=nnow)
      if file.keep_until >= nnow:
        file.save()
      else:
        raise Exception(
            'Theres no reason to keep {} but calc_and_set_keep set '
            'keep_until to {} which is in the past'.format(
                file, file.keep_until))


def list_unaccounted_images(
    bucket, also_delete=False, also_print_urls=False):
  """ Actually list the contents of the directory and compare it with the File
  and SignedFile classes. If you specify also_delete, you'll remove anything
  that we don't recognize from S3. Wow is this function dangerous. Especially
  in production, list the files first and double check a few to make sure you
  actually want to delete them. """
  if not isinstance(bucket, Bucket):
    raise Exception(
        'bucket should be a Bucket object, not a {}'.format(bucket.__class__))
  actual_files = set()
  for file_name, modified_at in bucket.list():
    actual_files.add(file_name)
  known_files = set()
  for file in File.objects.all():
    known_files.add(file.file_name)
  for signed_file in SignedFile.objects.all():
    known_files.add(signed_file.file_name)
  unaccounted = actual_files - known_files
  if also_print_urls:
    for file_name in unaccounted:
      print(public_file_url(bucket, file_name))
  if also_delete:
    if not hasattr(settings, 'DEV_BUCKET_NAMES'):
      raise Exception(
          'Before I delete any files from S3, I want you to list the dev '
          'bucket names in settings.DEV_BUCKET_NAMES so I can make sure '
          'you do not make the horrific mistake of asking a non-prod '
          'environment to clean up a production bucket, which would delete '
          'all files from the production bucket.')
    dev_bucket_names = settings.DEV_BUCKET_NAMES

    # settings.PROD should describe whether or not we're in a production
    # environment. So you need something like this in your settings.py

    # PROD = os.environ.get('PROD', default='False') == 'True'

    if bucket not in dev_bucket_names and not settings.PROD:
      raise Exception(
          'It seems like youre trying to clean up images in a production S3 '
          'bucket that are unaccounted for in a non production database. But '
          'a non production database has no idea what images are in '
          'production. So this would completely empty an entire S3 bucket of '
          'production images, which is a terrible mistake.')
    for file_name in unaccounted:
      bucket.delete(file_name)
  return unaccounted
