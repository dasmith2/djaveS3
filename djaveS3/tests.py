from unittest.mock import Mock, call

from django.test import TestCase
from djaveS3.models.clean_up_files import (
    clean_up_never_used, clean_up_no_longer_needed,
    signed_file_is_used)
from djaveS3.models.file import File
from djaveS3.models.photo import resize_all, Photo
from djaveS3.models.signed_file import SignedFile
from djaveS3.models.test_photo import (
    TestPhoto, PUBLIC_BUCKET_NAME, SENSITIVE_BUCKET_NAME,
    SENSITIVE_BUCKET_CONFIG)
from djaveS3.random_string import random_string
from djaveS3.models.bucket import Bucket
from djaveDT import str_to_tz_dt


def get_test_photo(**kwargs):
  test_photo = TestPhoto(
      bucket_name=kwargs.get('bucket_name', PUBLIC_BUCKET_NAME),
      next_keep_until=kwargs.get('next_keep_until', None),
      why_no_need_for_file=kwargs.get('why_no_need_for_file', ''))
  return set_photo_stuff(test_photo, **kwargs)


def set_photo_stuff(photo, **kwargs):
  photo.resized_at = kwargs.get('resized_at', None)
  return set_file_stuff(photo, **kwargs)


def set_file_stuff(file, **kwargs):
  file.file_name = kwargs.get('file_name', random_string())
  file.keep_until = kwargs.get('keep_until', None)
  if 'created' in kwargs:
    File.objects.filter(pk=file.pk).update(created=kwargs['created'])
    file.refresh_from_db()
  file.save()
  return file


def get_test_signed_file(**kwargs):
  signed_file = SignedFile.objects.create(
      file_name=kwargs.get('file_name', None),
      bucket_name=kwargs.get('bucket_name', False))
  if 'created' in kwargs:
    SignedFile.objects.filter(pk=signed_file.pk).update(
        created=kwargs['created'])
    signed_file.refresh_from_db()
  return signed_file


class SignedFileIsUsedTests(TestCase):
  def setUp(self):
    super().setUp()
    get_test_photo(
        bucket_name=PUBLIC_BUCKET_NAME, file_name='earballs.jpg')

  def test_signed_file_is_used(self):
    earballs = get_test_signed_file(
        file_name='earballs.jpg', bucket_name=PUBLIC_BUCKET_NAME)
    self.assertTrue(signed_file_is_used(earballs))

  def test_signed_file_is_not_used(self):
    earballs = get_test_signed_file(
        file_name='earballs.jpg', bucket_name=SENSITIVE_BUCKET_NAME)
    self.assertFalse(signed_file_is_used(earballs))


class CleanUpNeverUsedTests(TestCase):
  def test_clean_up_never_used(self):
    # Used
    get_test_signed_file(
        file_name='verbs.jpg', bucket_name=PUBLIC_BUCKET_NAME,
        created=str_to_tz_dt('2018-12-24 12:00'))
    get_test_photo(file_name='verbs.jpg')
    # Created too recently
    recent = get_test_signed_file(
        file_name='participles.jpg', bucket_name=PUBLIC_BUCKET_NAME,
        created=str_to_tz_dt('2018-12-24 12:01'))
    # Coincidentally, there's a sensitive file with the same name. But that
    # means it's in a totally different bucket, so this should get cleaned up.
    get_test_signed_file(
        file_name='nouns.jpg', bucket_name=SENSITIVE_BUCKET_NAME,
        created=str_to_tz_dt('2018-12-24 12:00'))
    get_test_photo(file_name='nouns.jpg')
    # Standard abandoned upload. Clean it up.
    get_test_signed_file(
        file_name='adjectives.jpg', bucket_name=SENSITIVE_BUCKET_CONFIG,
        created=str_to_tz_dt('2018-12-24 12:00'))

    bucket = Mock(spec=Bucket)
    clean_up_never_used(nnow=str_to_tz_dt('2018-12-25 12:00'), bucket=bucket)
    self.assertEqual(
        [call('nouns.jpg'), call('adjectives.jpg')],
        bucket.delete.call_args_list)
    self.assertEqual(set([recent]), set(list(SignedFile.objects.all())))


class CleanUpNoLongerNeededTests(TestCase):
  def test_had_earlier_remove_date_moved_to_later(self):
    file = get_test_photo(
        file_name='ldnsldkf',
        keep_until=str_to_tz_dt('2018-12-25 12:00'),
        next_keep_until=str_to_tz_dt('2019-01-01 12:00'))
    clean_up_no_longer_needed(nnow=str_to_tz_dt('2018-12-26'))
    file.refresh_from_db()
    self.assertEqual(str_to_tz_dt('2019-01-01 12:00'), file.keep_until)

  def test_clean_up_no_longer_needed(self):
    # Don't bother checking. keep_until is in the future.
    get_test_photo(
        file_name='industrial', keep_until=str_to_tz_dt('2019-01-01'))
    # keep_until in the past, but there's no reason it's ok to delete and the
    # new keep_until is in the future.
    get_test_photo(
        file_name='autonomous',
        keep_until=str_to_tz_dt('2018-12-24'),
        next_keep_until=str_to_tz_dt('2019-01-01'))
    # Actually delete this one.
    deleted = get_test_photo(
        file_name='mowers',
        keep_until=str_to_tz_dt('2018-12-24'),
        why_no_need_for_file='You actually could delete this')
    self.assertEqual(3, TestPhoto.objects.count())
    bucket = Mock(spec=Bucket)
    bucket.name.return_value = PUBLIC_BUCKET_NAME
    clean_up_no_longer_needed(
        nnow=str_to_tz_dt('2018-12-25 12:00'), bucket=bucket)
    self.assertEqual([call('mowers')], bucket.delete.call_args_list)
    self.assertEqual(2, TestPhoto.objects.count())
    self.assertFalse(TestPhoto.objects.filter(pk=deleted.pk).exists())


class ResizeTests(TestCase):
  def setUp(self):
    super().setUp()
    self.file = get_test_photo(file_name='humblebrag.jpg')
    self.assertIsNone(self.file.resized_at)
    self.bucket = Mock(spec=Bucket)
    self.mock_image = Mock()
    self.mock_image.width = 1600
    self.mock_image.height = 3200
    self.mock_image.convert.return_value = self.mock_image
    self.mock_image.resize.return_value = self.mock_image
    self.image_opener = Mock(return_value=self.mock_image)
    self.use_os = Mock()
    self.use_os.path = Mock()
    self.use_os.path.exists.return_value = False
    self.use_os.remove = Mock()
    self.file_handle = Mock()
    self.file_handle.close = Mock()
    self.use_open = Mock(return_value=self.file_handle)

  def test_resize_base_class_raises_exception(self):
    try:
      Photo.objects.first().resize(bucket=Mock())
    except Exception as ex:
      self.assertEqual('Call resize on the child class', ex.args[0])

  def test_backup_resize(self):
    resize_all(
        bucket=self.bucket, image_opener=self.image_opener, use_os=self.use_os,
        use_open=self.use_open)
    self.assert_resized()

  def test_resize(self):
    self.file.resize(
        bucket=self.bucket, image_opener=self.image_opener, use_os=self.use_os,
        use_open=self.use_open)
    self.assert_resized()

  def assert_resized(self):
    # Download the existing file.
    self.assertEqual(
        self.bucket.download.call_args_list, [call('humblebrag.jpg')])
    # Open it.
    self.assertEqual(
        self.image_opener.call_args_list, [call('humblebrag.jpg')])
    # Make sure it's in RGB format so it can save as a jpg
    self.assertEqual(
        self.mock_image.convert.call_args_list, [call('RGB')])
    # Resize it.
    self.assertEqual(
        self.mock_image.resize.call_args_list, [call((400, 800))])
    # Write it.
    self.assertEqual(
        self.use_open.call_args_list, [call('humblebrag.jpg', 'wb')])
    self.assertEqual(
        self.mock_image.save.call_args_list,
        [call(self.file_handle, format='JPEG', quality=100)])
    self.assertEqual(
        self.file_handle.close.call_args_list, [call()])
    # Upload it, overwriting the original.
    self.assertEqual(
        self.bucket.upload.call_args_list, [call('humblebrag.jpg')])
    # Clean up locally.
    self.assertEqual(
        [call('humblebrag.jpg')], self.use_os.remove.call_args_list)
    # The database reflects the changes.
    self.file.refresh_from_db()
    self.assertEqual(self.file.file_name, 'humblebrag.jpg')
    self.assertTrue(self.file.resized_at)
