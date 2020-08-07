from datetime import timedelta
import os

from django.conf import settings
from django.db import models
from django.db.models import Q
from djaveDT import now
from djaveS3.models.file import File
from djaveThread.background_command import background_command
from djaveThread.background import background
from PIL import Image


@background_command
def resize_all(nnow=None, **kwargs):
  """ If all we ever get is a SignedFile, then the image will never be
  resized. """
  nnow = nnow or now()
  photos = Photo.objects.filter(
      ~Q(file_name=''),  # Sometimes a single empty file name is in the db
      resized_at__isnull=True,
      created__gte=nnow - timedelta(days=7))
  for photo in photos:
    photo.as_child_class().resize(**kwargs)


@background
def _do_resize_background(photo_id, **kwargs):
  # kwargs so I can pass Mocked objects all the way to the resize function.
  # settings.TEST should describe whether or not we're in a test environment.
  # Put something like this in your settintgs.py TEST = 'test' in sys.argv
  if settings.TEST and 'bucket' not in kwargs:
    return
  File.objects.get(pk=photo_id).as_child_class().resize(**kwargs)


class Photo(File):
  resized_at = models.DateTimeField(null=True)

  def notify_bad_image(self, **kwargs):
    """ You can use this to start a conversation with whoever uploaded a bad
    image, or you can just leave the default behavior of not really doing
    anything. """
    pass

  def do_additional_resize_steps(
      self, input_file_name, output_file_name, **kwargs):
    """ You can override this function if you want to have additional steps as
    part of resizing. Maybe you wanna blank out credit card numbers or
    something.  """
    pass

  def post_resize(self):
    pass

  def save(self, **kwargs):
    """ kwargs so I can pass in a mock bucket in tests """
    super().save()
    if not self.resized_at:
      _do_resize_background(self.pk, **kwargs)

  def resize(
      self, verbose=False, image_opener=None, use_os=None, use_open=None,
      **kwargs):
    """ This is a whole thing, and should run only in the background. It tries
    to run right away, but it also runs every night at midnight to help catch
    problems, so there are races possible, such as both threads trying to
    delete the working images. """
    if self.resized_at:
      return True

    image_opener = image_opener or Image.open
    use_os = use_os or os
    use_open = use_open or open
    bucket = kwargs.get('bucket', None) or self._bucket()

    if self.__class__ in (File, Photo):
      raise Exception('Call resize on the child class')
    if self.resized_at:
      return
    if not self.file_name:
      raise Exception('This photo was deleted and can\'t be recovered.')
    bucket.download(self.file_name)

    try:
      image = image_opener(self.file_name)
    except OSError as ex:
      if ex.args[0].find('cannot identify image file') == 0:
        self.notify_bad_image(**kwargs)
        return False
      raise ex

    # Sometimes people will upload pngs. Sometimes they'll upload pngs but
    # replace the file extension with jpg. Whatever, people are dumb at image
    # file formats. In any case just make sure it doesn't have an alpha channel
    # so we can save it as a jpg, which is pretty much the sane format for a
    # photograph.
    try:
      image = image.convert('RGB')
    except OSError as ex:
      if ex.args[0].find('image file is truncated') == 0:
        self.notify_bad_image(**kwargs)
        return False
      raise ex

    (width, height) = (image.width, image.height)
    max_dimension = max((width, height))
    if max_dimension > self.max_width_or_height():
      ratio = self.max_width_or_height() / max_dimension
      image = image.resize((int(ratio * width), int(ratio * height)))

    if use_os.path.exists(self.file_name):
      use_os.remove(self.file_name)

    # I don't use the handy `with ... as` because I didn't bother to figure out
    # how to mock that whole thing in tests.
    file_handle = use_open(self.file_name, 'wb')
    image.save(file_handle, format='JPEG', quality=100)
    file_handle.close()

    self.do_additional_resize_steps(self.file_name, self.file_name, **kwargs)

    bucket.upload(self.file_name)
    use_os.remove(self.file_name)

    self.resized_at = kwargs.get('nnow', now())
    self.save()

    self.post_resize()
    return True

  def max_width_or_height(self):
    return 800.0

  class Meta:
    abstract = False  # This makes resizing all photos fairly simple.
