from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0005_add_online_status_and_screenshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="onionprofile",
            name="screenshot_synced",
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
