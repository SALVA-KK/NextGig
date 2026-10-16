from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_device_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('new_application', 'New Application Received'),
                    ('application_status_changed', 'Application Status Updated'),
                    ('application_withdrawn', 'Application Withdrawn'),
                    ('opportunity_expired', 'Opportunity Expired'),
                    ('opportunity_force_closed', 'Opportunity Force Closed'),
                    ('opportunity_reopened', 'Opportunity Reopened'),
                    ('provider_welcome', 'Welcome Provider'),
                    ('provider_verified', 'Provider Verified'),
                    ('provider_unverified', 'Provider Unverified'),
                    ('recommendations_digest', 'Daily Recommendations Digest'),
                    ('new_chat_message', 'New Chat Message'),
                ],
                max_length=50,
            ),
        ),
    ]
