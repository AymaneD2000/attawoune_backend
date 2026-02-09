"""
ViewSets for teachers app models.

This module provides ViewSets for managing teacher-related data:
- Teacher: Teacher profiles with department and contract information
- TeacherCourse: Teacher course assignments for semesters
- TeacherContract: Teacher employment contracts
"""

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.permissions import IsAdminOrReadOnly, IsSecretaryOrAdmin
from .models import Teacher, TeacherCourse, TeacherContract
from .serializers import (
    TeacherListSerializer, TeacherDetailSerializer, TeacherCreateSerializer,
    TeacherCourseListSerializer, TeacherCourseDetailSerializer, TeacherCourseCreateSerializer,
    TeacherContractListSerializer, TeacherContractDetailSerializer, TeacherContractCreateSerializer
)


class TeacherViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teachers.
    
    Provides:
    - List: GET /api/v1/teachers/
    - Create: POST /api/v1/teachers/
    - Retrieve: GET /api/v1/teachers/{id}/
    - Update: PUT/PATCH /api/v1/teachers/{id}/
    - Delete: DELETE /api/v1/teachers/{id}/
    
    Custom Actions:
    - courses: GET /api/v1/teachers/{id}/courses/
    - schedules: GET /api/v1/teachers/{id}/schedules/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin and Secretary only
    
    Filtering:
    - department: Filter by department
    - rank: Filter by teacher rank (ASSISTANT, LECTURER, SENIOR_LECTURER, ASSOCIATE_PROFESSOR, PROFESSOR)
    - contract_type: Filter by contract type (PERMANENT, CONTRACT, VISITING, PART_TIME)
    - is_active: Filter by active status
    
    Searching:
    - employee_id, user first name, user last name, user email, specialization
    
    Ordering:
    - employee_id, hire_date, created_at
    """
    
    queryset = Teacher.objects.select_related(
        'user', 'department', 'department__faculty'
    ).prefetch_related(
        'course_assignments', 'contracts'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'rank', 'contract_type', 'is_active']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'user__email', 'specialization']
    ordering_fields = ['employee_id', 'hire_date', 'created_at']
    ordering = ['employee_id']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TeacherListSerializer
        elif self.action == 'retrieve':
            return TeacherDetailSerializer
        elif self.action == 'create':
            return TeacherCreateSerializer
        return TeacherDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve', 'courses', 'schedules']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all teachers
        - Teacher: See only their own profile
        - Others: See all teachers (read-only)
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see all teachers but only modify their own profile
            return self.queryset
        
        # Other roles can see all teachers (read-only)
        return self.queryset

    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        """
        Get all courses assigned to this teacher.
        
        Returns all TeacherCourse assignments for the teacher, grouped by semester.
        """
        teacher = self.get_object()
        
        # Get course assignments
        assignments = TeacherCourse.objects.filter(
            teacher=teacher
        ).select_related(
            'course', 'course__program', 'semester', 'semester__academic_year'
        ).order_by('-semester__academic_year__start_date', 'course__name')
        
        serializer = TeacherCourseListSerializer(assignments, many=True)
        
        # Group by semester
        grouped = {}
        for assignment in assignments:
            semester_key = f"{assignment.semester.academic_year.name} - {assignment.semester.get_semester_type_display()}"
            if semester_key not in grouped:
                grouped[semester_key] = []
            grouped[semester_key].append({
                'id': assignment.id,
                'course_name': assignment.course.name,
                'course_code': assignment.course.code,
                'program_name': assignment.course.program.name if assignment.course.program else None,
                'is_primary': assignment.is_primary,
                # 'hours_assigned': assignment.hours_assigned, # Field removed from model
            })
        
        return Response({
            'count': assignments.count(),
            'teacher': {
                'id': teacher.id,
                'name': teacher.user.get_full_name(),
                'employee_id': teacher.employee_id,
            },
            'by_semester': grouped,
            'results': serializer.data
        })

    @action(detail=True, methods=['get'])
    def schedules(self, request, pk=None):
        """
        Get schedule for this teacher.
        
        Returns all scheduled classes for the teacher in the current semester.
        """
        from apps.scheduling.models import Schedule
        from apps.university.models import Semester
        
        teacher = self.get_object()
        
        # Get current semester
        current_semester = Semester.objects.filter(is_current=True).first()
        
        # Get schedules
        schedules = Schedule.objects.filter(
            teacher=teacher
        ).select_related(
            'course', 'classroom', 'time_slot', 'semester'
        )
        
        if current_semester:
            schedules = schedules.filter(semester=current_semester)
        
        schedules = schedules.order_by('time_slot__day', 'time_slot__start_time')
        
        # Format schedule by day
        schedule_by_day = {}
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        for schedule in schedules:
            day_name = days[schedule.time_slot.day] if schedule.time_slot else 'Non défini'
            if day_name not in schedule_by_day:
                schedule_by_day[day_name] = []
            
            schedule_by_day[day_name].append({
                'id': schedule.id,
                'course_name': schedule.course.name if schedule.course else 'N/A',
                'course_code': schedule.course.code if schedule.course else 'N/A',
                'classroom': schedule.classroom.name if schedule.classroom else 'N/A',
                'start_time': schedule.time_slot.start_time.strftime('%H:%M') if schedule.time_slot else None,
                'end_time': schedule.time_slot.end_time.strftime('%H:%M') if schedule.time_slot else None,
            })
        
        return Response({
            'count': schedules.count(),
            'teacher': {
                'id': teacher.id,
                'name': teacher.user.get_full_name(),
                'employee_id': teacher.employee_id,
            },
            'current_semester': current_semester.name if current_semester else None,
            'schedule_by_day': schedule_by_day,
        })


class TeacherCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher course assignments.
    
    Provides:
    - List: GET /api/v1/teacher-courses/
    - Create: POST /api/v1/teacher-courses/
    - Retrieve: GET /api/v1/teacher-courses/{id}/
    - Update: PUT/PATCH /api/v1/teacher-courses/{id}/
    - Delete: DELETE /api/v1/teacher-courses/{id}/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin and Secretary only
    
    Filtering:
    - teacher: Filter by teacher
    - course: Filter by course
    - semester: Filter by semester
    - is_primary: Filter by primary teacher status
    
    Ordering:
    - assigned_date, created_at
    """
    
    queryset = TeacherCourse.objects.select_related(
        'teacher', 'teacher__user', 'teacher__department',
        'course', 'course__program', 'semester', 'semester__academic_year'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['teacher', 'course', 'semester', 'is_primary']
    search_fields = [
        'teacher__employee_id', 'teacher__user__first_name', 'teacher__user__last_name',
        'course__name', 'course__code'
    ]
    ordering_fields = ['assigned_date', 'created_at']
    ordering = ['-semester', 'teacher', 'course']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TeacherCourseListSerializer
        elif self.action == 'retrieve':
            return TeacherCourseDetailSerializer
        elif self.action == 'create':
            return TeacherCourseCreateSerializer
        return TeacherCourseDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all assignments
        - Teacher: See only their own assignments
        - Student: See assignments for their enrolled courses
        - Others: See all assignments (read-only)
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see only their own course assignments
            return self.queryset.filter(teacher__user=user)
        elif user.role == 'STUDENT':
            # Students can see assignments for courses in their program
            return self.queryset.filter(
                course__program__students__user=user
            ).distinct()
        
        # Other roles can see all assignments (read-only)
        return self.queryset


class TeacherContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher contracts.
    
    Provides:
    - List: GET /api/v1/teacher-contracts/
    - Create: POST /api/v1/teacher-contracts/
    - Retrieve: GET /api/v1/teacher-contracts/{id}/
    - Update: PUT/PATCH /api/v1/teacher-contracts/{id}/
    - Delete: DELETE /api/v1/teacher-contracts/{id}/
    
    Permissions:
    - Read: Admin and the contract owner (teacher)
    - Write: Admin only
    
    Filtering:
    - teacher: Filter by teacher
    - status: Filter by contract status (ACTIVE, EXPIRED, TERMINATED, RENEWED)
    
    Searching:
    - contract_number, teacher employee_id, teacher name
    
    Ordering:
    - start_date, end_date, created_at
    """
    
    queryset = TeacherContract.objects.select_related(
        'teacher', 'teacher__user', 'teacher__department'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['teacher', 'status']
    search_fields = [
        'contract_number', 'teacher__employee_id',
        'teacher__user__first_name', 'teacher__user__last_name'
    ]
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TeacherContractListSerializer
        elif self.action == 'retrieve':
            return TeacherContractDetailSerializer
        elif self.action == 'create':
            return TeacherContractCreateSerializer
        return TeacherContractDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: Admin and contract owner
        - Write operations: Admin only
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all contracts
        - Teacher: See only their own contracts
        - Others: No access
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can only see their own contracts
            return self.queryset.filter(teacher__user=user)
        
        # Other roles have no access to contracts
        return self.queryset.none()
