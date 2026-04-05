# Generated manually for MobileAppReleaseConfig

import uuid

from django.db import migrations, models


def seed_singleton(apps, schema_editor):
    MobileAppReleaseConfig = apps.get_model("core", "MobileAppReleaseConfig")
    if not MobileAppReleaseConfig.objects.exists():
        MobileAppReleaseConfig.objects.create(
            id=uuid.uuid4(),
            current_app_version=1,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_paymenttransaction_purpose"),
    ]

    operations = [
        migrations.CreateModel(
            name="MobileAppReleaseConfig",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("current_app_version", models.PositiveIntegerField(default=1)),
                ("android_file", models.FileField(blank=True, null=True, upload_to="releases/")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mobile app release",
                "verbose_name_plural": "Mobile app release",
            },
        ),
        migrations.RunPython(seed_singleton, migrations.RunPython.noop),
    ]
