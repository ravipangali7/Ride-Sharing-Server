# Generated manually for JSON admin CRUD without multipart uploads.

from django.db import migrations, models
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_mobile_app_release_config"),
    ]

    operations = [
        migrations.AlterField(
            model_name="restaurant",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
        migrations.AlterField(
            model_name="restaurant",
            name="cover_photo",
            field=models.ImageField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
        migrations.AlterField(
            model_name="menuitem",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
        migrations.AlterField(
            model_name="vendor",
            name="store_logo",
            field=models.ImageField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
        migrations.AlterField(
            model_name="vendor",
            name="store_banner",
            field=models.ImageField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
        migrations.AlterField(
            model_name="vendor",
            name="registration_doc",
            field=models.FileField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
        migrations.AlterField(
            model_name="roomownerprofile",
            name="citizenship_photo",
            field=models.ImageField(blank=True, null=True, upload_to=core.models.upload_media),
        ),
    ]
