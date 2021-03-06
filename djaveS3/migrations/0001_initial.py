# Generated by Django 3.0.5 on 2020-05-05 21:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='SignedFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(db_index=True, max_length=200, unique=True)),
                ('bucket_name', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(db_index=True, max_length=200, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('keep_until', models.DateTimeField(db_index=True, help_text='Once keep_until is in the past, if I can explain_why_can_delete, I will chuck this file.', null=True)),
                ('child_class', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
