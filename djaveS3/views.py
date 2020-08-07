from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render


from djaveS3.file_types import (
    suffix_from_file_type, content_type_from_file_name)
from djaveS3.generate_presigned_post import generate_presigned_post
from djaveS3.models.bucket import Bucket
from djaveS3.random_string import random_string


def sensitive_file_response(file):
  """ This function is helpful to construct your own views that will return the
  actual bytes for a sensitive image. You need to pass the literal bytes for
  sensitive photos through your server in order to put security checks in front
  of those bytes. So for instance you might put something like this in your
  views.py:

  def view_photo_of_steve(request, file_name):
    if request.user.username != 'Steve':
      raise Exception('Only Steve may look at photos of Steve!')
    return sensitive_file_response('steves_s3_bucket', file_name)

  def steves_page(request):
    return render(
        request, 'steve.html', {'steve_photo_url': reverse(
            'view_photo_of_steve',
            kwargs={'file_name': SteveFile.objects.first().file_name})})

  And something like this in steve.html or whatever

  <img src="{{ steve_photo_url }}">
  """
  bucket_config = file.bucket_config()
  if bucket_config.is_public:
    raise Exception((
        'S3 bucket {} is public, so performance-wise, it is best to just '
        'leave this server out of it entirely and use public_photo_url '
        'in djaveS3.S3 instead.').format(bucket_config.name))
  img_bytes = Bucket(bucket_config).file_bytes(file.file_name)
  if img_bytes:
    return HttpResponse(
        img_bytes, content_type=content_type_from_file_name(file.file_name))
  return Http404()


def photo_demo(request):
  """ This simple page is what I'm using to get photo management working. """
  return render(request, 'photo_demo.html', {})


def sign_upload(request, bucket_name, boto_client=None):
  """ The user is about to try to upload a photo directly to S3. We gotta
  sign it and say where it goes. """
  file_type = request.GET.get('file_type', '')
  if not file_type:
    return HttpResponse(
        'You have to include a file_type parameter in the query string',
        status=400)
  suffix = suffix_from_file_type(file_type)
  if not suffix:
    raise Exception(
        'Not sure what suffix a {} file is supposed to have'.format(file_type))

  destination_file_name = '{}.{}'.format(random_string(), suffix)
  presigned_post = generate_presigned_post(
      bucket_name, destination_file_name, file_type, boto_client=boto_client)

  return JsonResponse({
      'presigned_post': presigned_post,
      'destination_file_name': destination_file_name})
