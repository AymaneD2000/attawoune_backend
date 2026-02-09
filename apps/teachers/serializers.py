from rest_framework import serializers
from .models import Teacher, TeacherCourse, TeacherContract


# Teacher Serializers
class TeacherListSerializer(serializers.ModelSerializer):
    """List serializer for Teacher with basic fields."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    department_name = serializers.CharField(
        source='department.name', read_only=True
    )
    rank_display = serializers.CharField(source='get_rank_display', read_only=True)
    contract_type_display = serializers.CharField(
        source='get_contract_type_display', read_only=True
    )
    
    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'employee_id', 'user_name', 'department', 'department_name',
            'rank', 'rank_display', 'contract_type', 'contract_type_display',
            'hire_date', 'is_active'
        ]


class TeacherDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Teacher with all fields and computed properties."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    department_name = serializers.CharField(
        source='department.name', read_only=True
    )
    department_code = serializers.CharField(
        source='department.code', read_only=True
    )
    faculty_name = serializers.CharField(
        source='department.faculty.name', read_only=True
    )
    rank_display = serializers.CharField(source='get_rank_display', read_only=True)
    contract_type_display = serializers.CharField(
        source='get_contract_type_display', read_only=True
    )
    courses_count = serializers.SerializerMethodField()
    active_contracts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Teacher
        fields = '__all__'
    
    def get_courses_count(self, obj):
        return obj.course_assignments.count()
    
    def get_active_contracts_count(self, obj):
        return obj.contracts.filter(status='ACTIVE').count()


class TeacherCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Teacher with validation."""
    
    class Meta:
        model = Teacher
        fields = [
            'user', 'department', 'rank', 'contract_type',
            'hire_date', 'specialization', 'office_location', 'is_active'
        ]
        read_only_fields = ['employee_id']
    
    def validate_employee_id(self, value):
        """Validate that employee_id is unique."""
        if Teacher.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError(
                "Un enseignant avec ce matricule existe déjà."
            )
        return value


# TeacherCourse Serializers
class TeacherCourseListSerializer(serializers.ModelSerializer):
    """List serializer for TeacherCourse with basic fields."""
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    teacher_employee_id = serializers.CharField(
        source='teacher.employee_id', read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    semester_display = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    
    class Meta:
        model = TeacherCourse
        fields = [
            'id', 'teacher', 'teacher_name', 'teacher_employee_id',
            'course', 'course_name', 'course_code', 'semester', 'semester_display',
            'is_primary', 'assigned_date'
        ]


class TeacherCourseDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for TeacherCourse with all fields."""
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    teacher_employee_id = serializers.CharField(
        source='teacher.employee_id', read_only=True
    )
    teacher_department = serializers.CharField(
        source='teacher.department.name', read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_credits = serializers.IntegerField(source='course.credits', read_only=True)
    semester_display = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='semester.academic_year.name', read_only=True
    )
    
    class Meta:
        model = TeacherCourse
        fields = '__all__'


class TeacherCourseCreateSerializer(serializers.ModelSerializer):
    """Create serializer for TeacherCourse with validation."""
    
    class Meta:
        model = TeacherCourse
        fields = ['teacher', 'course', 'semester', 'is_primary']
    
    def validate(self, attrs):
        """Validate teacher course assignment constraints."""
        teacher = attrs.get('teacher')
        course = attrs.get('course')
        semester = attrs.get('semester')
        
        # Validate no duplicate assignment for same teacher, course, and semester
        if teacher and course and semester:
            existing_assignment = TeacherCourse.objects.filter(
                teacher=teacher,
                course=course,
                semester=semester
            ).exists()
            
            if existing_assignment:
                raise serializers.ValidationError({
                    "teacher": "Cet enseignant est déjà affecté à ce cours pour ce semestre."
                })
        
        return attrs


# TeacherContract Serializers
class TeacherContractListSerializer(serializers.ModelSerializer):
    """List serializer for TeacherContract with basic fields."""
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    teacher_employee_id = serializers.CharField(
        source='teacher.employee_id', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    
    class Meta:
        model = TeacherContract
        fields = [
            'id', 'contract_number', 'teacher', 'teacher_name', 'teacher_employee_id',
            'start_date', 'end_date', 'base_salary', 'status', 'status_display'
        ]


class TeacherContractDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for TeacherContract with all fields."""
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    teacher_employee_id = serializers.CharField(
        source='teacher.employee_id', read_only=True
    )
    teacher_department = serializers.CharField(
        source='teacher.department.name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    
    class Meta:
        model = TeacherContract
        fields = '__all__'


class TeacherContractCreateSerializer(serializers.ModelSerializer):
    """Create serializer for TeacherContract with validation."""
    
    class Meta:
        model = TeacherContract
        fields = [
            'teacher', 'contract_number', 'start_date', 'end_date',
            'base_salary', 'status', 'document'
        ]
    
    def validate_contract_number(self, value):
        """Validate that contract_number is unique."""
        if TeacherContract.objects.filter(contract_number=value).exists():
            raise serializers.ValidationError(
                "Un contrat avec ce numéro existe déjà."
            )
        return value
    
    def validate(self, attrs):
        """Validate contract date constraints."""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        # Validate end_date is after start_date
        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError({
                "end_date": "La date de fin doit être postérieure à la date de début."
            })
        
        return attrs


# Backward compatibility serializers
class TeacherSerializer(serializers.ModelSerializer):
    """Default serializer for Teacher (backward compatibility)."""
    user_full_name = serializers.CharField(
        source='user.get_full_name', read_only=True
    )
    user_email = serializers.CharField(source='user.email', read_only=True)
    department_name = serializers.CharField(
        source='department.name', read_only=True
    )
    rank_display = serializers.CharField(source='get_rank_display', read_only=True)
    contract_type_display = serializers.CharField(
        source='get_contract_type_display', read_only=True
    )

    class Meta:
        model = Teacher
        fields = '__all__'


class TeacherCourseSerializer(serializers.ModelSerializer):
    """Default serializer for TeacherCourse (backward compatibility)."""
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )

    class Meta:
        model = TeacherCourse
        fields = '__all__'


class TeacherContractSerializer(serializers.ModelSerializer):
    """Default serializer for TeacherContract (backward compatibility)."""
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = TeacherContract
        fields = '__all__'
