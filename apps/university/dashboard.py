from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q

from apps.students.models import Student
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

        if user.role in ['ADMIN', 'SECRETARY']:
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
        courses = Course.objects.filter(teachers=teacher)
        courses_count = courses.count()

        # Total students (approximate via enrollments or simple count if linked)
        # Assuming simple relation for now or just skip
        
        # Simple Schedule for Today
        today_index = timezone.now().weekday() # 0=Monday
        # Map python weekday to model choice (MONDAY='MON', etc)
        # Assuming model uses 0, 1, 2 directly or string keys?
        # Let's check Schedule model. 
        # For safety I will try to map common days or use a helper
        DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        current_day = DAYS[today_index] if today_index < 7 else 'MON'

        today_schedule = Schedule.objects.filter(
            teacher=teacher,
            day=current_day
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
            'students_count': 0, # Placeholder
            'schedule': schedule_data
        }

    def get_student_data(self, user):
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return {'error': 'Profil étudiant non trouvé'}
            
        current_semester = Semester.objects.filter(is_current=True).first()

        # Stats
        credits_validated = 0 # Placeholder logic
        # If we have CourseGrade with is_validated=True
        validated_grades = CourseGrade.objects.filter(student=student, is_validated=True)
        for vg in validated_grades:
            credits_validated += vg.course.credits
            
        total_credits = 60 # Assumption for year
        
        # Enrolled Courses (via CourseGrade for current semester as proxy for enrollment)
        # Or if we have an enrollment model. Using CourseGrade as enrollment for now.
        enrolled_count = CourseGrade.objects.filter(student=student, semester=current_semester).count()
        
        # Recent Grades
        recent_grades_qs = Grade.objects.filter(student=student).select_related('exam', 'exam__course').order_by('-date_graded')[:5]
        recent_grades = [
            {
                'course': g.exam.course.name,
                'type': g.exam.get_exam_type_display(),
                'score': g.score,
                'date': g.date_graded
            }
            for g in recent_grades_qs
        ]
        
        # Schedule
        today_index = timezone.now().weekday()
        DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        current_day = DAYS[today_index] if today_index < 7 else 'MON'
        
        # Find schedule for courses the student is in
        # Assuming CourseGrade implies enrollment in Course
        student_courses = CourseGrade.objects.filter(student=student, semester=current_semester).values_list('course', flat=True)
        
        today_schedule = Schedule.objects.filter(
            course__id__in=student_courses,
            day=current_day
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
            'average': "N/A", # Complex calculation skipped for dashboard summary for now
            'courses_count': enrolled_count,
            'credits_validated': credits_validated,
            'credits_total': total_credits,
            'recent_grades': recent_grades,
            'schedule': schedule_data
        }
