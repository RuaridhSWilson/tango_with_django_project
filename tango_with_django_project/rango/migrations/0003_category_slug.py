# Generated by Django 2.2.9 on 2020-01-19 18:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rango', '0002_auto_20200119_1247'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='slug',
            field=models.SlugField(default='default'),
            preserve_default=False,
        ),
    ]