from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, FieldSubmission

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'is_active', 'date_joined')
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user

class FieldSubmissionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = FieldSubmission
        fields = '__all__'
        extra_kwargs = {
            'is_approved': {'read_only': True},
            'approved_at': {'read_only': True},
            'approved_by': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }
    
    def validate_polygon(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError("Polygon must be a list of coordinates")
        return value
    
    def validate_lat(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value
    
    def validate_lng(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value