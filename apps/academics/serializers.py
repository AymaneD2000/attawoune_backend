from rest_framework import serializers
from decimal import Decimal
from .models import Course, Exam, Grade, CourseGrade, ReportCard


# Course Serializers
class CourseListSerializer(serializers.ModelSerializer):
    """List serializer for Course with basic fields."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    course_type_display = serializers.CharField(
        source='get_course_type_display', read_only=True
    )
    semester_type_display = serializers.CharField(
        source='get_semester_type_display', read_only=True
    )
    level_display = serializers.CharField(
        source='level.get_name_display', read_only=True
    )
    total_hours = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'code', 'name', 'program', 'program_name', 'program_code',
            'course_type', 'course_type_display', 'credits', 'coefficient',
            'semester_type', 'semester_type_display', 'level', 'level_display',
            'total_hours', 'is_active'
        ]


class CourseDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Course with all fields and computed properties."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    department_name = serializers.CharField(
        source='program.department.name', read_only=True
    )
    faculty_name = serializers.CharField(
        source='program.department.faculty.name', read_only=True
    )
    course_type_display = serializers.CharField(
        source='get_course_type_display', read_only=True
    )
    semester_type_display = serializers.CharField(
        source='get_semester_type_display', read_only=True
    )
    level_display = serializers.CharField(
        source='level.get_name_display', read_only=True
    )
    total_hours = serializers.IntegerField(read_only=True)
    exams_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    prerequisites_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
    
    def get_exams_count(self, obj):
        return obj.exams.count()
    
    def get_students_count(self, obj):
        return obj.program.students.filter(status='ACTIVE').count()
    
    def get_prerequisites_count(self, obj):
        return obj.prerequisites.count()


class CourseCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Course with validation."""
    
    class Meta:
        model = Course
        fields = [
            'name', 'code', 'program', 'course_type', 'credits', 'coefficient',
            'hours_lecture', 'hours_practical', 'hours_tutorial', 'description',
            'prerequisites', 'semester_type', 'level', 'is_active'
        ]
    
    def validate_code(self, value):
        """Validate that course code is unique."""
        if Course.objects.filter(code=value).exists():
            raise serializers.ValidationError(
                "Un cours avec ce code existe déjà."
            )
        return value
    
    def validate(self, attrs):
        """Validate course constraints."""
        credits = attrs.get('credits', 0)
        coefficient = attrs.get('coefficient', Decimal('1.0'))
        
        # Validate positive values
        if credits <= 0:
            raise serializers.ValidationError({
                "credits": "Le nombre de crédits doit être positif."
            })
        
        if coefficient <= 0:
            raise serializers.ValidationError({
                "coefficient": "Le coefficient doit être positif."
            })
        
        return attrs


# Exam Serializers
class ExamListSerializer(serializers.ModelSerializer):
    """List serializer for Exam with basic fields."""
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    exam_type_display = serializers.CharField(
        source='get_exam_type_display', read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name', read_only=True
    )
    
    class Meta:
        model = Exam
        fields = [
            'id', 'course', 'course_name', 'course_code', 'exam_type',
            'exam_type_display', 'semester', 'semester_name', 'date',
            'start_time', 'end_time', 'classroom', 'classroom_name',
            'max_score', 'weight'
        ]


class ExamDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Exam with all fields and computed properties."""
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    program_name = serializers.CharField(
        source='course.program.name', read_only=True
    )
    exam_type_display = serializers.CharField(
        source='get_exam_type_display', read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='semester.academic_year.name', read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name', read_only=True
    )
    classroom_capacity = serializers.IntegerField(
        source='classroom.capacity', read_only=True
    )
    grades_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = '__all__'
    
    def get_grades_count(self, obj):
        return obj.grades.count()


class ExamCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Exam with validation."""
    
    class Meta:
        model = Exam
        fields = [
            'id', 'course', 'exam_type', 'semester', 'date', 'start_time',
            'end_time', 'classroom', 'max_score', 'weight'
        ]
    
    def validate(self, attrs):
        """Validate exam constraints."""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        date = attrs.get('date')
        semester = attrs.get('semester')
        max_score = attrs.get('max_score', Decimal('20.00'))
        weight = attrs.get('weight', Decimal('1.00'))
        
        # Validate start_time is before end_time
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({
                "end_time": "L'heure de fin doit être postérieure à l'heure de début."
            })
        
        # Validate date is within semester dates
        if date and semester:
            if date < semester.start_date or date > semester.end_date:
                raise serializers.ValidationError({
                    "date": "La date de l'examen doit être dans la période du semestre."
                })
        
        # Validate positive values
        if max_score <= 0:
            raise serializers.ValidationError({
                "max_score": "La note maximale doit être positive."
            })
        
        if weight < 0 or weight > 1:
            raise serializers.ValidationError({
                "weight": "Le poids doit être entre 0 et 1."
            })
        
        return attrs


# Grade Serializers
class GradeListSerializer(serializers.ModelSerializer):
    """List serializer for Grade with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    exam_info = serializers.CharField(source='exam.__str__', read_only=True)
    course_name = serializers.CharField(source='exam.course.name', read_only=True)
    course_code = serializers.CharField(source='exam.course.code', read_only=True)
    exam_type_display = serializers.CharField(
        source='exam.get_exam_type_display', read_only=True
    )
    graded_by_name = serializers.CharField(
        source='graded_by.get_full_name', read_only=True
    )
    percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = Grade
        fields = [
            'id', 'student', 'student_name', 'student_matricule', 'exam',
            'exam_info', 'course_name', 'course_code', 'exam_type_display',
            'score', 'percentage', 'is_absent', 'graded_by', 'graded_by_name',
            'graded_at'
        ]


class GradeDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Grade with all fields and computed properties."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    student_program = serializers.CharField(
        source='student.program.name', read_only=True
    )
    exam_name = serializers.CharField(source='exam.__str__', read_only=True)
    course_name = serializers.CharField(source='exam.course.name', read_only=True)
    course_code = serializers.CharField(source='exam.course.code', read_only=True)
    exam_type_display = serializers.CharField(
        source='exam.get_exam_type_display', read_only=True
    )
    exam_date = serializers.DateField(source='exam.date', read_only=True)
    exam_max_score = serializers.DecimalField(
        source='exam.max_score', max_digits=5, decimal_places=2, read_only=True
    )
    exam_weight = serializers.DecimalField(
        source='exam.weight', max_digits=3, decimal_places=2, read_only=True
    )
    graded_by_name = serializers.CharField(
        source='graded_by.get_full_name', read_only=True
    )
    percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = Grade
        fields = '__all__'


class GradeCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Grade with validation."""
    
    class Meta:
        model = Grade
        fields = [
            'student', 'exam', 'score', 'remarks', 'is_absent', 'graded_by'
        ]
        # Remove default unique_together validator to use custom validation
        validators = []
    
    def validate(self, attrs):
        """Validate grade constraints."""
        # Resolve exam: from attrs (create/update) or instance (partial update)
        exam = attrs.get('exam')
        if not exam and self.instance:
            exam = self.instance.exam
            
        student = attrs.get('student')
        if not student and self.instance:
             student = self.instance.student
             
        score = attrs.get('score')
        if score is None and self.instance:
            score = self.instance.score
        elif score is None:
            score = Decimal('0.00')

        is_absent = attrs.get('is_absent')
        if is_absent is None and self.instance:
            is_absent = self.instance.is_absent
        elif is_absent is None:
             is_absent = False
        
        # Set score to 0 if absent (do this first before other validations)
        if is_absent:
            # If we modifying attrs, we must ensure we don't break update if score valid
            # But if validation says absent means 0, we can force it.
            # But normally logic sets score=0 in model? Or here?
            # Existing code sets attrs['score'] = 0.
            # Only if is_absent became True or was True.
            # If user sends score=15, is_absent=True -> score becomes 0.
            score = Decimal('0.00')
            attrs['score'] = score
        
        # Check for duplicate grade
        # Only check on Create. If Updating, strict unique check exists on model but we can skip custom check.
        if student and exam and not self.instance:
             if Grade.objects.filter(student=student, exam=exam).exists():
                raise serializers.ValidationError({
                    "student": "Une note existe déjà pour cet étudiant et cet examen."
                })
        
        # Validate score doesn't exceed max_score
        if exam and score > exam.max_score:
            raise serializers.ValidationError({
                "score": f"La note ne peut pas dépasser {exam.max_score}."
            })
        
        return attrs


# CourseGrade Serializers
class CourseGradeListSerializer(serializers.ModelSerializer):
    """List serializer for CourseGrade with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    validated_by_name = serializers.CharField(
        source='validated_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = CourseGrade
        fields = [
            'id', 'student', 'student_name', 'student_matricule', 'course',
            'course_name', 'course_code', 'semester', 'semester_name',
            'final_score', 'grade_letter', 'is_validated', 'validated_by',
            'validated_by_name', 'validated_at'
        ]


class CourseGradeDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for CourseGrade with all fields and computed properties."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    student_program = serializers.CharField(
        source='student.program.name', read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_credits = serializers.IntegerField(source='course.credits', read_only=True)
    course_coefficient = serializers.DecimalField(
        source='course.coefficient', max_digits=3, decimal_places=1, read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='semester.academic_year.name', read_only=True
    )
    validated_by_name = serializers.CharField(
        source='validated_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = CourseGrade
        fields = '__all__'


class CourseGradeCreateSerializer(serializers.ModelSerializer):
    """Create serializer for CourseGrade with validation."""
    
    class Meta:
        model = CourseGrade
        fields = [
            'student', 'course', 'semester', 'final_score', 'is_validated',
            'validated_by'
        ]
        # Remove default unique_together validator to use custom validation
        validators = []
    
    def validate(self, attrs):
        """Validate course grade constraints."""
        student = attrs.get('student')
        course = attrs.get('course')
        semester = attrs.get('semester')
        final_score = attrs.get('final_score', Decimal('0.00'))
        
        # Check for duplicate course grade
        if student and course and semester:
            # Only check for duplicates on create (when instance is None)
            if not self.instance:
                if CourseGrade.objects.filter(student=student, course=course, semester=semester).exists():
                    raise serializers.ValidationError({
                        "student": "Une note de cours existe déjà pour cet étudiant, ce cours et ce semestre."
                    })
        
        # Validate final_score is between 0 and 20
        if final_score < 0 or final_score > 20:
            raise serializers.ValidationError({
                "final_score": "La note finale doit être entre 0 et 20."
            })
        
        return attrs


# ReportCard Serializers
class ReportCardListSerializer(serializers.ModelSerializer):
    """List serializer for ReportCard with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    program_name = serializers.CharField(
        source='student.program.name', read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='semester.academic_year.name', read_only=True
    )
    generated_by_name = serializers.CharField(
        source='generated_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = ReportCard
        fields = [
            'id', 'student', 'student_name', 'student_matricule', 'program_name',
            'semester', 'semester_name', 'academic_year', 'gpa', 'total_credits',
            'credits_earned', 'rank', 'is_published', 'published_at',
            'generated_by', 'generated_by_name', 'generated_at'
        ]


class ReportCardDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for ReportCard with all fields and computed properties."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    student_email = serializers.CharField(
        source='student.user.email', read_only=True
    )
    student_program = serializers.CharField(
        source='student.program.name', read_only=True
    )
    program_code = serializers.CharField(
        source='student.program.code', read_only=True
    )
    student_level = serializers.CharField(
        source='student.current_level.get_name_display', read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='semester.academic_year.name', read_only=True
    )
    generated_by_name = serializers.CharField(
        source='generated_by.get_full_name', read_only=True
    )
    course_grades_count = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportCard
        fields = '__all__'
    
    def get_course_grades_count(self, obj):
        return CourseGrade.objects.filter(
            student=obj.student,
            semester=obj.semester
        ).count()

    def get_rank(self, obj):
        if obj.rank:
            return obj.rank
        
        # Calculate dynamic global rank if not stored
        all_cards = ReportCard.objects.filter(
            semester=obj.semester,
            student__program=obj.student.program
        ).order_by('-gpa')
        
        rank = 1
        for card in all_cards:
            if card.id == obj.id:
                return rank
            rank += 1
        return rank

    def get_courses(self, obj):
        course_grades = CourseGrade.objects.filter(
            student=obj.student,
            semester=obj.semester
        ).select_related('course')
        
        result = []
        for cg in course_grades:
            # Get individual exams details
            exams = Grade.objects.filter(
                student=obj.student,
                exam__course=cg.course,
                exam__semester=obj.semester
            ).select_related('exam')
            
            exam_details = [{
                'name': g.exam.get_exam_type_display(),
                'score': g.score,
                'max_score': g.exam.max_score,
                'weight': g.exam.weight
            } for g in exams]

            # Calculate class stats for this course
            all_grades = CourseGrade.objects.filter(
                course=cg.course,
                semester=obj.semester
            ).values_list('final_score', flat=True)
            
            all_scores = [float(s) for s in all_grades]
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
            max_score = max(all_scores) if all_scores else 0
            min_score = min(all_scores) if all_scores else 0
            
            # Calculate rank in course
            sorted_scores = sorted(all_scores, reverse=True)
            try:
                rank = sorted_scores.index(float(cg.final_score)) + 1
            except ValueError:
                rank = '-'

            result.append({
                'course_name': cg.course.name,
                'course_code': cg.course.code,
                'credits': cg.course.credits,
                'coefficient': cg.course.coefficient,
                'final_score': cg.final_score,
                'grade_letter': cg.grade_letter,
                'evaluations': exam_details,
                'class_avg': round(avg_score, 2),
                'class_max': max_score,
                'class_min': min_score,
                'rank': rank,
                'total_students': len(all_scores)
            })
            
        return result


# Backward compatibility serializers
class CourseSerializer(serializers.ModelSerializer):
    """Default serializer for Course (backward compatibility)."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    course_type_display = serializers.CharField(
        source='get_course_type_display', read_only=True
    )
    total_hours = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = '__all__'


class ExamSerializer(serializers.ModelSerializer):
    """Default serializer for Exam (backward compatibility)."""
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    exam_type_display = serializers.CharField(
        source='get_exam_type_display', read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name', read_only=True
    )

    class Meta:
        model = Exam
        fields = '__all__'


class GradeSerializer(serializers.ModelSerializer):
    """Default serializer for Grade (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.matricule', read_only=True
    )
    exam_name = serializers.CharField(source='exam.__str__', read_only=True)
    percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = Grade
        fields = '__all__'


class CourseGradeSerializer(serializers.ModelSerializer):
    """Default serializer for CourseGrade (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)

    class Meta:
        model = CourseGrade
        fields = '__all__'


class ReportCardSerializer(serializers.ModelSerializer):
    """Default serializer for ReportCard (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    semester_display = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )

    class Meta:
        model = ReportCard
        fields = '__all__'
