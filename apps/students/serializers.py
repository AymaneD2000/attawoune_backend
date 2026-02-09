from rest_framework import serializers
from .models import Student, Enrollment, Attendance


# Student Serializers
class StudentListSerializer(serializers.ModelSerializer):
    """List serializer for Student with basic fields."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    level_display = serializers.CharField(
        source='current_level.get_name_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'user', 'student_id', 'user_name', 'program_name', 
            'level_display', 'status', 'status_display', 'enrollment_date',
            'photo'
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Student with all fields and computed properties."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    department_name = serializers.CharField(
        source='program.department.name', read_only=True
    )
    faculty_name = serializers.CharField(
        source='program.department.faculty.name', read_only=True
    )
    level_display = serializers.CharField(
        source='current_level.get_name_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    enrollments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = '__all__'
    
    def get_enrollments_count(self, obj):
        return obj.enrollments.count()


class StudentCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Student with validation."""
    
    class Meta:
        model = Student
        fields = [
            'user', 'student_id', 'program', 'current_level', 
            'enrollment_date', 'status', 'guardian_name', 
            'guardian_phone', 'emergency_contact', 'photo'
        ]
        read_only_fields = ['student_id']
    
    def validate_student_id(self, value):
        """Validate that student_id is unique."""
        if Student.objects.filter(student_id=value).exists():
            raise serializers.ValidationError(
                "Un étudiant avec ce matricule existe déjà."
            )
        return value
    
    def validate(self, attrs):
        """Validate program and level compatibility."""
        program = attrs.get('program')
        level = attrs.get('current_level')
        
        if program and level and not program.levels.filter(id=level.id).exists():
            raise serializers.ValidationError({
                "current_level": "Le niveau ne correspond pas au programme sélectionné."
            })
        
        return attrs


# Enrollment Serializers
class EnrollmentListSerializer(serializers.ModelSerializer):
    """List serializer for Enrollment with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    program_name = serializers.CharField(source='program.name', read_only=True)
    level_display = serializers.CharField(
        source='level.get_name_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_name', 'student_matricule',
            'academic_year', 'academic_year_name', 'program', 'program_name',
            'level', 'level_display', 'status', 'status_display',
            'enrollment_date', 'is_active'
        ]


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Enrollment with all fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    level_display = serializers.CharField(
        source='level.get_name_display', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = '__all__'


class EnrollmentCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Enrollment with validation."""
    
    class Meta:
        model = Enrollment
        fields = [
            'student', 'academic_year', 'program', 'level', 
            'status', 'is_active'
        ]
    
    def validate(self, attrs):
        """Validate enrollment constraints."""
        student = attrs.get('student')
        academic_year = attrs.get('academic_year')
        program = attrs.get('program')
        level = attrs.get('level')
        
        # Validate program and level compatibility
        if program and level and not program.levels.filter(id=level.id).exists():
            raise serializers.ValidationError({
                "level": "Le niveau ne correspond pas au programme sélectionné."
            })
        
        # Validate only one active enrollment per academic year
        if student and academic_year:
            existing_enrollment = Enrollment.objects.filter(
                student=student,
                academic_year=academic_year,
                is_active=True
            ).exists()
            
            if existing_enrollment:
                raise serializers.ValidationError({
                    "student": "L'étudiant a déjà une inscription active pour cette année académique."
                })
        
        return attrs


# Attendance Serializers
class AttendanceListSerializer(serializers.ModelSerializer):
    """List serializer for Attendance with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    course_name = serializers.CharField(
        source='course_session.schedule.course.name', read_only=True
    )
    session_date = serializers.DateField(
        source='course_session.date', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'student', 'student_name', 'student_matricule',
            'course_session', 'course_name', 'session_date',
            'status', 'status_display', 'recorded_at'
        ]


class AttendanceDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Attendance with all fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    course_name = serializers.CharField(
        source='course_session.schedule.course.name', read_only=True
    )
    course_code = serializers.CharField(
        source='course_session.schedule.course.code', read_only=True
    )
    session_date = serializers.DateField(
        source='course_session.date', read_only=True
    )
    teacher_name = serializers.CharField(
        source='course_session.schedule.teacher.user.get_full_name', read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recorded_by_name = serializers.CharField(
        source='recorded_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = Attendance
        fields = '__all__'


class AttendanceCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Attendance with validation."""
    
    class Meta:
        model = Attendance
        fields = [
            'student', 'course_session', 'status', 'remarks', 'recorded_by'
        ]
    
    def validate(self, attrs):
        """Validate attendance constraints."""
        student = attrs.get('student')
        course_session = attrs.get('course_session')
        
        # Check if attendance already exists
        if student and course_session:
            existing_attendance = Attendance.objects.filter(
                student=student,
                course_session=course_session
            ).exists()
            
            if existing_attendance:
                raise serializers.ValidationError({
                    "student": "La présence pour cet étudiant et cette séance existe déjà."
                })
        
        return attrs


class AttendanceBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk attendance creation."""
    course_session = serializers.IntegerField()
    attendances = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
    
    def validate_attendances(self, value):
        """Validate attendance records."""
        for attendance in value:
            if 'student' not in attendance:
                raise serializers.ValidationError(
                    "Chaque enregistrement de présence doit contenir un 'student'."
                )
            if 'status' not in attendance:
                attendance['status'] = 'PRESENT'  # Default status
        return value


# Backward compatibility serializers
class StudentSerializer(serializers.ModelSerializer):
    """Default serializer for Student (backward compatibility)."""
    user_full_name = serializers.CharField(
        source='user.get_full_name', read_only=True
    )
    user_email = serializers.CharField(source='user.email', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    level_display = serializers.CharField(
        source='current_level.get_name_display', read_only=True
    )

    class Meta:
        model = Student
        fields = '__all__'


class EnrollmentSerializer(serializers.ModelSerializer):
    """Default serializer for Enrollment (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_id = serializers.CharField(
        source='student.student_id', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    program_name = serializers.CharField(source='program.name', read_only=True)
    level_display = serializers.CharField(
        source='level.get_name_display', read_only=True
    )

    class Meta:
        model = Enrollment
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    """Default serializer for Attendance (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )

    class Meta:
        model = Attendance
        fields = '__all__'
