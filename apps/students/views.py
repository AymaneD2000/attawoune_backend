"""
ViewSets for students app models.

This module provides ViewSets for managing student-related data:
- Student: Student profiles with enrollment and academic information
- Enrollment: Student enrollments for academic years
- Attendance: Student attendance records for course sessions
"""

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.permissions import IsSecretaryOrAdmin, IsTeacherOrAdmin
from .models import Student, Enrollment, Attendance
from .serializers import (
    StudentListSerializer, StudentDetailSerializer, StudentCreateSerializer,
    EnrollmentListSerializer, EnrollmentDetailSerializer, EnrollmentCreateSerializer,
    AttendanceListSerializer, AttendanceDetailSerializer, AttendanceCreateSerializer,
    AttendanceBulkCreateSerializer
)


class StudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing students.
    
    Provides:
    - List: GET /api/v1/students/
    - Create: POST /api/v1/students/
    - Retrieve: GET /api/v1/students/{id}/
    - Update: PUT/PATCH /api/v1/students/{id}/
    - Delete: DELETE /api/v1/students/{id}/
    
    Custom Actions:
    - promote: POST /api/v1/students/{id}/promote/
    - repeat: POST /api/v1/students/{id}/repeat/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Admin and Secretary only
    
    Filtering:
    - program: Filter by program
    - current_level: Filter by level
    - status: Filter by student status (ACTIVE, GRADUATED, SUSPENDED, DROPPED)
    
    Searching:
    - student_id, user first name, user last name, user email
    
    Ordering:
    - student_id, enrollment_date, created_at
    """
    
    queryset = Student.objects.select_related(
        'user', 'program', 'program__department', 'program__department__faculty', 'current_level'
    ).prefetch_related('enrollments').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'current_level', 'status']
    search_fields = ['student_id', 'user__first_name', 'user__last_name', 'user__email']
    ordering_fields = ['student_id', 'enrollment_date', 'created_at']
    ordering = ['student_id']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return StudentListSerializer
        elif self.action == 'retrieve':
            return StudentDetailSerializer
        elif self.action == 'create':
            return StudentCreateSerializer
        return StudentDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users (with role-based filtering)
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all students
        - Student: See only their own profile
        - Teacher: See students in their courses
        - Others: No access
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'STUDENT':
            # Students can only see their own profile
            return self.queryset.filter(user=user)
        elif user.role == 'TEACHER':
            # Teachers can see students in their courses
            # Get students enrolled in programs that have courses taught by this teacher
            return self.queryset.filter(
                enrollments__program__courses__teacher_assignments__teacher__user=user
            ).distinct()
        
        return self.queryset.none()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def promote(self, request, pk=None):
        """
        Promote student to next level.
        
        Creates a new enrollment with PROMOTED status and updates student's current level.
        """
        student = self.get_object()
        next_level_order = student.current_level.order + 1
        
        from apps.university.models import Level, AcademicYear
        
        try:
            next_level = Level.objects.get(order=next_level_order)
        except Level.DoesNotExist:
            return Response(
                {"error": "Niveau suivant non disponible"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update student level
        student.current_level = next_level
        student.save()
        
        # Create new enrollment with PROMOTED status
        try:
            current_year = AcademicYear.objects.get(is_current=True)
            Enrollment.objects.create(
                student=student,
                academic_year=current_year,
                program=student.program,
                level=next_level,
                status='PROMOTED'
            )
        except AcademicYear.DoesNotExist:
            pass  # No current academic year, just update the level
        
        return Response({
            "message": "Étudiant promu avec succès",
            "new_level": next_level.get_name_display()
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def repeat(self, request, pk=None):
        """
        Mark student as repeating current level.
        
        Creates a new enrollment with REPEATED status for the same level.
        """
        student = self.get_object()
        
        from apps.university.models import AcademicYear
        
        try:
            current_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            return Response(
                {"error": "Aucune année académique active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new enrollment with REPEATED status
        Enrollment.objects.create(
            student=student,
            academic_year=current_year,
            program=student.program,
            level=student.current_level,
            status='REPEATED'
        )
        
        return Response({
            "message": "Étudiant marqué comme redoublant",
            "level": student.current_level.get_name_display()
        })

    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        """
        Get all enrollments for a student.
        
        Returns all enrollment records for the student, ordered by academic year.
        """
        student = self.get_object()
        enrollments = Enrollment.objects.filter(student=student).select_related(
            'academic_year', 'program', 'level'
        ).order_by('-academic_year__start_date')
        
        serializer = EnrollmentListSerializer(enrollments, many=True)
        return Response({
            'count': enrollments.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        """
        Get all grades for a student.
        
        Query parameters:
        - semester_id: Filter by semester
        - course_id: Filter by course
        
        Returns all grade records for the student.
        """
        from apps.academics.models import Grade, CourseGrade
        from apps.academics.serializers import GradeListSerializer, CourseGradeListSerializer
        
        student = self.get_object()
        
        # Get exam grades
        grades = Grade.objects.filter(student=student).select_related(
            'exam', 'exam__course', 'graded_by'
        )
        
        # Get course grades
        course_grades = CourseGrade.objects.filter(student=student).select_related(
            'course', 'semester'
        )
        
        # Apply filters
        semester_id = request.query_params.get('semester_id')
        if semester_id:
            grades = grades.filter(exam__semester_id=semester_id)
            course_grades = course_grades.filter(semester_id=semester_id)
        
        course_id = request.query_params.get('course_id')
        if course_id:
            grades = grades.filter(exam__course_id=course_id)
            course_grades = course_grades.filter(course_id=course_id)
        
        grades = grades.order_by('-exam__date')
        course_grades = course_grades.order_by('-semester__academic_year__start_date')
        
        return Response({
            'exam_grades': {
                'count': grades.count(),
                'results': GradeListSerializer(grades, many=True).data
            },
            'course_grades': {
                'count': course_grades.count(),
                'results': CourseGradeListSerializer(course_grades, many=True).data
            }
        })

    @action(detail=True, methods=['get'])
    def attendance_stats(self, request, pk=None):
        """
        Get attendance statistics for a student.
        
        Query parameters:
        - semester_id: Filter by semester
        - course_id: Filter by course
        
        Returns attendance counts by status and overall attendance rate.
        """
        from django.db.models import Count, Q
        
        student = self.get_object()
        
        attendances = Attendance.objects.filter(student=student)
        
        # Apply filters
        semester_id = request.query_params.get('semester_id')
        if semester_id:
            attendances = attendances.filter(
                course_session__schedule__semester_id=semester_id
            )
        
        course_id = request.query_params.get('course_id')
        if course_id:
            attendances = attendances.filter(
                course_session__schedule__course_id=course_id
            )
        
        # Get counts by status
        stats = attendances.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            late=Count('id', filter=Q(status='LATE')),
            excused=Count('id', filter=Q(status='EXCUSED'))
        )
        
        # Calculate attendance rate
        total = stats['total']
        if total > 0:
            attended = stats['present'] + stats['late']
            attendance_rate = round((attended / total) * 100, 2)
        else:
            attendance_rate = 0.0
        
        return Response({
            'student_id': student.id,
            'student_name': student.user.get_full_name(),
            'statistics': {
                'total_sessions': stats['total'],
                'present': stats['present'],
                'absent': stats['absent'],
                'late': stats['late'],
                'excused': stats['excused'],
                'attendance_rate': attendance_rate
            }
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def generate_id_card(self, request, pk=None):
        """Generate and download Student ID Card."""
        from apps.students.services.id_card import IDCardGenerator
        from django.http import HttpResponse
        
        student = self.get_object()
        generator = IDCardGenerator(student)
        image_stream = generator.generate()
        
        response = HttpResponse(image_stream, content_type='image/png')
        filename = f"carte_etudiant_{student.student_id}.png"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def generate_bulk_id_cards(self, request):
        """Generate and download ID cards for multiple students as ZIP."""
        import zipfile
        import io
        from apps.students.services.id_card import IDCardGenerator
        from django.http import HttpResponse

        student_ids = request.data.get('student_ids', [])
        if not student_ids:
            return Response(
                {"error": "Aucun étudiant sélectionné"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
            students = Student.objects.filter(id__in=student_ids)
            if not students.exists():
                return Response(
                     {"error": "Aucun étudiant trouvé pour les IDs fournis"},
                     status=status.HTTP_400_BAD_REQUEST
                )
            
            for student in students:
                try:
                    generator = IDCardGenerator(student)
                    image_stream = generator.generate()
                    # Add to zip
                    # Ensure unique filenames in case of duplicates? student_id should be unique.
                    filename = f"carte_etudiant_{student.student_id}.png"
                    zip_file.writestr(filename, image_stream.getvalue())
                except Exception as e:
                    # Log error or skip
                    print(f"Error generating ID card for {student.id}: {e}")
                    continue

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="cartes_etudiants.zip"'
        return response

class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing enrollments.
    
    Provides:
    - List: GET /api/v1/enrollments/
    - Create: POST /api/v1/enrollments/
    - Retrieve: GET /api/v1/enrollments/{id}/
    - Update: PUT/PATCH /api/v1/enrollments/{id}/
    - Delete: DELETE /api/v1/enrollments/{id}/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Admin and Secretary only
    
    Filtering:
    - student: Filter by student
    - academic_year: Filter by academic year
    - program: Filter by program
    - level: Filter by level
    - status: Filter by enrollment status (ENROLLED, PROMOTED, REPEATED, TRANSFERRED)
    - is_active: Filter by active status
    
    Ordering:
    - enrollment_date, created_at
    """
    
    queryset = Enrollment.objects.select_related(
        'student', 'student__user', 'academic_year', 'program', 'level'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'academic_year', 'program', 'level', 'status', 'is_active']
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name']
    ordering_fields = ['enrollment_date', 'created_at']
    ordering = ['-academic_year', 'student']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return EnrollmentListSerializer
        elif self.action == 'retrieve':
            return EnrollmentDetailSerializer
        elif self.action == 'create':
            return EnrollmentCreateSerializer
        return EnrollmentDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users (with role-based filtering)
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all enrollments
        - Student: See only their own enrollments
        - Teacher: See enrollments for students in their courses
        - Others: No access
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'STUDENT':
            # Students can only see their own enrollments
            return self.queryset.filter(student__user=user)
        elif user.role == 'TEACHER':
            # Teachers can see enrollments for students in their courses
            return self.queryset.filter(
                program__courses__teacher_assignments__teacher__user=user
            ).distinct()
        
        return self.queryset.none()


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing attendance records.
    
    Provides:
    - List: GET /api/v1/attendances/
    - Create: POST /api/v1/attendances/
    - Retrieve: GET /api/v1/attendances/{id}/
    - Update: PUT/PATCH /api/v1/attendances/{id}/
    - Delete: DELETE /api/v1/attendances/{id}/
    
    Custom Actions:
    - record_bulk: POST /api/v1/attendances/record_bulk/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Teachers and Admin only
    
    Filtering:
    - student: Filter by student
    - course_session: Filter by course session
    - status: Filter by attendance status (PRESENT, ABSENT, LATE, EXCUSED)
    
    Ordering:
    - recorded_at, created_at
    """
    
    queryset = Attendance.objects.select_related(
        'student', 'student__user', 'course_session', 
        'course_session__schedule', 'course_session__schedule__course',
        'course_session__schedule__teacher', 'recorded_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'course_session', 'status']
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name']
    ordering_fields = ['recorded_at', 'created_at']
    ordering = ['-recorded_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return AttendanceListSerializer
        elif self.action == 'retrieve':
            return AttendanceDetailSerializer
        elif self.action == 'create':
            return AttendanceCreateSerializer
        elif self.action == 'record_bulk':
            return AttendanceBulkCreateSerializer
        return AttendanceDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users (with role-based filtering)
        - Write operations: Teachers and Admin only
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsTeacherOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin: See all attendance records
        - Teacher: See attendance for their courses
        - Student: See only their own attendance
        - Others: No access
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see attendance for their courses
            return self.queryset.filter(
                course_session__schedule__teacher__user=user
            )
        elif user.role == 'STUDENT':
            # Students can only see their own attendance
            return self.queryset.filter(student__user=user)
        
        return self.queryset.none()
    
    def perform_create(self, serializer):
        """Automatically set recorded_by to current user."""
        serializer.save(recorded_by=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def record_bulk(self, request):
        """
        Record attendance for multiple students in one request.
        
        Expected payload:
        {
            "course_session": <course_session_id>,
            "attendances": [
                {"student": <student_id>, "status": "PRESENT", "remarks": ""},
                {"student": <student_id>, "status": "ABSENT", "remarks": "Malade"},
                ...
            ]
        }
        """
        serializer = AttendanceBulkCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        course_session_id = serializer.validated_data['course_session']
        attendances_data = serializer.validated_data['attendances']
        
        from apps.scheduling.models import CourseSession
        
        try:
            course_session = CourseSession.objects.select_related(
                'schedule', 'schedule__teacher', 'schedule__teacher__user'
            ).get(id=course_session_id)
        except CourseSession.DoesNotExist:
            return Response(
                {"error": "Séance de cours non trouvée"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate teacher permission
        if request.user.role == 'TEACHER':
            if course_session.schedule.teacher.user != request.user:
                return Response(
                    {"error": "Vous n'êtes pas assigné à ce cours"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for attendance_data in attendances_data:
            student_id = attendance_data.get('student')
            status_value = attendance_data.get('status', 'PRESENT')
            remarks = attendance_data.get('remarks', '')
            
            try:
                student = Student.objects.get(id=student_id)
                
                # Check if student is enrolled in the course
                if not student.enrollments.filter(
                    program=course_session.schedule.course.program,
                    is_active=True
                ).exists():
                    errors.append({
                        "student_id": student_id,
                        "error": "Étudiant non inscrit à ce cours"
                    })
                    continue
                
                # Create or update attendance
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    course_session=course_session,
                    defaults={
                        'status': status_value,
                        'remarks': remarks,
                        'recorded_by': request.user
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
            except Student.DoesNotExist:
                errors.append({
                    "student_id": student_id,
                    "error": "Étudiant non trouvé"
                })
        
        return Response({
            "created": created_count,
            "updated": updated_count,
            "errors": errors
        })
