"""
Permission classes for role-based access control.

This module provides permission classes for the Université Attawoune Management System API.
Permissions are based on user roles: ADMIN, DEAN, TEACHER, STUDENT, ACCOUNTANT, SECRETARY.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


# Base Permission Classes

class IsAdmin(BasePermission):
    """
    Allow access only to admin users.
    
    Admins have full access to all endpoints and operations.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsDean(BasePermission):
    """
    Allow access only to dean users.
    
    Deans have access to faculty and department management.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'DEAN'


class IsTeacher(BasePermission):
    """
    Allow access only to teacher users.
    
    Teachers have access to their assigned courses, grades, and schedules.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'TEACHER'


class IsStudent(BasePermission):
    """
    Allow access only to student users.
    
    Students have access to their own data (grades, enrollments, attendance).
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'STUDENT'


class IsAccountant(BasePermission):
    """
    Allow access only to accountant users.
    
    Accountants have full access to financial data (payments, salaries, expenses).
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ACCOUNTANT'


class IsSecretary(BasePermission):
    """
    Allow access only to secretary users.
    
    Secretaries have access to student management and enrollment operations.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'SECRETARY'


# Combined Permission Classes

class IsAdminOrReadOnly(BasePermission):
    """
    Admin users can modify, all authenticated users can read.
    
    Useful for reference data that should be readable by all but only modifiable by admins.
    """
    
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsTeacherOrAdmin(BasePermission):
    """
    Allow access to teachers and admins.
    
    Used for endpoints that both teachers and admins should access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['TEACHER', 'ADMIN']
        )


class IsAccountantOrAdmin(BasePermission):
    """
    Allow access to accountants and admins.
    
    Used for financial endpoints that both accountants and admins should access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['ACCOUNTANT', 'ADMIN']
        )


class IsSecretaryOrAdmin(BasePermission):
    """
    Allow access to secretaries and admins.
    
    Used for student management endpoints that both secretaries and admins should access.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['SECRETARY', 'ADMIN']
        )


# Object-Level Permission Classes

class IsOwnerOrAdmin(BasePermission):
    """
    Allow access to object owner or admin.
    
    Checks if the user owns the object (via user field) or is an admin.
    Used for endpoints where users should only access their own data.
    """
    
    def has_permission(self, request, view):
        # Allow authenticated users to proceed to object-level check
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins have full access
        if request.user.role == 'ADMIN':
            return True
        
        # Check if user owns the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsTeacherOfCourse(BasePermission):
    """
    Allow access if teacher is assigned to the course.
    
    Checks if the teacher is assigned to the course through TeacherCourse relationship.
    Used for course-related endpoints where only assigned teachers should have access.
    """
    
    def has_permission(self, request, view):
        # Allow authenticated users to proceed to object-level check
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins have full access
        if request.user.role == 'ADMIN':
            return True
        
        # Check if user is a teacher
        if request.user.role != 'TEACHER':
            return False
        
        # Check if teacher is assigned to this course
        # The object could be a Course, Grade, or other course-related model
        if hasattr(obj, 'teacher_assignments'):
            # Object is a Course
            return obj.teacher_assignments.filter(
                teacher__user=request.user
            ).exists()
        elif hasattr(obj, 'course'):
            # Object has a course field (Grade, Exam, etc.)
            return obj.course.teacher_assignments.filter(
                teacher__user=request.user
            ).exists()
        
        return False
