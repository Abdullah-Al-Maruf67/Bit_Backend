from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth.models import User
from rest_framework.serializers import ModelSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You are authenticated!"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Clear cookies for access and refresh tokens
            response = Response({"message": "Successfully logged out"}, status=200)
            response.delete_cookie("access")
            response.delete_cookie("refresh")
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class NothingView(APIView):
    permission_classes = [AllowAny] 

    def get(self, request):
        return Response("nothing", status=status.HTTP_200_OK)


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password')
        extra_kwargs = {'password': {'write_only': True}}


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.create_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)

            # Set the access token in the response data (for frontend to use)
            response_data = {
                "message": "Login successful",
                "access_token": str(refresh.access_token), 
            }
            response = Response(response_data, status=status.HTTP_200_OK)   

            # Set the refresh token as a cookie
            response.set_cookie(
                key='refresh_token',  # Changed cookie name to 'refresh_token'
                value=str(refresh),
                httponly=True,
                secure=False,       # Use True in production with HTTPS
                samesite='Lax',      # Adjust if needed for your use case
                path='/'
            )

            return response
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class VerifyToken(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            access_token_str = request.data.get('access_token')
            access_token = AccessToken(access_token_str)
            
            # Get the user ID from the token
            user_id = access_token['user_id']

            # Retrieve the User object using the user ID
            user = User.objects.get(id=user_id)

            # Access the username
            username = user.username

            return Response({"Valid": True, "username": username}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)