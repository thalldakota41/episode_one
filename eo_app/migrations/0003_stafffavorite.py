# Generated by Django 4.2.1 on 2023-06-23 18:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eo_app', '0002_creator_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eo_app.show')),
            ],
        ),
    ]
