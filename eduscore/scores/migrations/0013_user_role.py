# Generated by Django 5.1.4 on 2025-01-24 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scores', '0012_evaluationcriteria_evaluationgroup_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('admin', 'Admin'), ('staff', 'Staff'), ('student', 'Student')], default='student', max_length=10),
        ),
    ]
