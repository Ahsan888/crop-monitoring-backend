from django.urls import path
from .views import (
    SignupView, ApprovedFieldsView, FieldSubmissionView, 
    UserFieldsView, get_sentinel_token,
    user_profile, approval_status
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("fields/", UserFieldsView.as_view(), name="user-fields"),
    path("fields/add/", FieldSubmissionView.as_view(), name="add-field"),
    path("user/profile/", user_profile, name="user-profile"),
    path("user/approval-status/", approval_status, name="approval-status"),
    path("sentinel/token/", get_sentinel_token, name="sentinel-token"),
]