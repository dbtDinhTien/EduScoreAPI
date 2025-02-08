# Generated by Django 5.1.4 on 2025-02-04 08:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scores', '0020_registration_active_registration_created_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluationcriteria',
            name='activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='evaluation_criteria', to='scores.activity'),
        ),
    ]
