"""
ViewSets for students app models.

This module provides ViewSets for managing student-related data:
- Student: Student profiles with enrollment and academic information
- Enrollment: Student enrollments for academic years
- Attendance: Student attendance records for course sessions
"""

from dataclasses import asdict
import logging
from datetime import date

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from apps.core.exceptions import APIError
from apps.core.permissions import IsSecretaryOrAdmin, IsTeacherOrAdmin, IsAdminOrSecretary
from .models import Student, Enrollment, Attendance
from .serializers import (
    StudentListSerializer, StudentDetailSerializer, StudentCreateSerializer,
    EnrollmentListSerializer, EnrollmentDetailSerializer, EnrollmentCreateSerializer,
    AttendanceListSerializer, AttendanceDetailSerializer, AttendanceCreateSerializer,
    AttendanceBulkCreateSerializer,
    AcademicYearCorrectionRequestSerializer, AcademicYearCorrectionResponseSerializer
)
from .services.excel import StudentExcelService
from .services.year_correction import CorrectionBlocked, correct_student_academic_year
from django.http import HttpResponse

logger = logging.getLogger(__name__)


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
        - Academic-year correction: Admin and Secretary only (deans excluded)
        - Other write operations: Admin, Secretary and Dean
        """
        if self.action in ['list', 'retrieve', 'enrollments', 'grades', 'attendance_stats']:
            return [IsAuthenticated()]
        if self.action == 'correct_academic_year':
            return [IsAuthenticated(), IsAdminOrSecretary()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]

    def perform_update(self, serializer):
        """Save the student and discard the previous generated card version."""
        from django.core.cache import cache
        from apps.students.services.id_card import IDCardGenerator

        previous_card_key = IDCardGenerator(serializer.instance).cache_key()
        serializer.save()
        cache.delete(previous_card_key)

    def perform_create(self, serializer):
        """
        Create the student profile, then register it in the active academic
        year (enrollment + financial balance). Year data stays independent:
        creating a student only writes data for the active year.
        """
        serializer.save()
        from .services.registration import register_in_current_year
        register_in_current_year(serializer.instance)

    def get_queryset(self):
        """
        Filter queryset based on user role.

        - Admin/Secretary: See all students
        - Student: See only their own profile
        - Teacher: See students in their courses
        - Others: No access
        """
        user = self.request.user

        queryset = self.queryset

        if user.role == 'STUDENT':
            # Students can only see their own profile
            queryset = queryset.filter(user=user)
        elif user.role == 'TEACHER':
            # Teachers can see students in their courses
            queryset = queryset.filter(
                enrollments__program__courses__teacher_assignments__teacher__user=user
            ).distinct()
        elif user.role not in ['ADMIN', 'SECRETARY', 'ACCOUNTANT', 'DEAN']:
            # Others: No access
            return self.queryset.none()

        # Filter by current academic year if requested
        current_year_only = self.request.query_params.get('current_year_only', 'false').lower() == 'true'

        if current_year_only:
            queryset = queryset.filter(enrollments__academic_year__is_current=True).distinct()

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def promote(self, request, pk=None):
        """
        Promote student to next level.

        Updates the current-year enrollment with PROMOTED status and the next level.
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

        # Keep the one enrollment allowed per student and academic year in sync.
        try:
            current_year = AcademicYear.objects.get(is_current=True)
            Enrollment.objects.update_or_create(
                student=student,
                academic_year=current_year,
                defaults={
                    'program': student.program,
                    'level': next_level,
                    'status': 'PROMOTED',
                    'is_active': True,
                },
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

        Updates the current-year enrollment with REPEATED status for the same level.
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

        # Keep the one enrollment allowed per student and academic year in sync.
        Enrollment.objects.update_or_create(
            student=student,
            academic_year=current_year,
            defaults={
                'program': student.program,
                'level': student.current_level,
                'status': 'REPEATED',
                'is_active': True,
            },
        )

        return Response({
            "message": "Étudiant marqué comme redoublant",
            "level": student.current_level.get_name_display()
        })

    @extend_schema(operation_id='v1_students_student_enrollments_list')
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

    @action(detail=False, methods=['get'], url_path='reinscription-candidates')
    def reinscription_candidates(self, request):
        """
        Get students eligible for re-inscription in the active academic year.

        These are students enrolled in a previous academic year who have no
        enrollment in the active one. This is the only cross-year student
        view allowed by design (the re-inscription flow).

        Query parameters:
        - search: filter by student id or name
        - created_date: filter by the student account creation date (YYYY-MM-DD),
          i.e. the "Créé le" date shown on the users list
        """
        from django.db.models import Q
        from apps.university.models import AcademicYear

        current_year = AcademicYear.objects.filter(is_current=True).first()
        if not current_year:
            return Response(
                {'error': 'Aucune année académique active.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        candidates = (
            Student.objects.filter(
                enrollments__academic_year__start_date__lt=current_year.start_date,
                enrollments__is_active=True,
            )
            .exclude(enrollments__academic_year=current_year)
            .distinct()
            .select_related('user', 'program', 'current_level')
            .order_by('student_id')
        )

        search = request.query_params.get('search', '').strip()
        if search:
            candidates = candidates.filter(
                Q(student_id__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        created_date_value = request.query_params.get('created_date', '').strip()
        if created_date_value:
            try:
                created_date_filter = date.fromisoformat(created_date_value)
            except ValueError:
                raise APIError(message="Date d'ajout invalide.")
            # Match the account creation date ("Créé le"), i.e. the day the
            # student was added to the system — not the profile enrollment date.
            candidates = candidates.filter(user__created_at__date=created_date_filter)

        results = []
        for student in candidates[:50]:
            last_enrollment = (
                Enrollment.objects.filter(
                    student=student,
                    academic_year__start_date__lt=current_year.start_date,
                )
                .order_by('-academic_year__start_date')
                .select_related('academic_year', 'level', 'program')
                .first()
            )
            results.append({
                'id': student.id,
                'student_id': student.student_id,
                'name': student.user.get_full_name(),
                'email': student.user.email,
                'program': student.program.name,
                'last_year': last_enrollment.academic_year.name if last_enrollment else None,
                'last_level': last_enrollment.level.name if last_enrollment else None,
            })

        return Response(results)

    @action(detail=False, methods=['post'], url_path='reinscription')
    def reinscription(self, request):
        """
        Register an existing student (from a previous academic year) into the
        active academic year.

        Body:
        - student (id, required)
        - level (id, optional — defaults to the student's current level)
        - program (id, optional — defaults to the student's program)

        Creates the enrollment + the year's financial balance and syncs the
        student profile snapshot. Manual by design: no other flow transfers
        students between years.
        """
        from apps.university.models import AcademicYear, Level, Program
        from .services.registration import register_student_in_year

        current_year = AcademicYear.objects.filter(is_current=True).first()
        if not current_year:
            return Response(
                {'error': 'Aucune année académique active.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        student = Student.objects.filter(pk=request.data.get('student')).first()
        if not student:
            return Response({'error': 'Étudiant introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if Enrollment.objects.filter(student=student, academic_year=current_year, is_active=True).exists():
            return Response(
                {'error': 'Cet étudiant est déjà inscrit pour cette année académique.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        level = Level.objects.filter(pk=request.data.get('level')).first() or student.current_level
        program = Program.objects.filter(pk=request.data.get('program')).first() or student.program

        enrollment = register_student_in_year(student, current_year, level=level, program=program)

        return Response(
            {
                'message': f"Étudiant inscrit pour l'année {current_year.name}.",
                'enrollment': EnrollmentListSerializer(enrollment).data,
            },
            status=status.HTTP_201_CREATED,
        )

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
        image_bytes, cache_key = generator.generate_cached()

        response = HttpResponse(image_bytes, content_type='image/png')
        filename = f"carte_etudiant_{student.student_id}.png"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        # The server-side generator remains cached, but browsers must always
        # request the current fingerprint after a profile/photo update.
        response['Cache-Control'] = 'private, no-store, max-age=0'
        response['Pragma'] = 'no-cache'
        response['ETag'] = f'"{cache_key.rsplit(":", 1)[-1]}"'
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
            students = Student.objects.filter(id__in=student_ids).select_related(
                'user', 'program', 'current_level',
            ).prefetch_related('enrollments__academic_year')
            if not students.exists():
                return Response(
                     {"error": "Aucun étudiant trouvé pour les IDs fournis"},
                     status=status.HTTP_400_BAD_REQUEST
                )

            for student in students:
                try:
                    generator = IDCardGenerator(student)
                    image_bytes, _ = generator.generate_cached()
                    # Add to zip
                    # Ensure unique filenames in case of duplicates? student_id should be unique.
                    filename = f"carte_etudiant_{student.student_id}.png"
                    zip_file.writestr(filename, image_bytes)
                except Exception as e:
                    # Log error or skip
                    print(f"Error generating ID card for {student.id}: {e}")
                    continue

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="cartes_etudiants.zip"'
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def export_excel(self, request):
        """Export filtered students to Excel."""
        queryset = self.filter_queryset(self.get_queryset())
        excel_file = StudentExcelService.export_students(queryset)

        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="etudiants.xlsx"'
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def download_template(self, request):
        """Download import template."""
        excel_file = StudentExcelService.download_template()

        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_import_etudiants.xlsx"'
        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def import_excel(self, request):
        """Import students from Excel."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success_count, errors = StudentExcelService.import_students(file_obj)

        return Response({
            "success_count": success_count,
            "errors": errors
        }, status=status.HTTP_201_CREATED if success_count > 0 else status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=AcademicYearCorrectionRequestSerializer,
        responses={status.HTTP_200_OK: AcademicYearCorrectionResponseSerializer},
    )
    @action(detail=False, methods=['post'], url_path='correct-academic-year')
    def correct_academic_year(self, request):
        """Bulk-correct newly created students registered in the wrong academic year."""
        payload = AcademicYearCorrectionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        transferred, blocked = [], []
        for student_id in data['student_ids']:
            try:
                result = correct_student_academic_year(
                    student_id=student_id,
                    source_year=data['source_academic_year'],
                    target_year=data['target_academic_year'],
                    enrollment_date=data['enrollment_date'],
                )
                transferred.append(asdict(result))
            except CorrectionBlocked as exc:
                item = {'student': student_id}
                existing = Student.objects.filter(pk=student_id).first()
                if existing is not None:
                    item['student_id'] = existing.student_id
                item['reason'] = exc.reason
                blocked.append(item)
            except Exception:
                logger.exception('Academic-year correction failed for student %s', student_id)
                blocked.append({
                    'student': student_id,
                    'reason': "La correction a échoué; aucune donnée de cet étudiant n'a été modifiée.",
                })
        return Response({'transferred': transferred, 'blocked': blocked})

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

        if user.role in ['ADMIN', 'SECRETARY', 'DEAN']:
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

        if user.role in ['ADMIN', 'DEAN', 'SECRETARY']:
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
        self._validate_attendance_scope(
            serializer.validated_data['student'],
            serializer.validated_data['course_session'],
        )
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        self._validate_attendance_scope(
            serializer.validated_data.get('student', serializer.instance.student),
            serializer.validated_data.get('course_session', serializer.instance.course_session),
        )
        serializer.save(recorded_by=self.request.user)

    def _validate_attendance_scope(self, student, course_session):
        from rest_framework.exceptions import PermissionDenied, ValidationError

        schedule = course_session.schedule
        if (
            self.request.user.role == 'TEACHER'
            and schedule.teacher.user_id != self.request.user.id
        ):
            raise PermissionDenied("Vous n'êtes pas assigné à cette séance.")

        if not student.enrollments.filter(
            academic_year=schedule.semester.academic_year,
            program=schedule.course.program,
            is_active=True,
        ).exists():
            raise ValidationError({
                'student': "L'étudiant n'est pas activement inscrit à ce cours."
            })

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
