from rest_framework import serializers
from .models import (
    AcademicYear, Semester, Faculty, Department, Level, Program, Classroom
)


# AcademicYear Serializers
class AcademicYearListSerializer(serializers.ModelSerializer):
    """List serializer for AcademicYear with basic fields."""
    semesters_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademicYear
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current', 'semesters_count']
    
    def get_semesters_count(self, obj):
        return obj.semesters.count()


class AcademicYearDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for AcademicYear with all fields and related data."""
    semesters_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademicYear
        fields = '__all__'
    
    def get_semesters_count(self, obj):
        return obj.semesters.count()


class AcademicYearSerializer(serializers.ModelSerializer):
    """Default serializer for AcademicYear (backward compatibility)."""
    class Meta:
        model = AcademicYear
        fields = '__all__'


# Semester Serializers
class SemesterListSerializer(serializers.ModelSerializer):
    """List serializer for Semester with basic fields."""
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    semester_display = serializers.CharField(
        source='get_semester_type_display', read_only=True
    )
    
    class Meta:
        model = Semester
        fields = ['id', 'academic_year', 'academic_year_name', 'semester_type', 
                  'semester_display', 'start_date', 'end_date', 'is_current']


class SemesterDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Semester with all fields."""
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    semester_display = serializers.CharField(
        source='get_semester_type_display', read_only=True
    )
    
    class Meta:
        model = Semester
        fields = '__all__'


class SemesterSerializer(serializers.ModelSerializer):
    """Default serializer for Semester (backward compatibility)."""
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )

    class Meta:
        model = Semester
        fields = '__all__'


# Faculty Serializers
class FacultyListSerializer(serializers.ModelSerializer):
    """List serializer for Faculty with basic fields."""
    dean_name = serializers.CharField(
        source='dean.get_full_name', read_only=True
    )
    departments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Faculty
        fields = ['id', 'name', 'code', 'dean', 'dean_name', 'departments_count']
    
    def get_departments_count(self, obj):
        return obj.departments.count()


class FacultyDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Faculty with all fields and computed properties."""
    dean_name = serializers.CharField(
        source='dean.get_full_name', read_only=True
    )
    departments_count = serializers.SerializerMethodField()
    programs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Faculty
        fields = '__all__'
    
    def get_departments_count(self, obj):
        return obj.departments.count()
    
    def get_programs_count(self, obj):
        return sum(dept.programs.count() for dept in obj.departments.all())


class FacultySerializer(serializers.ModelSerializer):
    """Default serializer for Faculty (backward compatibility)."""
    dean_name = serializers.CharField(
        source='dean.get_full_name', read_only=True
    )
    departments_count = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = '__all__'

    def get_departments_count(self, obj):
        return obj.departments.count()


# Department Serializers
class DepartmentListSerializer(serializers.ModelSerializer):
    """List serializer for Department with basic fields."""
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)
    programs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'faculty', 'faculty_name', 
                  'head', 'head_name', 'programs_count']
    
    def get_programs_count(self, obj):
        return obj.programs.count()


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Department with all fields and computed properties."""
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    faculty_code = serializers.CharField(source='faculty.code', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)
    programs_count = serializers.SerializerMethodField()
    teachers_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = '__all__'
    
    def get_programs_count(self, obj):
        return obj.programs.count()
    
    def get_teachers_count(self, obj):
        return obj.teachers.count()
    
    def get_students_count(self, obj):
        return sum(program.students.filter(status='ACTIVE').count() 
                   for program in obj.programs.all())


class DepartmentSerializer(serializers.ModelSerializer):
    """Default serializer for Department (backward compatibility)."""
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)
    programs_count = serializers.SerializerMethodField()
    teachers_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = '__all__'

    def get_programs_count(self, obj):
        return obj.programs.count()

    def get_teachers_count(self, obj):
        return obj.teachers.count()


# Level Serializers
class LevelListSerializer(serializers.ModelSerializer):
    """List serializer for Level with basic fields."""
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    programs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Level
        fields = ['id', 'name', 'display_name', 'order', 'programs_count']
    
    def get_programs_count(self, obj):
        return obj.programs.count()


class LevelDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Level with all fields and computed properties."""
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    programs_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Level
        fields = '__all__'
    
    def get_programs_count(self, obj):
        return obj.programs.count()
    
    def get_students_count(self, obj):
        return sum(program.students.filter(status='ACTIVE').count() 
                   for program in obj.programs.all())


class LevelSerializer(serializers.ModelSerializer):
    """Default serializer for Level (backward compatibility)."""
    display_name = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model = Level
        fields = '__all__'


# Program Serializers
class ProgramListSerializer(serializers.ModelSerializer):
    """List serializer for Program with basic fields."""
    department_name = serializers.CharField(
        source='department.name', read_only=True
    )
    levels_display = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Program
        fields = ['id', 'name', 'code', 'department', 'department_name', 
                  'levels', 'levels_display', 'is_active', 'students_count']
    
    def get_levels_display(self, obj):
        return ", ".join([l.get_name_display() for l in obj.levels.all()])

    def get_students_count(self, obj):
        return obj.students.filter(status='ACTIVE').count()


class ProgramDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Program with all fields and computed properties."""
    department_name = serializers.CharField(
        source='department.name', read_only=True
    )
    department_code = serializers.CharField(
        source='department.code', read_only=True
    )
    faculty_name = serializers.CharField(
        source='department.faculty.name', read_only=True
    )
    faculty_code = serializers.CharField(
        source='department.faculty.code', read_only=True
    )
    levels_display = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Program
        fields = '__all__'
    
    def get_levels_display(self, obj):
        return ", ".join([l.get_name_display() for l in obj.levels.all()])

    def get_students_count(self, obj):
        return obj.students.filter(status='ACTIVE').count()
    
    def get_courses_count(self, obj):
        return obj.courses.count()


class ProgramSerializer(serializers.ModelSerializer):
    """Default serializer for Program (backward compatibility)."""
    department_name = serializers.CharField(
        source='department.name', read_only=True
    )
    faculty_name = serializers.CharField(
        source='department.faculty.name', read_only=True
    )
    levels_display = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = '__all__'

    def get_levels_display(self, obj):
        return ", ".join([l.get_name_display() for l in obj.levels.all()])

    def get_students_count(self, obj):
        return obj.students.filter(status='ACTIVE').count()


# Classroom Serializers
class ClassroomListSerializer(serializers.ModelSerializer):
    """List serializer for Classroom with basic fields."""
    
    class Meta:
        model = Classroom
        fields = ['id', 'name', 'code', 'building', 'capacity', 
                  'has_projector', 'has_computers', 'is_available']


class ClassroomDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Classroom with all fields."""
    
    class Meta:
        model = Classroom
        fields = '__all__'


class ClassroomSerializer(serializers.ModelSerializer):
    """Default serializer for Classroom (backward compatibility)."""
    class Meta:
        model = Classroom
        fields = '__all__'
