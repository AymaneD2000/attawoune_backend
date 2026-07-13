from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Avg, Sum

from apps.students.models import Enrollment, Student
from apps.teachers.models import Teacher
from apps.university.models import Program, Department, Semester
from apps.finance.models import TuitionPayment
from apps.scheduling.models import Schedule
from apps.academics.models import Grade, CourseGrade, Course

class DashboardView(APIView):
    """
    Centralized Dashboard View for all user roles.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {}

        if user.role in ['ADMIN', 'SECRETARY', 'ACCOUNTANT', 'DEAN']:
            data = self.get_admin_data()
        elif user.role == 'TEACHER':
            data = self.get_teacher_data(user)
        elif user.role == 'STUDENT':
            data = self.get_student_data(user)
        
        return Response(data)

    def get_admin_data(self):
        # Counts
        students_count = Student.objects.filter(status='ACTIVE').count()
        teachers_count = Teacher.objects.filter(is_active=True).count()
        programs_count = Program.objects.filter(is_active=True).count()
        departments_count = Department.objects.count()

        # Recent Inscriptions (Last 5 students)
        recent_students = Student.objects.select_related('user', 'program', 'current_level').order_by('-created_at')[:5]
        recent_inscriptions = [
            {
                'id': s.id,
                'name': s.user.get_full_name(),
                'program': f"{s.program.name} {s.current_level.name if s.current_level else ''}",
                'date': s.created_at,
                'avatar': s.user.first_name[0] + s.user.last_name[0] if s.user.first_name and s.user.last_name else '??'
            }
            for s in recent_students
        ]

        # Recent Payments (Last 5)
        recent_payments_qs = TuitionPayment.objects.select_related('student', 'student__user').order_by('-payment_date', '-created_at')[:5]
        recent_payments = [
            {
                'id': p.id,
                'reference': p.reference,
                'student_name': p.student.user.get_full_name(),
                'amount': p.amount,
                'status': p.status,
                'date': p.payment_date,
                'avatar': '💳'
            }
            for p in recent_payments_qs
        ]

        return {
            'role': 'ADMIN',
            'students_count': students_count,
            'teachers_count': teachers_count,
            'programs_count': programs_count,
            'departments_count': departments_count,
            'recent_inscriptions': recent_inscriptions,
            'recent_payments': recent_payments
        }

    def get_teacher_data(self, user):
        try:
            teacher = user.teacher_profile
        except Teacher.DoesNotExist:
            return {'error': 'Profil enseignant non trouvé'}

        # Courses taught
        courses = Course.objects.filter(
            teacher_assignments__teacher=teacher,
            is_active=True,
        ).distinct()
        courses_count = courses.count()

        students_count = Student.objects.filter(
            status='ACTIVE',
            enrollments__is_active=True,
            enrollments__program__courses__in=courses,
        ).distinct().count()
        
        # Simple Schedule for Today
        today_index = timezone.now().weekday() # 0=Monday
        today_schedule = Schedule.objects.filter(
            teacher=teacher,
            time_slot__day=today_index,
            is_active=True,
        ).select_related('course', 'classroom', 'time_slot').order_by('time_slot__start_time')

        schedule_data = [
            {
                'id': s.id,
                'course': s.course.name,
                'location': f"{s.classroom.building} - {s.classroom.name}" if s.classroom else "N/A",
                'time': f"{s.time_slot.start_time.strftime('%H:%M')} - {s.time_slot.end_time.strftime('%H:%M')}",
                'color': 'blue' # proactive default
            }
            for s in today_schedule
        ]

        return {
            'role': 'TEACHER',
            'courses_count': courses_count,
            'students_count': students_count,
            'schedule': schedule_data
        }

    def get_student_data(self, user):
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return {'error': 'Profil étudiant non trouvé'}
            
        current_semester = Semester.objects.filter(is_current=True).first()

        current_enrollment = None
        if current_semester:
            current_enrollment = Enrollment.objects.filter(
                student=student,
                academic_year=current_semester.academic_year,
                is_active=True,
            ).select_related('program', 'level').first()

        student_courses = Course.objects.none()
        if current_semester and current_enrollment:
            student_courses = Course.objects.filter(
                program=current_enrollment.program,
                level=current_enrollment.level,
                semester_type=current_semester.semester_type,
                is_active=True,
            )

        validated_grades = CourseGrade.objects.filter(
            student=student,
            semester=current_semester,
            is_validated=True,
        ) if current_semester else CourseGrade.objects.none()
        credits_validated = validated_grades.aggregate(total=Sum('course__credits'))['total'] or 0
        total_credits = student_courses.aggregate(total=Sum('credits'))['total'] or 0
        enrolled_count = student_courses.count()
        
        # Recent Grades
        recent_grades_qs = Grade.objects.filter(student=student).select_related(
            'exam', 'exam__course'
        ).order_by('-graded_at')[:5]
        recent_grades = [
            {
                'course': g.exam.course.name,
                'type': g.exam.get_exam_type_display(),
                'score': g.score,
                'date': g.graded_at
            }
            for g in recent_grades_qs
        ]
        
        # Schedule
        today_index = timezone.now().weekday()
        
        today_schedule = Schedule.objects.filter(
            course__in=student_courses,
            semester=current_semester,
            time_slot__day=today_index,
            is_active=True,
        ).select_related('course', 'classroom', 'time_slot').order_by('time_slot__start_time')

        schedule_data = [
            {
                'id': s.id,
                'course': s.course.name,
                'location': f"{s.classroom.building} - {s.classroom.name}" if s.classroom else "N/A",
                'time': f"{s.time_slot.start_time.strftime('%H:%M')} - {s.time_slot.end_time.strftime('%H:%M')}",
                'color': 'green'
            }
            for s in today_schedule
        ]

        return {
            'role': 'STUDENT',
            'average': validated_grades.aggregate(value=Avg('final_score'))['value'],
            'courses_count': enrolled_count,
            'credits_validated': credits_validated,
            'credits_total': total_credits,
            'recent_grades': recent_grades,
            'schedule': schedule_data
        }
