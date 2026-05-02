from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('venues', '0005_alter_venue_google_maps_url'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='venue',
            options={
                'verbose_name': 'Venue',
                'verbose_name_plural': 'Venues',
                'permissions': [
                    ('manage_venue', 'Can manage venues'),
                    ('manage_venue_gallery', 'Can manage venue gallery images'),
                ],
            },
        ),
    ]
