from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    # Remove is_approved field - users are auto-approved
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} (Active: {self.is_active})"

class FieldSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='field_submissions')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Location Information
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=10)
    zip_code = models.CharField(max_length=10)
    
    # Field Information
    field_name = models.CharField(max_length=100)
    crop_name = models.CharField(max_length=100)
    plantation_date = models.DateField()
    
    # Geographic Data
    lat = models.FloatField()
    lng = models.FloatField()
    polygon = models.JSONField(blank=True, null=True)
    kml_file = models.FileField(upload_to='kml_files/', null=True, blank=True)
    
    # Approval Status - Only fields need approval
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_fields')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Field Submission"
        verbose_name_plural = "Field Submissions"

    def __str__(self):
        return f"{self.field_name} - {self.user.username} ({'Approved' if self.is_approved else 'Pending'})"

    def approve(self, approved_by_user):
        """Approve the field and send notification email"""
        self.is_approved = True
        self.approved_at = timezone.now()
        self.approved_by = approved_by_user
        self.save()
        
        # Send approval email
        try:
            send_mail(
                subject=f'Field "{self.field_name}" Approved',
                message=f'''
Dear {self.first_name} {self.last_name},

Your field "{self.field_name}" has been approved and is now active in the Crop Monitoring System.

Field Details:
- Field Name: {self.field_name}
- Crop: {self.crop_name}
- Location: {self.city}, {self.country}
- Plantation Date: {self.plantation_date}

You can now access your field data through the dashboard.

Best regards,
Crop Monitoring Team
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send approval email: {e}")

# Email notification signals
@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send welcome email when user is created"""
    if created:
        try:
            send_mail(
                subject='Welcome to Crop Monitoring System',
                message=f'''
Dear {instance.first_name} {instance.last_name},

Welcome to the Crop Monitoring System!

Your account has been created successfully. Your field submission is now under review by our administrators.

You will receive another email once your field is approved, after which you can access the full dashboard.

Login Details:
- Username: {instance.username}
- Dashboard: http://localhost:3000

Best regards,
Crop Monitoring Team
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send welcome email: {e}")