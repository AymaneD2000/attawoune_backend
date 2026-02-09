from rest_framework import viewsets, generics, status, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, RegisterSerializer
)

User = get_user_model()


class IsAdminOrSelf(permissions.BasePermission):
    """Permission to only allow admins or the user themselves."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_admin or obj == request.user


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users."""
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['username', 'created_at', 'last_login']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password."""
        user = self.get_object()
        serializer = PasswordChangeSerializer(data=request.data)

        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": "Mot de passe incorrect."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Mot de passe modifié avec succès."})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get users filtered by role."""
        role = request.query_params.get('role', None)
        if role:
            users = User.objects.filter(role=role.upper())
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "Role parameter required"},
            status=status.HTTP_400_BAD_REQUEST
        )


class CurrentUserView(APIView):
    """View for getting current authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(generics.CreateAPIView):
    """View for user registration."""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
