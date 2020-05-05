from django.urls import path

from djaveS3.views import view_sensitive_image, photo_demo, sign_upload


urlpatterns = [
    path(
        'view_sensitive_image/<bucket>/<file_name>', view_sensitive_image,
        name='view_sensitive_image'),
    path('photo_demo/', photo_demo, name='photo_demo'),
    path('sign_upload/<bucket_name>/', sign_upload, name='sign_upload')]
