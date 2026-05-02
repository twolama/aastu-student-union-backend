from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_alter_booking_event'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='booking',
            options={
                'verbose_name': 'Booking',
                'verbose_name_plural': 'Bookings',
                'permissions': [
                    ('approve_booking', 'Can approve booking requests'),
                    ('reject_booking', 'Can reject booking requests'),
                ],
            },
        ),
    ]
