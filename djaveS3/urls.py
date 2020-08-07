from django.urls import path

from djaveS3.views import photo_demo, sign_upload


djave_s3_urls = [
    path('photo_demo/', photo_demo, name='photo_demo'),
    path('sign_upload/<bucket_name>/', sign_upload, name='sign_upload')]
