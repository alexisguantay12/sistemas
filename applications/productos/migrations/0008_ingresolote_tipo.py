# Generated by Django 3.2.25 on 2025-06-23 21:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0007_auto_20250623_0002'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingresolote',
            name='tipo',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
