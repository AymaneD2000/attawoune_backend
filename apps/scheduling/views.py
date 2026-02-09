"""
ViewSets for scheduling app models.

This module provides ViewSets for managing scheduling-related data:
- TimeSlot: Time slot definitions for scheduling
- Schedule: Course schedules with conflict detection
- CourseSession: Individual course session instances
- Announcement: System announcements with target audience
"""

from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from apps.core.permissions import IsAdminOrReadOnly, IsSecretaryOrAdmin, IsTeacherOrAdmin
from .models import TimeSlot, Schedule, CourseSession, Announcement
from .serializers import (
    TimeSlotSerializer, ScheduleSerializer,
    CourseSessionSerializer, AnnouncementSerializer,
    ScheduleListSerializer, ScheduleDetailSerializer,
    ScheduleCreateSerializer
)


class TimeSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing time slots.
    
    Provides:
    - List: GET /api/scheduling/time-slots/
    - Create: POST /api/scheduling/time-slots/
    - Retrieve: GET /api/scheduling/time-slots/{id}/
    - Update: PUT/PATCH /api/scheduling/time-slots/{id}/
    - Delete: DELETE /api/scheduling/time-slots/{id}/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin only
    """
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['day']
    search_fields = ['day']
    ordering_fields = ['day', 'start_time']
    ordering = ['day', 'start_time']


class ScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course schedules.
    
    Provides:
    - List: GET /api/scheduling/schedules/
    - Create: POST /api/scheduling/schedules/
    - Retrieve: GET /api/scheduling/schedules/{id}/
    - Update: PUT/PATCH /api/scheduling/schedules/{id}/
    - Delete: DELETE /api/scheduling/schedules/{id}/
    
    Custom Actions:
    - by_teacher: GET /api/scheduling/schedules/by_teacher/?teacher_id=X
    - by_program: GET /api/scheduling/schedules/by_program/?program_id=X
    - check_conflicts: POST /api/scheduling/schedules/check_conflicts/
    
    Permissions:
    - Read: All authenticated users
    - Write: Admin and Secretary only
    """
    queryset = Schedule.objects.select_related(
        'course', 'course__program', 'teacher', 'teacher__user',
        'semester', 'time_slot', 'classroom'
    ).all()
    def get_serializer_class(self):
        if self.action == 'list':
            return ScheduleListSerializer
        elif self.action == 'retrieve':
            return ScheduleDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ScheduleCreateSerializer
        return ScheduleSerializer

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['course', 'teacher', 'semester', 'classroom', 'is_active']
    search_fields = ['course__name', 'course__code', 'teacher__user__first_name', 
                     'teacher__user__last_name', 'classroom__name']
    ordering_fields = ['created_at', 'time_slot__day', 'time_slot__start_time']
    ordering = ['time_slot__day', 'time_slot__start_time']

    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Admin and Secretary only
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSecretaryOrAdmin()]
        return [IsAuthenticated()]

    def _check_conflicts(self, schedule_data, exclude_pk=None):
        """
        Check for teacher and classroom conflicts.
        
        Returns a tuple: (has_conflicts, conflicts_list)
        """
        conflicts = []
        teacher = schedule_data.get('teacher')
        classroom = schedule_data.get('classroom')
        semester = schedule_data.get('semester')
        time_slot = schedule_data.get('time_slot')
        
        # Build base query
        base_query = Schedule.objects.filter(
            semester=semester,
            time_slot=time_slot,
            is_active=True
        )
        
        if exclude_pk:
            base_query = base_query.exclude(pk=exclude_pk)
        
        # Check teacher conflicts
        if teacher:
            teacher_conflicts = base_query.filter(teacher=teacher)
            for conflict in teacher_conflicts:
                conflicts.append({
                    'type': 'teacher',
                    'message': f"L'enseignant a déjà un cours à ce créneau",
                    'teacher_name': conflict.teacher.user.get_full_name(),
                    'time_slot': str(conflict.time_slot),
                    'conflicting_course': conflict.course.name,
                    'conflicting_schedule_id': conflict.id
                })
        
        # Check classroom conflicts
        if classroom:
            classroom_conflicts = base_query.filter(classroom=classroom)
            for conflict in classroom_conflicts:
                conflicts.append({
                    'type': 'classroom',
                    'message': f"La salle est déjà occupée à ce créneau",
                    'classroom_name': conflict.classroom.name,
                    'time_slot': str(conflict.time_slot),
                    'conflicting_course': conflict.course.name,
                    'conflicting_schedule_id': conflict.id
                })
        
        return len(conflicts) > 0, conflicts

    def create(self, request, *args, **kwargs):
        """Create a schedule with conflict validation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check for conflicts before saving
        has_conflicts, conflicts = self._check_conflicts(serializer.validated_data)
        if has_conflicts:
            return Response({
                'error': 'Conflits détectés',
                'conflicts': conflicts
            }, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Update a schedule with conflict validation."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Get the final data (merge existing with new for partial updates)
        check_data = {
            'teacher': serializer.validated_data.get('teacher', instance.teacher),
            'classroom': serializer.validated_data.get('classroom', instance.classroom),
            'semester': serializer.validated_data.get('semester', instance.semester),
            'time_slot': serializer.validated_data.get('time_slot', instance.time_slot),
        }
        
        # Check for conflicts before saving
        has_conflicts, conflicts = self._check_conflicts(check_data, exclude_pk=instance.pk)
        if has_conflicts:
            return Response({
                'error': 'Conflits détectés',
                'conflicts': conflicts
            }, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_teacher(self, request):
        """Get schedules for a specific teacher."""
        teacher_id = request.query_params.get('teacher_id')
        semester_id = request.query_params.get('semester_id')
        
        if not teacher_id:
            return Response(
                {'error': 'teacher_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedules = self.queryset.filter(
            teacher_id=teacher_id,
            is_active=True
        )
        if semester_id:
            schedules = schedules.filter(semester_id=semester_id)
        
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_program(self, request):
        """Get schedules for a specific program."""
        program_id = request.query_params.get('program_id')
        semester_id = request.query_params.get('semester_id')
        
        if not program_id:
            return Response(
                {'error': 'program_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedules = self.queryset.filter(
            course__program_id=program_id,
            is_active=True
        )
        if semester_id:
            schedules = schedules.filter(semester_id=semester_id)
        
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsSecretaryOrAdmin])
    def check_conflicts(self, request):
        """
        Check for all schedule conflicts in a semester.
        
        Expected payload:
        {
            "semester_id": <semester_id>
        }
        
        Returns all teacher and classroom conflicts in the semester.
        """
        semester_id = request.data.get('semester_id')
        
        if not semester_id:
            return Response(
                {'error': 'semester_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedules = Schedule.objects.filter(
            semester_id=semester_id,
            is_active=True
        ).select_related('teacher', 'teacher__user', 'classroom', 'time_slot', 'course')
        
        conflicts = []
        
        # Check teacher conflicts
        teacher_slots = {}
        for schedule in schedules:
            key = (schedule.teacher_id, schedule.time_slot_id)
            if key in teacher_slots:
                conflicts.append({
                    'type': 'teacher',
                    'teacher_id': schedule.teacher_id,
                    'teacher_name': schedule.teacher.user.get_full_name(),
                    'time_slot': str(schedule.time_slot),
                    'courses': [
                        {
                            'id': teacher_slots[key].course.id,
                            'name': teacher_slots[key].course.name,
                            'schedule_id': teacher_slots[key].id
                        },
                        {
                            'id': schedule.course.id,
                            'name': schedule.course.name,
                            'schedule_id': schedule.id
                        }
                    ]
                })
            else:
                teacher_slots[key] = schedule
        
        # Check classroom conflicts
        classroom_slots = {}
        for schedule in schedules:
            if schedule.classroom:
                key = (schedule.classroom_id, schedule.time_slot_id)
                if key in classroom_slots:
                    conflicts.append({
                        'type': 'classroom',
                        'classroom_id': schedule.classroom_id,
                        'classroom_name': schedule.classroom.name,
                        'time_slot': str(schedule.time_slot),
                        'courses': [
                            {
                                'id': classroom_slots[key].course.id,
                                'name': classroom_slots[key].course.name,
                                'schedule_id': classroom_slots[key].id
                            },
                            {
                                'id': schedule.course.id,
                                'name': schedule.course.name,
                                'schedule_id': schedule.id
                            }
                        ]
                    })
                else:
                    classroom_slots[key] = schedule
        
        return Response({
            'semester_id': semester_id,
            'conflicts_found': len(conflicts),
            'conflicts': conflicts
        })


class CourseSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course sessions.
    
    Provides:
    - List: GET /api/scheduling/course-sessions/
    - Create: POST /api/scheduling/course-sessions/
    - Retrieve: GET /api/scheduling/course-sessions/{id}/
    - Update: PUT/PATCH /api/scheduling/course-sessions/{id}/
    - Delete: DELETE /api/scheduling/course-sessions/{id}/
    
    Custom Actions:
    - cancel: POST /api/scheduling/course-sessions/{id}/cancel/
    
    Permissions:
    - Read: All authenticated users
    - Write: Teachers and Admin only
    """
    queryset = CourseSession.objects.select_related(
        'schedule', 'schedule__course', 'schedule__teacher',
        'schedule__time_slot', 'schedule__classroom'
    ).all()
    serializer_class = CourseSessionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['schedule', 'session_type', 'is_cancelled', 'date']
    search_fields = ['topic', 'schedule__course__name']
    ordering_fields = ['date']
    ordering = ['-date']

    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Read operations: All authenticated users
        - Write operations: Teachers and Admin only
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'cancel']:
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTeacherOrAdmin])
    def cancel(self, request, pk=None):
        """
        Cancel a course session.
        
        Expected payload:
        {
            "reason": "Optional cancellation reason"
        }
        """
        session = self.get_object()
        reason = request.data.get('reason', '')
        
        session.is_cancelled = True
        session.cancellation_reason = reason
        session.save()
        
        return Response({
            'message': 'Séance annulée avec succès',
            'session_id': session.id,
            'reason': reason
        })


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing announcements.
    
    Provides:
    - List: GET /api/scheduling/announcements/
    - Create: POST /api/scheduling/announcements/
    - Retrieve: GET /api/scheduling/announcements/{id}/
    - Update: PUT/PATCH /api/scheduling/announcements/{id}/
    - Delete: DELETE /api/scheduling/announcements/{id}/
    
    Custom Actions:
    - publish: POST /api/scheduling/announcements/{id}/publish/
    - active: GET /api/scheduling/announcements/active/
    
    Permissions:
    - Read: Public (only published) or Authenticated (all)
    - Write: Authenticated users
    """
    queryset = Announcement.objects.select_related(
        'faculty', 'program', 'created_by'
    ).all()
    serializer_class = AnnouncementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['announcement_type', 'target_audience', 'faculty', 'program', 
                        'is_published', 'is_pinned']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'publish_date', 'is_pinned']
    ordering = ['-is_pinned', '-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'active']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.action in ['list', 'retrieve', 'active']:
            # Only show published announcements to public
            if not self.request.user.is_authenticated:
                queryset = queryset.filter(
                    is_published=True,
                    publish_date__lte=timezone.now()
                ).filter(
                    Q(expiry_date__isnull=True) | Q(expiry_date__gte=timezone.now())
                )
        
        return queryset

    def perform_create(self, serializer):
        """Automatically set created_by to current user."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish an announcement.
        
        Sets is_published=True and records publication timestamp.
        """
        announcement = self.get_object()
        announcement.is_published = True
        announcement.publish_date = timezone.now()
        announcement.save()
        
        return Response({
            'message': 'Annonce publiée avec succès',
            'announcement_id': announcement.id,
            'publish_date': announcement.publish_date.isoformat()
        })

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all active (published and non-expired) announcements.
        
        Query parameters:
        - target_audience: Filter by target audience
        - faculty_id: Filter by faculty
        - program_id: Filter by program
        """
        now = timezone.now()
        
        queryset = Announcement.objects.filter(
            is_published=True,
            publish_date__lte=now
        ).filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
        ).select_related('faculty', 'program', 'created_by')
        
        # Apply optional filters
        target_audience = request.query_params.get('target_audience')
        if target_audience:
            queryset = queryset.filter(target_audience=target_audience)
        
        faculty_id = request.query_params.get('faculty_id')
        if faculty_id:
            queryset = queryset.filter(
                Q(faculty_id=faculty_id) | Q(faculty__isnull=True)
            )
        
        program_id = request.query_params.get('program_id')
        if program_id:
            queryset = queryset.filter(
                Q(program_id=program_id) | Q(program__isnull=True)
            )
        
        # Order by pinned first, then by date
        queryset = queryset.order_by('-is_pinned', '-publish_date')
        
        serializer = AnnouncementSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

