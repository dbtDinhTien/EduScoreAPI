from rest_framework import permissions


class OwnerPerms(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, instance):
        return super().has_permission(request, view) and request.user == instance.user

class DestroyActivityPerms(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return super().has_permission(request, view) and (
            request.user.is_superuser or (request.user.is_staff and obj.created_by == request.user)
        )

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff