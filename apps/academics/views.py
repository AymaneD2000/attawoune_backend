"""
ViewSets for academics app models.

This module provides ViewSets for managing academic data:
- Course: Courses/subjects with prerequisites and credits
- Exam: Exams for courses with scheduling and scoring
- Grade: Individual exam grades for students
- CourseGrade: Final course grades for students in semesters
- ReportCard: Semester report cards with GPA and credits
"""

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.permissions import IsAdminOrReadOnly, IsTeacherOrAdmin, IsSecretaryOrAdmin
from .models import Course, Exam, Grade, CourseGrade, ReportCard
from django.db import transaction
from django.db.models import Sum, Avg, Max, Min, Q
from django.http import HttpResponse
from .utils import export_grades_template, export_current_grades
import openpyxl
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateSerializer,
    ExamListSerializer, ExamDetailSerializer, ExamCreateSerializer,
    GradeListSerializer, GradeDetailSerializer, GradeCreateSerializer,
    CourseGradeListSerializer, CourseGradeDetailSerializer, CourseGradeCreateSerializer,
    ReportCardListSerializer, ReportCardDetailSerializer
)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing courses.
    
    Provides:
    - List: GET /api/v1/courses/
    - Create: POST /api/v1/courses/
    - Retrieve: GET /api/v1/courses/{id}/
    - Update: PUT/PATCH /api/v1/courses/{id}/
    - Delete: DELETE /api/v1/courses/{id}/
    
    Custom Actions:
    - check_prerequisites: POST /api/v1/courses/{id}/check_prerequisites/
    - students: GET /api/v1/courses/{id}/students/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin and Secretary only
    
    Filtering:
    - program: Filter by program
    - semester: Filter by semester
    - course_type: Filter by course type (REQUIRED, ELECTIVE, PRACTICAL)
    - is_active: Filter by active status
    
    Searching:
    - name, code, description
    
    Ordering:
    - code, name, credits, created_at
    """
    
    queryset = Course.objects.select_related(
        'program', 'program__department', 'program__department__faculty',
        'level'
    ).prefetch_related('prerequisites', 'exams').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'semester_type', 'course_type', 'is_active', 'level']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['code', 'name', 'credits', 'created_at']
    ordering = ['program', 'code']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CourseListSerializer
        elif self.action == 'retrieve':
            return CourseDetailSerializer
        elif self.action == 'create':
            return CourseCreateSerializer
        return CourseDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Admin and Secretary only
        """
        if self.action in ['list', 'retrieve', 'check_prerequisites', 'students']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSecretaryOrAdmin()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all courses
        - Teacher: See courses they teach
        - Student: See courses in their program
        - Others: See all courses (read-only)
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see courses they teach
            return self.queryset.filter(
                teacher_assignments__teacher__user=user
            ).distinct()
        elif user.role == 'STUDENT':
            # Students can see courses in their program
            return self.queryset.filter(
                program__students__user=user
            ).distinct()
        
        # Other roles can see all courses (read-only)
        return self.queryset

    @action(detail=True, methods=['post'])
    def check_prerequisites(self, request, pk=None):
        """
        Check if a student has completed prerequisites for this course.
        
        Expected payload:
        {
            "student_id": <student_id>
        }
        
        Returns:
        - can_enroll: Boolean indicating if student can enroll
        - prerequisites: List of prerequisite courses with completion status
        """
        from apps.students.models import Student
        
        course = self.get_object()
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response(
                {'error': 'student_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Étudiant non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get prerequisites
        prerequisites = course.prerequisites.all()
        
        if not prerequisites.exists():
            return Response({
                'can_enroll': True,
                'course': {
                    'id': course.id,
                    'name': course.name,
                    'code': course.code,
                },
                'student': {
                    'id': student.id,
                    'name': student.user.get_full_name(),
                    'student_id': student.student_id,
                },
                'prerequisites': [],
                'message': "Ce cours n'a pas de prérequis."
            })
        
        # Check each prerequisite
        prerequisite_status = []
        all_completed = True
        
        for prereq in prerequisites:
            # Check if student has a passing grade (>=10/20) in the prerequisite course
            course_grade = CourseGrade.objects.filter(
                student=student,
                course=prereq,
                final_score__gte=10.0  # Passing grade in French system
            ).first()
            
            is_completed = course_grade is not None
            if not is_completed:
                all_completed = False
            
            prerequisite_status.append({
                'course_id': prereq.id,
                'course_name': prereq.name,
                'course_code': prereq.code,
                'is_completed': is_completed,
                'grade': course_grade.final_grade if course_grade else None,
            })
        
        return Response({
            'can_enroll': all_completed,
            'course': {
                'id': course.id,
                'name': course.name,
                'code': course.code,
            },
            'student': {
                'id': student.id,
                'name': student.user.get_full_name(),
                'student_id': student.student_id,
            },
            'prerequisites': prerequisite_status,
            'message': "L'étudiant peut s'inscrire à ce cours." if all_completed else "L'étudiant n'a pas validé tous les prérequis."
        })

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """
        Get all students enrolled in this course.
        """
        from apps.students.models import Enrollment
        
        from apps.university.models import Semester
        
        course = self.get_object()
        
        # Get current semester
        current_semester = Semester.objects.filter(is_current=True).first()
        
        # Get students in the program of this course who are enrolled
        enrollments = Enrollment.objects.filter(
            student__program=course.program,
            status='ACTIVE'
        ).select_related('student', 'student__user', 'student__current_level')
        
        if current_semester:
            enrollments = enrollments.filter(academic_year=current_semester.academic_year)
        
        students = [
            {
                'id': e.student.id,
                'student_id': e.student.student_id,
                'full_name': e.student.user.get_full_name(),
                'email': e.student.user.email,
                'level': e.student.current_level.get_name_display() if e.student.current_level else None,
            }
            for e in enrollments
        ]
        
        return Response({
            'count': len(students),
            'course': {
                'id': course.id,
                'name': course.name,
                'code': course.code,
            },
            'results': students
        })


class ExamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing exams.
    
    Provides:
    - List: GET /api/v1/exams/
    - Create: POST /api/v1/exams/
    - Retrieve: GET /api/v1/exams/{id}/
    - Update: PUT/PATCH /api/v1/exams/{id}/
    - Delete: DELETE /api/v1/exams/{id}/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Teachers and Admin only
    
    Filtering:
    - course: Filter by course
    - semester: Filter by semester
    - exam_type: Filter by exam type (MIDTERM, FINAL, QUIZ, PRACTICAL, PROJECT, ORAL, RESIT)
    - classroom: Filter by classroom
    - date: Filter by date
    
    Searching:
    - course name, course code
    
    Ordering:
    - date, start_time, created_at
    """
    
    queryset = Exam.objects.select_related(
        'course', 'course__program', 'semester', 'semester__academic_year', 'classroom'
    ).prefetch_related('grades').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['course', 'semester', 'exam_type', 'classroom', 'date']
    search_fields = ['course__name', 'course__code']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['date', 'start_time']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ExamListSerializer
        elif self.action == 'retrieve':
            return ExamDetailSerializer
        elif self.action == 'create':
            return ExamCreateSerializer
        return ExamDetailSerializer
    
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
        
        - Admin: See all exams
        - Teacher: See exams for their courses
        - Student: See exams for courses in their program
        - Others: See all exams (read-only)
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see exams for their courses
            return self.queryset.filter(
                course__teacher_assignments__teacher__user=user
            ).distinct()
        elif user.role == 'STUDENT':
            # Students can see exams for courses in their program
            return self.queryset.filter(
                course__program__students__user=user
            ).distinct()
        
        # Other roles can see all exams (read-only)
        return self.queryset


class GradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing grades.
    
    Provides:
    - List: GET /api/v1/grades/
    - Create: POST /api/v1/grades/
    - Retrieve: GET /api/v1/grades/{id}/
    - Update: PUT/PATCH /api/v1/grades/{id}/
    - Delete: DELETE /api/v1/grades/{id}/
    
    Custom Actions:
    - bulk_create: POST /api/v1/grades/bulk_create/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Teachers and Admin only
    
    Filtering:
    - student: Filter by student
    - exam: Filter by exam
    - is_absent: Filter by absence status
    
    Searching:
    - student name, student matricule, course name
    
    Ordering:
    - graded_at, score, created_at
    
    Teacher Validation:
    - Teachers can only create/update grades for courses they teach
    """
    
    queryset = Grade.objects.select_related(
        'student', 'student__user', 'student__program',
        'exam', 'exam__course', 'exam__semester',
        'graded_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'exam', 'is_absent', 'exam__semester']
    search_fields = [
        'student__student_id', 'student__user__first_name', 'student__user__last_name',
        'exam__course__name', 'exam__course__code'
    ]
    ordering_fields = ['graded_at', 'score', 'created_at']
    ordering = ['-graded_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return GradeListSerializer
        elif self.action == 'retrieve':
            return GradeDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return GradeCreateSerializer
        return GradeDetailSerializer
    
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
        
        - Admin: See all grades
        - Teacher: See grades for their courses
        - Student: See only their own grades
        - Others: No access
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see grades for their courses
            return self.queryset.filter(
                exam__course__teacher_assignments__teacher__user=user
            ).distinct()
        elif user.role == 'STUDENT':
            # Students can only see their own grades
            return self.queryset.filter(student__user=user)
        
        # Other roles have no access
        return self.queryset.none()
    
    def perform_create(self, serializer):
        """
        Automatically set graded_by to current user.
        Validate that teacher is assigned to the course.
        """
        # Validate teacher assignment if user is a teacher
        if self.request.user.role == 'TEACHER':
            exam = serializer.validated_data.get('exam')
            if exam:
                # Check if teacher is assigned to this course
                from apps.teachers.models import TeacherCourse
                is_assigned = TeacherCourse.objects.filter(
                    teacher__user=self.request.user,
                    course=exam.course,
                    semester=exam.semester
                ).exists()
                
                if not is_assigned:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied(
                        "Vous n'êtes pas assigné à ce cours pour ce semestre."
                    )
        
        serializer.save(graded_by=self.request.user)
    
    def perform_update(self, serializer):
        """
        Automatically update graded_by to current user.
        Validate that teacher is assigned to the course.
        """
        # Validate teacher assignment if user is a teacher
        if self.request.user.role == 'TEACHER':
            exam = serializer.validated_data.get('exam') or serializer.instance.exam
            if exam:
                # Check if teacher is assigned to this course
                from apps.teachers.models import TeacherCourse
                is_assigned = TeacherCourse.objects.filter(
                    teacher__user=self.request.user,
                    course=exam.course,
                    semester=exam.semester
                ).exists()
                
                if not is_assigned:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied(
                        "Vous n'êtes pas assigné à ce cours pour ce semestre."
                    )
        
        serializer.save(graded_by=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def bulk_create(self, request):
        """
        Create multiple grades at once.
        
        Expected payload:
        {
            "grades": [
                {"student": <student_id>, "exam": <exam_id>, "score": 15.5, "remarks": "", "is_absent": false},
                {"student": <student_id>, "exam": <exam_id>, "score": 0, "remarks": "", "is_absent": true},
                ...
            ]
        }
        """
        grades_data = request.data.get('grades', [])
        
        if not grades_data:
            return Response(
                {"error": "Le champ 'grades' est requis et ne peut pas être vide"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created = []
        errors = []
        
        for grade_data in grades_data:
            serializer = GradeCreateSerializer(data=grade_data)
            
            if serializer.is_valid():
                # Validate teacher assignment if user is a teacher
                if request.user.role == 'TEACHER':
                    exam = serializer.validated_data.get('exam')
                    if exam:
                        from apps.teachers.models import TeacherCourse
                        is_assigned = TeacherCourse.objects.filter(
                            teacher__user=request.user,
                            course=exam.course,
                            semester=exam.semester
                        ).exists()
                        
                        if not is_assigned:
                            errors.append({
                                "data": grade_data,
                                "error": "Vous n'êtes pas assigné à ce cours"
                            })
                            continue
                
                serializer.save(graded_by=request.user)
                created.append(serializer.data)
            else:
                errors.append({
                    "data": grade_data,
                    "errors": serializer.errors
                })
        
        return Response({
            'created': len(created),
            'records': created,
            'errors': errors
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def export_template(self, request):
        """Exporter un modèle Excel pour l'importation des notes."""
        exam_id = request.query_params.get('exam_id')
        if not exam_id:
            return Response({"error": "exam_id est requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            exam = Exam.objects.select_related('course', 'course__program').get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Examen non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        # Get students enrolled in the program
        from apps.students.models import Student
        students = Student.objects.filter(program=exam.course.program, status='ACTIVE').select_related('user')

        buffer = export_grades_template(exam, students)
        filename = f"Modele_Notes_{exam.course.code}_{exam.exam_type}.xlsx"
        
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def export_grades(self, request):
        """Exporter les notes d'un examen en Excel."""
        exam_id = request.query_params.get('exam_id')
        if not exam_id:
            return Response({"error": "exam_id est requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Examen non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        grades = Grade.objects.filter(exam_id=exam_id).select_related('student', 'student__user', 'graded_by')
        serializer = GradeListSerializer(grades, many=True)

        buffer = export_current_grades(exam, serializer.data)
        filename = f"Notes_{exam.course.code}_{exam.exam_type}.xlsx"
        
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def import_grades(self, request):
        """Importer des notes à partir d'un fichier Excel."""
        exam_id = request.data.get('exam_id')
        file_obj = request.FILES.get('file')

        if not exam_id or not file_obj:
            return Response({"error": "exam_id et file sont requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Examen non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        # Validate teacher access
        if request.user.role == 'TEACHER':
            from apps.teachers.models import TeacherCourse
            if not TeacherCourse.objects.filter(teacher__user=request.user, course=exam.course, semester=exam.semester).exists():
                return Response({"error": "Vous n'êtes pas assigné à ce cours"}, status=status.HTTP_403_FORBIDDEN)

        try:
            wb = openpyxl.load_workbook(file_obj, data_only=True)
            ws = wb.active
            
            from apps.students.models import Student
            from decimal import Decimal, InvalidOperation

            results = {'created': 0, 'updated': 0, 'errors': []}
            
            with transaction.atomic():
                # Skip header
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
                    matricule, name, score_val, absent_val, remarks = row[0:5]
                    
                    if not matricule:
                        continue
                        
                    try:
                        student = Student.objects.get(student_id=matricule)
                        # Basic score validation
                        is_absent = str(absent_val).strip().upper() in ['O', 'OUI', 'Y', 'YES', 'TRUE']
                        
                        score = Decimal('0.00')
                        if not is_absent and score_val is not None:
                            try:
                                score = Decimal(str(score_val))
                                if score > exam.max_score:
                                    results['errors'].append(f"Ligne {row_idx}: La note {score} dépasse le maximum {exam.max_score}")
                                    continue
                                if score < 0:
                                    results['errors'].append(f"Ligne {row_idx}: La note ne peut pas être négative")
                                    continue
                            except (InvalidOperation, ValueError):
                                results['errors'].append(f"Ligne {row_idx}: Format de note invalide: {score_val}")
                                continue
                        
                        grade, created = Grade.objects.update_or_create(
                            student=student,
                            exam=exam,
                            defaults={
                                'score': score,
                                'is_absent': is_absent,
                                'remarks': str(remarks or ""),
                                'graded_by': request.user
                            }
                        )
                        
                        if created:
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                            
                    except Student.DoesNotExist:
                        results['errors'].append(f"Ligne {row_idx}: Étudiant avec le matricule {matricule} non trouvé")
                    except Exception as e:
                        results['errors'].append(f"Ligne {row_idx}: Erreur inattendue: {str(e)}")

            return Response(results)
        except Exception as e:
            return Response({"error": f"Erreur lors de la lecture du fichier: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def student_history(self, request):
        """Historique complet des notes d'un étudiant."""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({"error": "student_id est requis"}, status=status.HTTP_400_BAD_REQUEST)

        # Check permissions
        user = request.user
        if user.role == 'STUDENT':
            # A student can only see their own history
            from apps.students.models import Student
            try:
                student = Student.objects.get(user=user)
                if str(student.id) != str(student_id):
                     return Response({"error": "Non autorisé"}, status=status.HTTP_403_FORBIDDEN)
            except Student.DoesNotExist:
                return Response({"error": "Profil étudiant non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        grades = Grade.objects.filter(student_id=student_id).select_related(
            'exam', 'exam__course', 'exam__semester', 'exam__semester__academic_year'
        ).order_by('-exam__date')

        serializer = GradeListSerializer(grades, many=True)
        
        # Calculate some stats
        stats = grades.aggregate(
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score'),
            total_exams=Sum(Q(score__isnull=False)), # This is a bit weird, aggregate doesn't work like this for count
        )
        # Fix total count
        stats['total_exams'] = grades.count()
        stats['absences'] = grades.filter(is_absent=True).count()

        return Response({
            'grades': serializer.data,
            'stats': stats
        })



class CourseGradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course grades.
    
    Provides:
    - List: GET /api/v1/course-grades/
    - Create: POST /api/v1/course-grades/
    - Retrieve: GET /api/v1/course-grades/{id}/
    - Update: PUT/PATCH /api/v1/course-grades/{id}/
    - Delete: DELETE /api/v1/course-grades/{id}/
    
    Custom Actions:
    - validate: POST /api/v1/course-grades/{id}/validate/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Teachers and Admin only
    
    Filtering:
    - student: Filter by student
    - course: Filter by course
    - semester: Filter by semester
    - is_validated: Filter by validation status
    - grade_letter: Filter by letter grade (A, B, C, D, F)
    
    Searching:
    - student name, student matricule, course name, course code
    
    Ordering:
    - final_score, created_at, validated_at
    """
    
    queryset = CourseGrade.objects.select_related(
        'student', 'student__user', 'student__program',
        'course', 'course__program',
        'semester', 'semester__academic_year',
        'validated_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'course', 'semester', 'is_validated', 'grade_letter']
    search_fields = [
        'student__student_id', 'student__user__first_name', 'student__user__last_name',
        'course__name', 'course__code'
    ]
    ordering_fields = ['final_score', 'created_at', 'validated_at']
    ordering = ['-semester', 'student', 'course']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CourseGradeListSerializer
        elif self.action == 'retrieve':
            return CourseGradeDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CourseGradeCreateSerializer
        return CourseGradeDetailSerializer
    
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
        
        - Admin: See all course grades
        - Teacher: See course grades for their courses
        - Student: See only their own course grades
        - Others: No access
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see course grades for their courses
            return self.queryset.filter(
                course__teacher_assignments__teacher__user=user
            ).distinct()
        elif user.role == 'STUDENT':
            # Students can only see their own course grades
            return self.queryset.filter(student__user=user)
        
        return self.queryset.none()
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def calculate_final_grades(self, request):
        """
        Calculate final grades for all students in a course for a semester.
        
        Formula: Weighted average of normalized scores (out of 20).
        Normalized Score = (Grade / Max Score) * 20
        Final Grade = Sum(Normalized Score * Exam Weight) / Sum(Exam Weights)
        """
        from decimal import Decimal
        from apps.students.models import Enrollment
        from apps.academics.models import Exam, Grade
        
        course_id = request.data.get('course_id')
        semester_id = request.data.get('semester_id')
        
        if not course_id or not semester_id:
            return Response(
                {"error": "course_id et semester_id sont requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate teacher permissions
        if request.user.role == 'TEACHER':
            from apps.teachers.models import TeacherCourse
            if not TeacherCourse.objects.filter(
                teacher__user=request.user,
                course_id=course_id,
                semester_id=semester_id
            ).exists():
                return Response(
                    {"error": "Vous n'êtes pas assigné à ce cours"},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Get all students enrolled in this course (via program) and active
        # Actually we should look for students who have grades OR are enrolled.
        # Let's rely on Enrollments matching the course's program.
        
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Cours non trouvé"}, status=status.HTTP_404_NOT_FOUND)
            
        # Get exams for this course and semester
        exams = Exam.objects.filter(course_id=course_id, semester_id=semester_id)
        if not exams.exists():
             return Response(
                {"error": "Aucun examen trouvé pour ce cours et ce semestre"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Map exams by ID for easy access
        exam_map = {e.id: e for e in exams}
        
        # Get students
        enrollments = Enrollment.objects.filter(
            program=course.program,
            academic_year__semesters__id=semester_id, # Link enrollment to semester's year
            status='ACTIVE'
        ).select_related('student').distinct()
        
        updated_count = 0
        created_count = 0
        
        for enrollment in enrollments:
            student = enrollment.student
            
            # Get grades for this student and these exams
            grades = Grade.objects.filter(student=student, exam__in=exams)
            
            if not grades.exists():
                continue
                
            total_weighted_user_score = Decimal('0.00')
            total_weight = Decimal('0.00')
            
            for grade in grades:
                exam = exam_map[grade.exam_id]
                
                # Normalize score to 20
                if exam.max_score > 0:
                    normalized_score = (grade.score / exam.max_score) * 20
                else:
                    normalized_score = Decimal('0.00')
                    
                total_weighted_user_score += normalized_score * exam.weight
                total_weight += exam.weight
            
            if total_weight > 0:
                final_score = total_weighted_user_score / total_weight
            else:
                final_score = Decimal('0.00')
                
            # Round to 2 decimal places
            final_score = final_score.quantize(Decimal('0.01'))
            
            # Create or update CourseGrade
            obj, created = CourseGrade.objects.update_or_create(
                student=student,
                course=course,
                semester_id=semester_id,
                defaults={
                    'final_score': final_score,
                    'is_validated': False # Reset validation on recalculation? Yes, safer.
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
                
        return Response({
            "message": "Calcul des notes effectué",
            "created": created_count,
            "updated": updated_count
        })

        """
        Validate a course grade.
        
        Sets is_validated=True, records validated_by and validated_at.
        """
        from django.utils import timezone
        
        course_grade = self.get_object()
        
        # Check if already validated
        if course_grade.is_validated:
            return Response(
                {"message": "Cette note est déjà validée"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        course_grade.is_validated = True
        course_grade.validated_by = request.user
        course_grade.validated_at = timezone.now()
        course_grade.save()
        
        serializer = CourseGradeDetailSerializer(course_grade)
        return Response({
            "message": "Note validée avec succès",
            "course_grade": serializer.data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def publish(self, request):
        """
        Publish all grades for a course in a semester.
        
        Expected payload:
        {
            "course_id": <course_id>,
            "semester_id": <semester_id>
        }
        
        Sets is_published=True and records publication timestamp for all matching grades.
        """
        from django.utils import timezone
        
        course_id = request.data.get('course_id')
        semester_id = request.data.get('semester_id')
        
        if not course_id or not semester_id:
            return Response(
                {"error": "course_id et semester_id sont requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate teacher assignment if user is a teacher
        if request.user.role == 'TEACHER':
            from apps.teachers.models import TeacherCourse
            is_assigned = TeacherCourse.objects.filter(
                teacher__user=request.user,
                course_id=course_id,
                semester_id=semester_id
            ).exists()
            
            if not is_assigned:
                return Response(
                    {"error": "Vous n'êtes pas assigné à ce cours pour ce semestre"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get all unpublished, validated course grades
        course_grades = CourseGrade.objects.filter(
            course_id=course_id,
            semester_id=semester_id,
            is_validated=True,
            is_published=False
        )
        
        if not course_grades.exists():
            return Response({
                "message": "Aucune note à publier",
                "published_count": 0
            })
        
        # Publish all grades
        now = timezone.now()
        updated_count = course_grades.update(
            is_published=True,
            published_at=now
        )
        
        return Response({
            "message": f"{updated_count} notes publiées avec succès",
            "published_count": updated_count,
            "course_id": course_id,
            "semester_id": semester_id,
            "published_at": now.isoformat()
        })


class ReportCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing report cards.
    
    Provides:
    - List: GET /api/v1/report-cards/
    - Create: POST /api/v1/report-cards/
    - Retrieve: GET /api/v1/report-cards/{id}/
    - Update: PUT/PATCH /api/v1/report-cards/{id}/
    - Delete: DELETE /api/v1/report-cards/{id}/
    
    Custom Actions:
    - calculate_gpa: POST /api/v1/report-cards/{id}/calculate_gpa/
    - publish: POST /api/v1/report-cards/{id}/publish/
    
    Permissions:
    - Read: All authenticated users (filtered by role)
    - Write: Admin only
    
    Filtering:
    - student: Filter by student
    - semester: Filter by semester
    - is_published: Filter by publication status
    
    Searching:
    - student name, student matricule, program name
    
    Ordering:
    - gpa, generated_at, published_at
    """
    
    queryset = ReportCard.objects.select_related(
        'student', 'student__user', 'student__program', 'student__current_level',
        'semester', 'semester__academic_year',
        'generated_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'semester', 'is_published']
    search_fields = [
        'student__student_id', 'student__user__first_name', 'student__user__last_name',
        'student__program__name'
    ]
    ordering_fields = ['gpa', 'generated_at', 'published_at']
    ordering = ['-semester', '-gpa']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ReportCardListSerializer
        elif self.action == 'retrieve':
            return ReportCardDetailSerializer
        return ReportCardDetailSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users (with role-based filtering)
        - Write operations: Admin only
        """
        if self.action in ['list', 'retrieve', 'calculate_gpa']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrReadOnly()]
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        - Admin/Secretary: See all report cards
        - Teacher: See report cards for students in their courses
        - Student: See only their own report cards
        - Others: No access
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'SECRETARY']:
            return self.queryset
        elif user.role == 'TEACHER':
            # Teachers can see report cards for students in their courses
            return self.queryset.filter(
                student__program__courses__teacher_assignments__teacher__user=user
            ).distinct()
        elif user.role == 'STUDENT':
            # Students can only see their own report cards
            return self.queryset.filter(student__user=user)
        
        # Other roles have no access
        return self.queryset.none()
    
    def perform_create(self, serializer):
        """Automatically set generated_by to current user."""
        serializer.save(generated_by=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def calculate_gpa(self, request, pk=None):
        """
        Calculate and update GPA for a report card.
        
        Calculates weighted average GPA from validated course grades,
        total credits, and credits earned.
        """
        report_card = self.get_object()
        report_card.calculate_gpa()
        
        serializer = ReportCardDetailSerializer(report_card)
        return Response({
            "message": "GPA calculé avec succès",
            "report_card": serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def publish(self, request, pk=None):
        """
        Publish a report card.
        
        Sets is_published=True and records publication timestamp.
        """
        from django.utils import timezone
        
        report_card = self.get_object()
        
        # Check if already published
        if report_card.is_published:
            return Response(
                {"message": "Ce bulletin est déjà publié"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report_card.is_published = True
        report_card.published_at = timezone.now()
        report_card.save()
        
        serializer = ReportCardDetailSerializer(report_card)
        return Response({
            "message": "Bulletin publié avec succès",
            "report_card": serializer.data
        })

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download Report Card as PDF.
        """
        from apps.core.services.pdf import PDFService
        from django.http import HttpResponse
        
        report_card = self.get_object()
        buffer = PDFService.generate_report_card(report_card)
        
        filename = f"Bulletin_{report_card.student.student_id}_{report_card.semester.get_semester_type_display()}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def generate_bulk(self, request):
        """
        Generate report cards for all students in a semester.
        
        Expected payload:
        {
            "semester_id": <semester_id>,
            "program_id": <program_id> (optional)
        }
        
        Creates report cards for all students with validated course grades.
        """
        from apps.students.models import Student
        from apps.university.models import Semester
        from django.db.models import Exists, OuterRef
        
        semester_id = request.data.get('semester_id')
        program_id = request.data.get('program_id')
        
        if not semester_id:
            return Response(
                {"error": "semester_id est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate semester exists
        try:
            semester = Semester.objects.get(id=semester_id)
        except Semester.DoesNotExist:
            return Response(
                {"error": "Semestre non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get students with validated course grades for this semester
        students = Student.objects.filter(
            status='ACTIVE'
        ).annotate(
            has_grades=Exists(
                CourseGrade.objects.filter(
                    student=OuterRef('pk'),
                    semester_id=semester_id,
                    is_validated=True
                )
            )
        ).filter(has_grades=True)
        
        # Apply optional program filter
        if program_id:
            students = students.filter(program_id=program_id)
        
        # Check for existing report cards
        existing_report_cards = ReportCard.objects.filter(
            semester_id=semester_id
        ).values_list('student_id', flat=True)
        
        # Filter out students who already have report cards
        students = students.exclude(id__in=existing_report_cards)
        
        created_count = 0
        errors = []
        
        for student in students:
            try:
                report_card = ReportCard.objects.create(
                    student=student,
                    semester=semester,
                    generated_by=request.user
                )
                # Calculate GPA
                report_card.calculate_gpa()
                created_count += 1
            except Exception as e:
                errors.append({
                    "student_id": student.id,
                    "error": str(e)
                })
        
        return Response({
            "message": f"{created_count} bulletins générés avec succès",
            "created_count": created_count,
            "semester_id": semester_id,
            "errors": errors
        })


class DeliberationViewSet(viewsets.ViewSet):
    """
    ViewSet pour la gestion des délibérations.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @action(detail=False, methods=['post'])
    def process(self, request):
        """
        Lancer la délibération pour un étudiant ou une liste d'étudiants.
        """
        from apps.students.models import Student
        from apps.university.models import AcademicYear
        from apps.academics.services.deliberation import DeliberationService

        academic_year_id = request.data.get('academic_year_id')
        student_id = request.data.get('student_id')
        program_id = request.data.get('program_id')

        if not academic_year_id:
            return Response({'error': 'academic_year_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            academic_year = AcademicYear.objects.get(pk=academic_year_id)
        except AcademicYear.DoesNotExist:
            return Response({'error': 'Année académique introuvable'}, status=status.HTTP_404_NOT_FOUND)

        students_to_process = []

        if student_id:
            try:
                student = Student.objects.get(pk=student_id)
                students_to_process.append(student)
            except Student.DoesNotExist:
                return Response({'error': 'Étudiant introuvable'}, status=status.HTTP_404_NOT_FOUND)
        elif program_id:
            students_to_process = Student.objects.filter(program_id=program_id, status='ACTIVE')
        else:
            return Response({'error': 'student_id ou program_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for student in students_to_process:
            try:
                promotion = DeliberationService.deliberate_student(student, academic_year)
                results.append({
                    'student': student.user.get_full_name(),
                    'matricule': student.student_id,
                    'decision': promotion.get_decision_display(),
                    'annual_gpa': promotion.annual_gpa
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                results.append({
                    'student': student.user.get_full_name(),
                    'error': str(e)
                })

        return Response({
            'processed_count': len(results),
            'results': results
        })

