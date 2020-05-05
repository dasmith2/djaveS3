""" Heroku machines don't stick around for long. So file uploads have to go to
some kind of cloud storage.

Let's say the user wants to upload a file. We serve the user a page. That page
contains Javascript which first does a round trip to our servers to sign the
metadata of the file they intend to upload. Note that our servers still haven't
seen the actual bytes of the upload yet. Then the Javascript on the page sends
the user's file, along with the signed information, directly to S3. So our
server's STILL haven't seen the bytes of the file, which is great. But since we
had to sign every upload, we know all the photos that got uploaded by users. I
mean, you can also call an api on the bucket to list the contents, but that
will start to break down if the bucket grows with time.  I believe that API
call taps out after a thousand files.

OK, so the user uploaded a photo to S3. The Javascript on the page we served up
will put the file name in a form somewhere. Eventually the user clicks some
kind of submit button, and when we get that POST, we finally know WHY the user
uploaded that photo, and we create objects that reference the uploaded file.

I have 1 central Files table so that it's relatively straightforward to ask the
question, "Is anybody actually using this file?" Whatever new feature you need
files for, you should make a new model that inherits from this File object,
which you'll notice, is NOT abstract. In fact you're almost certainly uploading
photos, so you probably want to inherit from Photo in djaveS3.models.photo
which has resize tools.

Files have to describe when they can be thrown out. This keeps cost and
clutter down. I also keep cost and clutter down by resizing all photos. """
from abc import abstractmethod

from django.core.exceptions import ValidationError
from django.db import models
from djaveClass import BaseKnowsChild


class File(BaseKnowsChild):
  # It's a little aggressive to put a unique constraint on file_name because
  # it's totally possible for different buckets to have files with the same
  # name. But this will solve some problems ahead of time, and djaveS3
  # purposefully renames every file to something random, so I think it's worth
  # it.
  file_name = models.CharField(
      max_length=200, db_index=True, unique=True, null=False, blank=False)
  created_at = models.DateTimeField(auto_now_add=True, db_index=True)
  keep_until = models.DateTimeField(db_index=True, null=True, help_text=(
      'Once keep_until is in the past, if I can '
      'explain_why_can_delete, I will chuck this file.'))

  def save(self, *args, **kwargs):
    if not self.file_name:
      raise Exception('File name is required!')
    super().save(*args, **kwargs)

  @abstractmethod
  def explain_why_can_delete(self, nnow=None):
    """ Explain why it's ok to throw this file out. If you want to keep this
    file, return nothing. """
    raise NotImplementedError('explain_why_can_delete')

  @abstractmethod
  def calc_and_set_keep(self, nnow=None):
    """ When should we definitely keep this file until? Put that value in
    keep_until, but don't save. """
    raise NotImplementedError('calc_and_set_keep')

  @abstractmethod
  def bucket_config(self):
    """ This determines which Amazon S3 bucket the file gets stored in, which
    in turn determines whether or not this is a sensitive file. """
    raise NotImplementedError('bucket')

  def delete(self, bucket=None):
    child_instance = self.as_child_class()
    if not child_instance.explain_why_can_delete():
      raise Exception((
          'Why are you deleting a file with no explanation for why '
          'we can delete it?'), child_instance)
    bucket = bucket or self._bucket()
    bucket.delete(self.file_name)
    return super().delete()

  def clean(self):
    if not self.file_name:
      raise ValidationError('file_name must be a non empty string')
    return super().clean()

  def _bucket(self):
    return self.as_child_class().bucket()

  def __repr__(self):
    return '<{} {}: {}>'.format(
        self._meta.model_name, self.pk, self.file_name)

  class Meta:
    abstract = False  # This makes cleaning up files fairly simple.
