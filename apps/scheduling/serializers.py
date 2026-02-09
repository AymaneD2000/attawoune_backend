from rest_framework import serializers
from .models import TimeSlot, Schedule, CourseSession, Announcement


# TimeSlot Serializers
class TimeSlotListSerializer(serializers.ModelSerializer):
    """List serializer for TimeSlot with basic fields."""
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    
    class Meta:
        model = TimeSlot
        fields = ['id', 'day', 'day_display', 'start_time', 'end_time']


class TimeSlotDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for TimeSlot with all fields and computed properties."""
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    schedules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeSlot
        fields = '__all__'
    
    def get_schedules_count(self, obj):
        return obj.schedules.filter(is_active=True).count()


class TimeSlotCreateSerializer(serializers.ModelSerializer):
    """Create serializer for TimeSlot with validation."""
    
    class Meta:
        model = TimeSlot
        fields = ['day', 'start_time', 'end_time']
    
    def validate(self, attrs):
        """Validate time slot constraints."""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        day = attrs.get('day')
        
        # Validate start_time is before end_time
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({
                "end_time": "L'heure de fin doit être postérieure à l'heure de début."
            })
        
        # Check for duplicate time slot
        if day is not None and start_time and end_time:
            # Only check for duplicates on create (when instance is None)
            if not self.instance:
                if TimeSlot.objects.filter(
                    day=day, 
                    start_time=start_time, 
                    end_time=end_time
                ).exists():
                    raise serializers.ValidationError({
                        "day": "Un créneau horaire identique existe déjà."
                    })
        
        return attrs


# Schedule Serializers
class ScheduleListSerializer(serializers.ModelSerializer):
    """List serializer for Schedule with basic fields."""
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    time_slot_display = serializers.CharField(
        source='time_slot.__str__', read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name', read_only=True
    )
    
    time_slot = TimeSlotListSerializer(read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'course', 'course_name', 'course_code', 'teacher',
            'teacher_name', 'semester', 'semester_name', 'time_slot',
            'time_slot_display', 'classroom', 'classroom_name', 'is_active'
        ]


class ScheduleDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Schedule with all fields and computed properties."""
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    program_name = serializers.CharField(
        source='course.program.name', read_only=True
    )
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    teacher_employee_id = serializers.CharField(
        source='teacher.employee_id', read_only=True
    )
    semester_name = serializers.CharField(
        source='semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='semester.academic_year.name', read_only=True
    )
    time_slot_display = serializers.CharField(
        source='time_slot.__str__', read_only=True
    )
    day_display = serializers.CharField(
        source='time_slot.get_day_display', read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name', read_only=True
    )
    classroom_capacity = serializers.IntegerField(
        source='classroom.capacity', read_only=True
    )
    sessions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Schedule
        fields = '__all__'
    
    def get_sessions_count(self, obj):
        return obj.sessions.count()


class ScheduleCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Schedule with conflict validation."""
    
    class Meta:
        model = Schedule
        fields = [
            'course', 'teacher', 'semester', 'time_slot', 'classroom', 'is_active'
        ]
    
    def validate(self, attrs):
        """Validate schedule constraints and check for conflicts."""
        teacher = attrs.get('teacher')
        semester = attrs.get('semester')
        time_slot = attrs.get('time_slot')
        classroom = attrs.get('classroom')
        is_active = attrs.get('is_active', True)
        
        # Only check for conflicts if the schedule is active
        if is_active:
            # Check for teacher conflicts
            if teacher and semester and time_slot:
                teacher_conflicts = Schedule.objects.filter(
                    teacher=teacher,
                    semester=semester,
                    time_slot=time_slot,
                    is_active=True
                )
                
                # Exclude current instance if updating
                if self.instance:
                    teacher_conflicts = teacher_conflicts.exclude(pk=self.instance.pk)
                
                if teacher_conflicts.exists():
                    conflict = teacher_conflicts.first()
                    raise serializers.ValidationError({
                        "teacher": f"L'enseignant a déjà un cours à ce créneau: {conflict.course.name}"
                    })
            
            # Check for classroom conflicts
            if classroom and semester and time_slot:
                classroom_conflicts = Schedule.objects.filter(
                    classroom=classroom,
                    semester=semester,
                    time_slot=time_slot,
                    is_active=True
                )
                
                # Exclude current instance if updating
                if self.instance:
                    classroom_conflicts = classroom_conflicts.exclude(pk=self.instance.pk)
                
                if classroom_conflicts.exists():
                    conflict = classroom_conflicts.first()
                    raise serializers.ValidationError({
                        "classroom": f"La salle est déjà occupée à ce créneau: {conflict.course.name}"
                    })
        
        return attrs


# CourseSession Serializers
class CourseSessionListSerializer(serializers.ModelSerializer):
    """List serializer for CourseSession with basic fields."""
    course_name = serializers.CharField(
        source='schedule.course.name', read_only=True
    )
    course_code = serializers.CharField(
        source='schedule.course.code', read_only=True
    )
    teacher_name = serializers.CharField(
        source='schedule.teacher.user.get_full_name', read_only=True
    )
    time_slot_display = serializers.CharField(
        source='schedule.time_slot.__str__', read_only=True
    )
    classroom_name = serializers.CharField(
        source='schedule.classroom.name', read_only=True
    )
    session_type_display = serializers.CharField(
        source='get_session_type_display', read_only=True
    )
    
    class Meta:
        model = CourseSession
        fields = [
            'id', 'schedule', 'course_name', 'course_code', 'teacher_name',
            'time_slot_display', 'classroom_name', 'date', 'session_type',
            'session_type_display', 'topic', 'is_cancelled'
        ]


class CourseSessionDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for CourseSession with all fields and computed properties."""
    course_name = serializers.CharField(
        source='schedule.course.name', read_only=True
    )
    course_code = serializers.CharField(
        source='schedule.course.code', read_only=True
    )
    program_name = serializers.CharField(
        source='schedule.course.program.name', read_only=True
    )
    teacher_name = serializers.CharField(
        source='schedule.teacher.user.get_full_name', read_only=True
    )
    teacher_employee_id = serializers.CharField(
        source='schedule.teacher.employee_id', read_only=True
    )
    semester_name = serializers.CharField(
        source='schedule.semester.get_semester_type_display', read_only=True
    )
    academic_year = serializers.CharField(
        source='schedule.semester.academic_year.name', read_only=True
    )
    time_slot_display = serializers.CharField(
        source='schedule.time_slot.__str__', read_only=True
    )
    classroom_name = serializers.CharField(
        source='schedule.classroom.name', read_only=True
    )
    session_type_display = serializers.CharField(
        source='get_session_type_display', read_only=True
    )
    attendance_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseSession
        fields = '__all__'
    
    def get_attendance_count(self, obj):
        return obj.attendances.count()


class CourseSessionCreateSerializer(serializers.ModelSerializer):
    """Create serializer for CourseSession with validation."""
    
    class Meta:
        model = CourseSession
        fields = [
            'schedule', 'date', 'session_type', 'topic', 'notes',
            'is_cancelled', 'cancellation_reason'
        ]
    
    def validate(self, attrs):
        """Validate course session constraints."""
        schedule = attrs.get('schedule')
        date = attrs.get('date')
        is_cancelled = attrs.get('is_cancelled', False)
        cancellation_reason = attrs.get('cancellation_reason', '')
        
        # Check for duplicate session
        if schedule and date:
            # Only check for duplicates on create (when instance is None)
            if not self.instance:
                if CourseSession.objects.filter(schedule=schedule, date=date).exists():
                    raise serializers.ValidationError({
                        "date": "Une séance existe déjà pour cet emploi du temps à cette date."
                    })
        
        # Validate date is within semester dates
        if schedule and date:
            semester = schedule.semester
            if date < semester.start_date or date > semester.end_date:
                raise serializers.ValidationError({
                    "date": "La date de la séance doit être dans la période du semestre."
                })
        
        # Validate cancellation reason if cancelled
        if is_cancelled and not cancellation_reason:
            raise serializers.ValidationError({
                "cancellation_reason": "Une raison d'annulation est requise pour une séance annulée."
            })
        
        return attrs


# Announcement Serializers
class AnnouncementListSerializer(serializers.ModelSerializer):
    """List serializer for Announcement with basic fields."""
    announcement_type_display = serializers.CharField(
        source='get_announcement_type_display', read_only=True
    )
    target_audience_display = serializers.CharField(
        source='get_target_audience_display', read_only=True
    )
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'announcement_type', 'announcement_type_display',
            'target_audience', 'target_audience_display', 'faculty',
            'faculty_name', 'program', 'program_name', 'is_published',
            'publish_date', 'expiry_date', 'is_pinned', 'created_by',
            'created_by_name', 'created_at'
        ]


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Announcement with all fields."""
    announcement_type_display = serializers.CharField(
        source='get_announcement_type_display', read_only=True
    )
    target_audience_display = serializers.CharField(
        source='get_target_audience_display', read_only=True
    )
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    faculty_code = serializers.CharField(source='faculty.code', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    department_name = serializers.CharField(
        source='program.department.name', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    created_by_email = serializers.CharField(
        source='created_by.email', read_only=True
    )
    
    class Meta:
        model = Announcement
        fields = '__all__'


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Announcement with validation."""
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'announcement_type', 'target_audience',
            'faculty', 'program', 'is_published', 'publish_date',
            'expiry_date', 'is_pinned', 'created_by'
        ]
    
    def validate_target_audience(self, value):
        """Validate target audience is a valid choice."""
        valid_choices = [choice[0] for choice in Announcement.TargetAudience.choices]
        if value not in valid_choices:
            raise serializers.ValidationError(
                f"Le public cible doit être l'un des suivants: {', '.join(valid_choices)}"
            )
        return value
    
    def validate(self, attrs):
        """Validate announcement constraints."""
        publish_date = attrs.get('publish_date')
        expiry_date = attrs.get('expiry_date')
        
        # Validate expiry_date is after publish_date
        if publish_date and expiry_date and expiry_date <= publish_date:
            raise serializers.ValidationError({
                "expiry_date": "La date d'expiration doit être postérieure à la date de publication."
            })
        
        return attrs


# Backward compatibility serializers
class TimeSlotSerializer(serializers.ModelSerializer):
    """Default serializer for TimeSlot (backward compatibility)."""
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    
    class Meta:
        model = TimeSlot
        fields = '__all__'


class ScheduleSerializer(serializers.ModelSerializer):
    """Default serializer for Schedule (backward compatibility)."""
    course_name = serializers.CharField(source='course.name', read_only=True)
    teacher_name = serializers.CharField(
        source='teacher.user.get_full_name', read_only=True
    )
    time_slot_display = serializers.CharField(
        source='time_slot.__str__', read_only=True
    )
    classroom_name = serializers.CharField(
        source='classroom.name', read_only=True
    )
    
    class Meta:
        model = Schedule
        fields = '__all__'


class CourseSessionSerializer(serializers.ModelSerializer):
    """Default serializer for CourseSession (backward compatibility)."""
    course_name = serializers.CharField(
        source='schedule.course.name', read_only=True
    )
    session_type_display = serializers.CharField(
        source='get_session_type_display', read_only=True
    )
    
    class Meta:
        model = CourseSession
        fields = '__all__'


class AnnouncementSerializer(serializers.ModelSerializer):
    """Default serializer for Announcement (backward compatibility)."""
    announcement_type_display = serializers.CharField(
        source='get_announcement_type_display', read_only=True
    )
    target_audience_display = serializers.CharField(
        source='get_target_audience_display', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = Announcement
        fields = '__all__'
