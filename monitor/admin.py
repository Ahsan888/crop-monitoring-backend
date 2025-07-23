from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, FieldSubmission

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "field_count", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    
    def field_count(self, obj):
        count = obj.field_submissions.count()
        approved = obj.field_submissions.filter(is_approved=True).count()
        return f"{approved}/{count}"
    field_count.short_description = "Fields (Approved/Total)"

@admin.register(FieldSubmission)
class FieldSubmissionAdmin(admin.ModelAdmin):
    list_display = ("field_name", "user", "field_approval_status", "crop_name", "city", "created_at", "approved_at")
    list_filter = ("is_approved", "crop_name", "country", "created_at")
    search_fields = ("field_name", "user__username", "user__email", "crop_name", "city")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "approved_at", "approved_by")
    
    def field_approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: green; font-weight: bold;">✓ Approved</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">⏳ Pending</span>')
    field_approval_status.short_description = "Status"
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "first_name", "last_name", "email", "phone")
        }),
        ("Field Information", {
            "fields": ("field_name", "crop_name", "plantation_date", "lat", "lng", "polygon", "kml_file")
        }),
        ("Location", {
            "fields": ("city", "country", "zip_code")
        }),
        ("Approval", {
            "fields": ("is_approved", "approved_at", "approved_by"),
            "classes": ("wide",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    actions = ['approve_fields', 'unapprove_fields']
    
    def approve_fields(self, request, queryset):
        count = 0
        for field in queryset.filter(is_approved=False):
            field.approve(request.user)
            count += 1
        self.message_user(request, f"{count} fields were approved and notification emails sent.")
    approve_fields.short_description = "Approve selected fields (sends emails)"
    
    def unapprove_fields(self, request, queryset):
        updated = queryset.update(is_approved=False, approved_at=None, approved_by=None)
        self.message_user(request, f"{updated} fields were unapproved.")
    unapprove_fields.short_description = "Unapprove selected fields"