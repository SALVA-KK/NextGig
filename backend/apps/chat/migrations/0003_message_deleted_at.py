from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_messagerequest_conversation_is_direct_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
