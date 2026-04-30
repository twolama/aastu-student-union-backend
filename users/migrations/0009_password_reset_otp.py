from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_user_bio'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordResetOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('otp', models.CharField(max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('is_used', models.BooleanField(default=False)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_otps', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Password Reset OTP',
                'verbose_name_plural': 'Password Reset OTPs',
                'indexes': [
                    models.Index(fields=['otp'], name='users_pr_otp_idx'),
                    models.Index(fields=['user', 'is_used', 'expires_at'], name='users_pr_user_idx'),
                ],
            },
        ),
    ]
