from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin superuser'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser(
                username='admin',
                email='admin@cropmonitoring.com',
                password='CropAdmin123!',
                first_name='Admin',
                last_name='User'
            )
            # Ensure user is approved if your model has that field
            if hasattr(user, 'is_approved'):
                user.is_approved = True
                user.save()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Admin superuser created successfully!')
            )
            self.stdout.write(f'Username: admin')
            self.stdout.write(f'Password: CropAdmin123!')
        else:
            self.stdout.write('ℹ️ Admin user already exists')