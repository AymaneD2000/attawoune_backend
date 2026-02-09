"""
ViewSets for university app models.

This module provides ViewSets for managing university structure:
- AcademicYear: Academic years with semesters
- Semester: Semesters within academic years
- Faculty: University faculties
- Department: Departments within faculties
- Level: Academic levels (L1, L2, L3, M1, M2, D1, D2, D3)
- Program: Academic programs/filières
- Classroom: Physical classrooms with equipment
"""

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.permissions import IsAdminOrReadOnly, IsSecretaryOrAdmin
from .models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)
from .serializers import (
    AcademicYearListSerializer, AcademicYearDetailSerializer, AcademicYearSerializer,
    SemesterListSerializer, SemesterDetailSerializer, SemesterSerializer,
    FacultyListSerializer, FacultyDetailSerializer, FacultySerializer,
    DepartmentListSerializer, DepartmentDetailSerializer, DepartmentSerializer,
    LevelListSerializer, LevelDetailSerializer, LevelSerializer,
    ProgramListSerializer, ProgramDetailSerializer, ProgramSerializer,
    ClassroomListSerializer, ClassroomDetailSerializer, ClassroomSerializer
)


class AcademicYearViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing academic years.
    
    Provides:
    - List: GET /api/v1/academic-years/
    - Create: POST /api/v1/academic-years/
    - Retrieve: GET /api/v1/academic-years/{id}/
    - Update: PUT/PATCH /api/v1/academic-years/{id}/
    - Delete: DELETE /api/v1/academic-years/{id}/
    
    Custom Actions:
    - set_current: POST /api/v1/academic-years/{id}/set_current/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin only
    
    Filtering:
    - is_current: Filter by current academic year
    
    Ordering:
    - start_date, name, created_at
    """
    
    queryset = AcademicYear.objects.prefetch_related('semesters').all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_current']
    search_fields = ['name']
    ordering_fields = ['start_date', 'name', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return AcademicYearListSerializer
        elif self.action == 'retrieve':
            return AcademicYearDetailSerializer
        return AcademicYearSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def set_current(self, request, pk=None):
        """
        Set this academic year as the current one.
        
        Unsets any other current academic year.
        """
        academic_year = self.get_object()
        
        # Unset all other academic years
        AcademicYear.objects.exclude(pk=pk).update(is_current=False)
        
        # Set this one as current
        academic_year.is_current = True
        academic_year.save()
        
        serializer = AcademicYearDetailSerializer(academic_year)
        return Response({
            'message': f"L'année académique {academic_year.name} est maintenant l'année courante.",
            'academic_year': serializer.data
        })


class SemesterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing semesters.
    
    Provides:
    - List: GET /api/v1/semesters/
    - Create: POST /api/v1/semesters/
    - Retrieve: GET /api/v1/semesters/{id}/
    - Update: PUT/PATCH /api/v1/semesters/{id}/
    - Delete: DELETE /api/v1/semesters/{id}/
    
    Custom Actions:
    - set_current: POST /api/v1/semesters/{id}/set_current/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin only
    
    Filtering:
    - academic_year: Filter by academic year
    - semester_type: Filter by semester type (S1, S2)
    - is_current: Filter by current semester
    
    Ordering:
    - start_date, created_at
    """
    
    queryset = Semester.objects.select_related('academic_year').all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['academic_year', 'semester_type', 'is_current']
    search_fields = ['academic_year__name']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['academic_year', 'semester_type']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SemesterListSerializer
        elif self.action == 'retrieve':
            return SemesterDetailSerializer
        return SemesterSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def set_current(self, request, pk=None):
        """
        Set this semester as the current one.
        
        Unsets any other current semester.
        """
        semester = self.get_object()
        
        # Unset all other semesters
        Semester.objects.exclude(pk=pk).update(is_current=False)
        
        # Set this one as current
        semester.is_current = True
        semester.save()
        
        serializer = SemesterDetailSerializer(semester)
        return Response({
            'message': f"Le {semester.get_semester_type_display()} de {semester.academic_year.name} est maintenant le semestre courant.",
            'semester': serializer.data
        })


class FacultyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing faculties.
    
    Provides:
    - List: GET /api/v1/faculties/
    - Create: POST /api/v1/faculties/
    - Retrieve: GET /api/v1/faculties/{id}/
    - Update: PUT/PATCH /api/v1/faculties/{id}/
    - Delete: DELETE /api/v1/faculties/{id}/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin only
    
    Filtering:
    - dean: Filter by dean user
    
    Searching:
    - name, code, description
    
    Ordering:
    - name, code, created_at
    """
    
    queryset = Faculty.objects.select_related('dean').prefetch_related('departments').all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['dean']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return FacultyListSerializer
        elif self.action == 'retrieve':
            return FacultyDetailSerializer
        return FacultySerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing departments.
    
    Provides:
    - List: GET /api/v1/departments/
    - Create: POST /api/v1/departments/
    - Retrieve: GET /api/v1/departments/{id}/
    - Update: PUT/PATCH /api/v1/departments/{id}/
    - Delete: DELETE /api/v1/departments/{id}/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin only
    
    Filtering:
    - faculty: Filter by faculty
    - head: Filter by department head
    
    Searching:
    - name, code, description
    
    Ordering:
    - name, code, created_at
    """
    
    queryset = Department.objects.select_related(
        'faculty', 'head'
    ).prefetch_related(
        'programs', 'teachers'
    ).all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['faculty', 'head']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['faculty', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DepartmentListSerializer
        elif self.action == 'retrieve':
            return DepartmentDetailSerializer
        return DepartmentSerializer


class LevelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing academic levels.
    
    Provides:
    - List: GET /api/v1/levels/
    - Create: POST /api/v1/levels/
    - Retrieve: GET /api/v1/levels/{id}/
    - Update: PUT/PATCH /api/v1/levels/{id}/
    - Delete: DELETE /api/v1/levels/{id}/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin only
    
    Filtering:
    - name: Filter by level name (L1, L2, L3, M1, M2, D1, D2, D3)
    
    Ordering:
    - order, name
    """
    
    queryset = Level.objects.prefetch_related('programs').all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name']
    ordering_fields = ['order', 'name']
    ordering = ['order']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return LevelListSerializer
        elif self.action == 'retrieve':
            return LevelDetailSerializer
        return LevelSerializer


class ProgramViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing academic programs.
    
    Provides:
    - List: GET /api/v1/programs/
    - Create: POST /api/v1/programs/
    - Retrieve: GET /api/v1/programs/{id}/
    - Update: PUT/PATCH /api/v1/programs/{id}/
    - Delete: DELETE /api/v1/programs/{id}/
    
    Custom Actions:
    - courses: GET /api/v1/programs/{id}/courses/
    - students: GET /api/v1/programs/{id}/students/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin and Secretary
    
    Filtering:
    - department: Filter by department
    - level: Filter by level
    - is_active: Filter by active status
    
    Searching:
    - name, code, description
    
    Ordering:
    - name, code, created_at
    """
    
    queryset = Program.objects.select_related(
        'department', 'department__faculty'
    ).prefetch_related(
        'students', 'courses', 'levels'
    ).all()
    permission_classes = [IsAuthenticated, IsSecretaryOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'levels', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['department', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ProgramListSerializer
        elif self.action == 'retrieve':
            return ProgramDetailSerializer
        return ProgramSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve', 'courses', 'students']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]

    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        """
        Get all courses in this program.
        """
        from apps.academics.models import Course
        
        program = self.get_object()
        courses = Course.objects.filter(program=program).order_by('semester_type', 'name')
        
        return Response({
            'count': courses.count(),
            'program': {
                'id': program.id,
                'name': program.name,
                'code': program.code,
            },
            'results': [
                {
                    'id': c.id,
                    'name': c.name,
                    'code': c.code,
                    'credits': c.credits,
                    'semester': c.get_semester_type_display() if c.semester_type else None,
                }
                for c in courses
            ]
        })

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """
        Get all students in this program.
        """
        from apps.students.models import Student
        
        program = self.get_object()
        students = Student.objects.filter(
            program=program, status='ACTIVE'
        ).select_related('user', 'current_level').order_by('student_id')
        
        return Response({
            'count': students.count(),
            'program': {
                'id': program.id,
                'name': program.name,
                'code': program.code,
            },
            'results': [
                {
                    'id': s.id,
                    'student_id': s.student_id,
                    'full_name': s.user.get_full_name(),
                    'level': s.current_level.get_name_display() if s.current_level else None,
                    'status': s.status,
                }
                for s in students
            ]
        })


class ClassroomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing classrooms.
    
    Provides:
    - List: GET /api/v1/classrooms/
    - Create: POST /api/v1/classrooms/
    - Retrieve: GET /api/v1/classrooms/{id}/
    - Update: PUT/PATCH /api/v1/classrooms/{id}/
    - Delete: DELETE /api/v1/classrooms/{id}/
    
    Custom Actions:
    - check_availability: POST /api/v1/classrooms/{id}/check_availability/
    - available: GET /api/v1/classrooms/available/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin and Secretary
    
    Filtering:
    - building: Filter by building
    - is_available: Filter by availability
    - has_projector: Filter by projector availability
    - has_computers: Filter by computer availability
    - capacity: Filter by minimum capacity
    
    Searching:
    - name, code, building
    
    Ordering:
    - name, code, capacity, building
    """
    
    queryset = Classroom.objects.all()
    permission_classes = [IsAuthenticated, IsSecretaryOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['building', 'is_available', 'has_projector', 'has_computers']
    search_fields = ['name', 'code', 'building']
    ordering_fields = ['name', 'code', 'capacity', 'building']
    ordering = ['building', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ClassroomListSerializer
        elif self.action == 'retrieve':
            return ClassroomDetailSerializer
        return ClassroomSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve', 'check_availability', 'available']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]

    @action(detail=True, methods=['post'])
    def check_availability(self, request, pk=None):
        """
        Check if this classroom is available for a specific time slot.
        
        Expected payload:
        {
            "time_slot_id": <time_slot_id>,
            "semester_id": <semester_id> (optional, defaults to current)
        }
        """
        from apps.scheduling.models import Schedule, TimeSlot
        
        classroom = self.get_object()
        
        time_slot_id = request.data.get('time_slot_id')
        semester_id = request.data.get('semester_id')
        
        if not time_slot_id:
            return Response(
                {'error': 'time_slot_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            time_slot = TimeSlot.objects.get(pk=time_slot_id)
        except TimeSlot.DoesNotExist:
            return Response(
                {'error': 'Créneau horaire non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build query
        conflicts = Schedule.objects.filter(
            classroom=classroom,
            time_slot=time_slot
        )
        
        if semester_id:
            conflicts = conflicts.filter(semester_id=semester_id)
        else:
            # Default to current semester
            current_semester = Semester.objects.filter(is_current=True).first()
            if current_semester:
                conflicts = conflicts.filter(semester=current_semester)
        
        is_available = not conflicts.exists()
        
        return Response({
            'is_available': is_available,
            'classroom': {
                'id': classroom.id,
                'name': classroom.name,
                'capacity': classroom.capacity,
            },
            'time_slot': {
                'id': time_slot.id,
                'day': time_slot.get_day_display(),
                'start_time': time_slot.start_time.strftime('%H:%M'),
                'end_time': time_slot.end_time.strftime('%H:%M'),
            },
            'conflicts': [
                {
                    'id': c.id,
                    'course': c.course.name if c.course else 'N/A',
                    'teacher': c.teacher.user.get_full_name() if c.teacher else 'N/A',
                }
                for c in conflicts
            ] if not is_available else []
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get all classrooms available for a specific time slot.
        
        Query parameters:
        - time_slot_id: Required
        - semester_id: Optional (defaults to current)
        - min_capacity: Optional minimum capacity filter
        """
        from apps.scheduling.models import Schedule, TimeSlot
        
        time_slot_id = request.query_params.get('time_slot_id')
        semester_id = request.query_params.get('semester_id')
        min_capacity = request.query_params.get('min_capacity')
        
        if not time_slot_id:
            return Response(
                {'error': 'time_slot_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            time_slot = TimeSlot.objects.get(pk=time_slot_id)
        except TimeSlot.DoesNotExist:
            return Response(
                {'error': 'Créneau horaire non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get occupied classrooms
        occupied_query = Schedule.objects.filter(time_slot=time_slot)
        
        if semester_id:
            occupied_query = occupied_query.filter(semester_id=semester_id)
        else:
            current_semester = Semester.objects.filter(is_current=True).first()
            if current_semester:
                occupied_query = occupied_query.filter(semester=current_semester)
        
        occupied_classroom_ids = occupied_query.values_list('classroom_id', flat=True)
        
        # Get available classrooms
        available_classrooms = Classroom.objects.filter(
            is_available=True
        ).exclude(
            id__in=occupied_classroom_ids
        )
        
        if min_capacity:
            available_classrooms = available_classrooms.filter(capacity__gte=int(min_capacity))
        
        available_classrooms = available_classrooms.order_by('building', 'name')
        
        serializer = ClassroomListSerializer(available_classrooms, many=True)
        
        return Response({
            'count': available_classrooms.count(),
            'time_slot': {
                'id': time_slot.id,
                'day': time_slot.get_day_display(),
                'start_time': time_slot.start_time.strftime('%H:%M'),
                'end_time': time_slot.end_time.strftime('%H:%M'),
            },
            'results': serializer.data
        })

