# Generated by Django 5.1.4 on 2025-01-12 14:36

import cloudinary.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scores', '0002_remove_message_content_alter_activity_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('student', 'Student'), ('assistant', 'Assistant'), ('staff', 'Staff')], default='student', max_length=20),
        ),
    ]
