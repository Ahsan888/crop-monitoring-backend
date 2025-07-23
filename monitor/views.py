from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.db import transaction
import json
from .models import FieldSubmission, User
from .serializers import UserSerializer, FieldSubmissionSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import logging

# Set up logging
logger = logging.getLogger(__name__)

@csrf_exempt
def health_check(request):
    return JsonResponse({"status": "healthy", "message": "Django app is running"})

class SignupView(APIView):
    def post(self, request):
        """Handle complete signup with user account + field data"""
        
        try:
            with transaction.atomic():
                # Extract user data
                user_data = {
                    'username': request.data.get('username'),
                    'email': request.data.get('email'),
                    'password': request.data.get('password'),
                    'first_name': request.data.get('first_name', ''),
                    'last_name': request.data.get('last_name', ''),
                }
                
                # Validate and create user
                user_serializer = UserSerializer(data=user_data)
                if not user_serializer.is_valid():
                    return Response({
                        'error': 'User data validation failed',
                        'details': user_serializer.errors
                    }, status=400)
                
                user = user_serializer.save()
                
                # Extract field data
                field_data = {
                    'user': user.id,
                    'first_name': request.data.get('first_name'),
                    'last_name': request.data.get('last_name'),
                    'email': request.data.get('email'),
                    'phone': request.data.get('phone'),
                    'city': request.data.get('city'),
                    'country': request.data.get('country'),
                    'zip_code': request.data.get('zip_code'),
                    'field_name': request.data.get('field_name'),
                    'crop_name': request.data.get('crop_name'),
                    'plantation_date': request.data.get('plantation_date'),
                    'lat': request.data.get('lat'),
                    'lng': request.data.get('lng'),
                }
                
                print(f"🔍 [SIGNUP] Processing field data for user: {user.username}")
                print(f"   - Coordinates: {field_data['lat']}, {field_data['lng']}")
                
                # Initialize polygon as empty
                extracted_polygon = None
                
                # 1. CHECK FOR KML FILE FIRST (highest priority)
                if 'kml_file' in request.FILES:
                    kml_file = request.FILES['kml_file']
                    field_data['kml_file'] = kml_file
                    print(f"📁 [SIGNUP] KML file uploaded: {kml_file.name}")
                    
                    # Parse KML file to extract polygon
                    try:
                        extracted_polygon = self.parse_kml_file(kml_file)
                        if extracted_polygon:
                            print(f"✅ [SIGNUP] Extracted {len(extracted_polygon)} coordinates from KML")
                        else:
                            print("⚠️ [SIGNUP] No coordinates found in KML file")
                    except Exception as e:
                        print(f"❌ [SIGNUP] KML parsing failed: {str(e)}")
                
                # 2. CHECK FOR DRAWN POLYGON (second priority)
                if not extracted_polygon:
                    polygon_data = request.data.get('polygon')
                    if polygon_data:
                        print("🖊️ [SIGNUP] Processing drawn polygon data")
                        if isinstance(polygon_data, str):
                            try:
                                extracted_polygon = json.loads(polygon_data)
                                print(f"✅ [SIGNUP] Parsed drawn polygon: {len(extracted_polygon)} points")
                            except json.JSONDecodeError as e:
                                print(f"❌ [SIGNUP] JSON decode error for polygon: {str(e)}")
                        else:
                            extracted_polygon = polygon_data
                            print(f"✅ [SIGNUP] Direct polygon data: {len(extracted_polygon)} points")
                
                # 3. CREATE DEFAULT POLYGON (fallback)
                if not extracted_polygon:
                    print("🔄 [SIGNUP] Creating default polygon around coordinates")
                    try:
                        lat = float(field_data['lat'])
                        lng = float(field_data['lng'])
                        offset = 0.005  # Roughly 500m radius
                        
                        extracted_polygon = [
                            {'lat': lat - offset, 'lng': lng - offset},
                            {'lat': lat - offset, 'lng': lng + offset},
                            {'lat': lat + offset, 'lng': lng + offset},
                            {'lat': lat + offset, 'lng': lng - offset},
                            {'lat': lat - offset, 'lng': lng - offset},  # Close polygon
                        ]
                        print(f"✅ [SIGNUP] Created default polygon with {len(extracted_polygon)} points")
                    except (ValueError, TypeError) as e:
                        print(f"❌ [SIGNUP] Could not create default polygon: {str(e)}")
                        extracted_polygon = []
                
                # Set the final polygon
                field_data['polygon'] = extracted_polygon
                print(f"📍 [SIGNUP] Final polygon has {len(extracted_polygon)} points")
                
                # Create field submission
                field_serializer = FieldSubmissionSerializer(data=field_data)
                if not field_serializer.is_valid():
                    return Response({
                        'error': 'Field data validation failed',
                        'details': field_serializer.errors
                    }, status=400)
                
                field_submission = field_serializer.save()
                print(f"✅ [SIGNUP] Field submission created with ID: {field_submission.id}")
                
                return Response({
                    'message': 'Account created successfully! Your field submission is under review.',
                    'user_id': user.id,
                    'field_submission_id': field_submission.id,
                    'polygon_points': len(extracted_polygon),
                    'status': 'field_pending_approval'
                }, status=201)
                
        except Exception as e:
            print(f"❌ [SIGNUP] Unexpected error: {str(e)}")
            return Response({
                'error': 'Registration failed',
                'details': str(e)
            }, status=400)
    
    def parse_kml_file(self, kml_file):
        """
        Parse KML file to extract polygon coordinates
        Returns list of coordinate dictionaries or None if parsing fails
        """
        try:
            print("🔍 [KML_PARSER] Starting KML file parsing...")
            
            # Read file content
            kml_content = kml_file.read()
            if isinstance(kml_content, bytes):
                kml_content = kml_content.decode('utf-8')
            
            # Reset file pointer for potential later use
            kml_file.seek(0)
            
            print(f"📄 [KML_PARSER] KML content length: {len(kml_content)} characters")
            
            # Parse XML
            root = ET.fromstring(kml_content)
            
            # Define KML namespace
            ns = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            # Look for coordinates in various KML elements
            coordinates = []
            
            # Try to find Polygon coordinates
            for polygon in root.findall('.//kml:Polygon', ns):
                outer_boundary = polygon.find('kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', ns)
                if outer_boundary is not None and outer_boundary.text:
                    coords_text = outer_boundary.text.strip()
                    print(f"📍 [KML_PARSER] Found polygon coordinates: {coords_text[:100]}...")
                    coordinates.extend(self.parse_coordinates_text(coords_text))
            
            # Try to find LineString coordinates if no polygon found
            if not coordinates:
                for linestring in root.findall('.//kml:LineString/kml:coordinates', ns):
                    if linestring.text:
                        coords_text = linestring.text.strip()
                        print(f"📍 [KML_PARSER] Found linestring coordinates: {coords_text[:100]}...")
                        coordinates.extend(self.parse_coordinates_text(coords_text))
            
            # Try to find Point coordinates if no polygon/linestring found
            if not coordinates:
                for point in root.findall('.//kml:Point/kml:coordinates', ns):
                    if point.text:
                        coords_text = point.text.strip()
                        print(f"📍 [KML_PARSER] Found point coordinates: {coords_text}")
                        coordinates.extend(self.parse_coordinates_text(coords_text))
            
            # Try without namespace if nothing found
            if not coordinates:
                print("🔍 [KML_PARSER] Trying without namespace...")
                for elem in root.iter():
                    if elem.tag.endswith('coordinates') and elem.text:
                        coords_text = elem.text.strip()
                        print(f"📍 [KML_PARSER] Found coordinates (no namespace): {coords_text[:100]}...")
                        coordinates.extend(self.parse_coordinates_text(coords_text))
            
            if coordinates:
                print(f"✅ [KML_PARSER] Successfully extracted {len(coordinates)} coordinate points")
                return coordinates
            else:
                print("❌ [KML_PARSER] No coordinates found in KML file")
                return None
                
        except ET.ParseError as e:
            print(f"❌ [KML_PARSER] XML parsing error: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ [KML_PARSER] Unexpected error: {str(e)}")
            return None
    
    def parse_coordinates_text(self, coords_text):
        """
        Parse coordinate text from KML format (lng,lat,alt or lng,lat)
        Returns list of {'lat': float, 'lng': float} dictionaries
        """
        coordinates = []
        
        try:
            # Split by whitespace and newlines
            coord_pairs = re.split(r'\s+', coords_text.strip())
            
            for coord_pair in coord_pairs:
                if not coord_pair:
                    continue
                    
                # Split by comma (KML format is lng,lat,alt or lng,lat)
                parts = coord_pair.split(',')
                
                if len(parts) >= 2:
                    try:
                        lng = float(parts[0])
                        lat = float(parts[1])
                        
                        # Validate coordinate ranges
                        if -180 <= lng <= 180 and -90 <= lat <= 90:
                            coordinates.append({'lat': lat, 'lng': lng})
                        else:
                            print(f"⚠️ [KML_PARSER] Invalid coordinate range: {lat}, {lng}")
                    except ValueError:
                        print(f"⚠️ [KML_PARSER] Could not parse coordinate pair: {coord_pair}")
        
        except Exception as e:
            print(f"❌ [KML_PARSER] Error parsing coordinates text: {str(e)}")

class UserFieldsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get only the authenticated user's approved fields"""
        fields = FieldSubmission.objects.filter(user=request.user, is_approved=True)
        serializer = FieldSubmissionSerializer(fields, many=True)
        return Response(serializer.data)

class ApprovedFieldsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Get all approved fields for public display - DEPRECATED"""
        # This endpoint should probably be removed or restricted
        # For now, return empty to prevent data leakage
        return Response([])

class FieldSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Add new field for authenticated users"""
        data = request.data.copy()
        data["user"] = request.user.id
        serializer = FieldSubmissionSerializer(data=data)
        if serializer.is_valid():
            field_submission = serializer.save()
            return Response({
                "message": "Field submitted for approval",
                "field_id": field_submission.id
            }, status=201)
        return Response(serializer.errors, status=400)

# NEW: Sentinel Hub Token Proxy
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])  # Only authenticated users can get tokens
def get_sentinel_token(request):
    """
    Proxy endpoint to get Sentinel Hub access tokens
    This avoids CORS issues by making the request from Django backend
    """
    try:
        logger.info("🔄 [DJANGO] Fetching Sentinel Hub token for user: %s", request.user.username)
        
        # Sentinel Hub credentials (move to environment variables in production)
        CLIENT_ID = "sh-1a358ad6-d52b-4ff7-a053-66d024714ac7"
        CLIENT_SECRET = "HQ5Tl4HAJdK6hMNOJAgOk9ileEcx3A6y"
        TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        
        # Prepare the token request
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        logger.info("📤 [DJANGO] Making token request to Copernicus...")
        
        # Make the request to Copernicus
        response = requests.post(
            TOKEN_URL,
            data=token_data,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        logger.info("📥 [DJANGO] Token response status: %s", response.status_code)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Log success (without exposing full token)
            logger.info("✅ [DJANGO] Token fetched successfully")
            logger.info("   - Expires in: %s seconds", token_data.get('expires_in', 'unknown'))
            logger.info("   - Token type: %s", token_data.get('token_type', 'unknown'))
            
            # Return the token data to frontend
            return JsonResponse({
                'success': True,
                'access_token': token_data.get('access_token'),
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_in': token_data.get('expires_in', 3600),
                'scope': token_data.get('scope'),
            })
        else:
            # Log error details
            logger.error("❌ [DJANGO] Token request failed with status: %s", response.status_code)
            logger.error("❌ [DJANGO] Error response: %s", response.text)
            
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch token from Copernicus',
                'status_code': response.status_code,
                'details': response.text[:200]  # First 200 chars of error
            }, status=400)
            
    except requests.exceptions.Timeout:
        logger.error("❌ [DJANGO] Token request timed out")
        return JsonResponse({
            'success': False,
            'error': 'Token request timed out'
        }, status=504)
        
    except requests.exceptions.RequestException as e:
        logger.error("❌ [DJANGO] Network error during token request: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': 'Network error during token request',
            'details': str(e)
        }, status=500)
        
    except Exception as e:
        logger.error("❌ [DJANGO] Unexpected error during token request: %s", str(e))
        return JsonResponse({
            'success': False,
            'error': 'Unexpected error during token request',
            'details': str(e)
        }, status=500)

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def user_profile(request):
    """Get current user profile information"""
    user = request.user
    
    # Get user's field submissions
    field_submissions = FieldSubmission.objects.filter(user=user)
    approved_fields = field_submissions.filter(is_approved=True).count()
    pending_fields = field_submissions.filter(is_approved=False).count()
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'date_joined': user.date_joined.isoformat(),
        'approved_fields_count': approved_fields,
        'pending_fields_count': pending_fields,
        'can_access_dashboard': True,  # Users can always access dashboard
        'has_approved_fields': approved_fields > 0,
    })

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def approval_status(request):
    """Check field approval status for user"""
    user = request.user
    field_submissions = FieldSubmission.objects.filter(user=user)
    
    return Response({
        'user_approved': True,  # Users are always approved
        'fields': [
            {
                'id': field.id,
                'field_name': field.field_name,
                'is_approved': field.is_approved,
                'created_at': field.created_at.isoformat(),
                'approved_at': field.approved_at.isoformat() if hasattr(field, 'approved_at') and field.approved_at else None,
            }
            for field in field_submissions
        ],
        'summary': {
            'total_fields': field_submissions.count(),
            'approved_fields': field_submissions.filter(is_approved=True).count(),
            'pending_fields': field_submissions.filter(is_approved=False).count(),
        }
    })