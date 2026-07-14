"""
ViewSets for finance app models.

This module provides ViewSets for managing financial operations:
- TuitionPayment: Student tuition payments
- TuitionFee: Fee configuration per program and academic year
- StudentBalance: Financial balance per student per academic year
- Salary: Employee salary records
- Expense: University expenses
"""

from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count, Sum, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import date
import uuid

from apps.core.permissions import IsAccountantOrAdmin, IsFinanceViewer
from .models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense
from .serializers import (
    TuitionPaymentListSerializer, TuitionPaymentDetailSerializer, TuitionPaymentCreateSerializer,
    TuitionFeeListSerializer, TuitionFeeDetailSerializer, TuitionFeeCreateSerializer,
    StudentBalanceListSerializer, StudentBalanceDetailSerializer,
    SalaryListSerializer, SalaryDetailSerializer, SalaryCreateSerializer,
    ExpenseListSerializer, ExpenseDetailSerializer, ExpenseCreateSerializer,
    # Backward compatibility
    TuitionPaymentSerializer, TuitionFeeSerializer,
    StudentBalanceSerializer, SalarySerializer, ExpenseSerializer
)
from apps.university.models import AcademicYear
from .services.excel import PaymentExcelService, SalaryExcelService, ExpenseExcelService
from .services.balances import reconcile_balance_pairs, reconcile_student_balance
from django.http import HttpResponse


class TuitionPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tuition payments.
    
    Provides:
    - List: GET /api/v1/tuition-payments/
    - Create: POST /api/v1/tuition-payments/
    - Retrieve: GET /api/v1/tuition-payments/{id}/
    - Update: PUT/PATCH /api/v1/tuition-payments/{id}/
    - Delete: DELETE /api/v1/tuition-payments/{id}/
    
    Custom Actions:
    - by_student: GET /api/v1/tuition-payments/by_student/?student_id=X
    
    Permissions:
    - All operations: Accountant and Admin only
    
    Filtering:
    - student: Filter by student
    - academic_year: Filter by academic year
    - payment_method: Filter by payment method (CASH, BANK_TRANSFER, MOBILE_MONEY, CHECK)
    - status: Filter by status (PENDING, COMPLETED, FAILED, REFUNDED)
    
    Searching:
    - reference, receipt_number, student name
    
    Ordering:
    - payment_date, amount, created_at
    """
    
    queryset = TuitionPayment.objects.select_related(
        'student', 'student__user', 'student__program',
        'academic_year', 'received_by'
    ).all()

    def get_queryset(self):
        """Filter by current academic year by default."""
        queryset = super().get_queryset()
        
        # Filter by current academic year if requested (default True)
        current_year_only = self.request.query_params.get('current_year_only', 'true').lower() == 'true'
        
        if current_year_only and 'academic_year' not in self.request.query_params:
            from apps.university.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                queryset = queryset.filter(academic_year=current_year)
        
        return queryset

    permission_classes = [IsAuthenticated, IsFinanceViewer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'academic_year', 'payment_method', 'status']
    search_fields = ['reference', 'receipt_number', 'student__user__first_name', 'student__user__last_name', 'student__student_id']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TuitionPaymentListSerializer
        elif self.action == 'retrieve':
            return TuitionPaymentDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TuitionPaymentCreateSerializer
        return TuitionPaymentSerializer
    
    def _generate_reference(self):
        """Generate unique payment reference."""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"PAY-{timestamp}-{unique_id}"
    
    @transaction.atomic
    def perform_create(self, serializer):
        """
        Set received_by to current user on creation.
        Automatically generate reference number.
        Validate that amount is positive.
        Sets default academic_year if not provided.
        """
        # Validate positive amount
        amount = serializer.validated_data.get('amount', 0)
        if amount <= 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"amount": "Le montant doit être positif."})
        
        # Generate reference if not provided
        reference = serializer.validated_data.get('reference')
        if not reference:
            reference = self._generate_reference()
            
        # Default payment_date to today if not provided
        payment_date = serializer.validated_data.get('payment_date')
        if not payment_date:
            payment_date = timezone.now().date()

        # Handle academic_year default
        academic_year = serializer.validated_data.get('academic_year')
        if not academic_year:
            academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not academic_year:
                 # Fallback to latest? Or error?
                 # Better to error if no current year exists, but let's try latest
                 academic_year = AcademicYear.objects.order_by('-start_date').first()
            
            if not academic_year:
                 from rest_framework.exceptions import ValidationError
                 raise ValidationError({"academic_year": "Aucune année académique active trouvée."})

        payment = serializer.save(
            received_by=self.request.user,
            reference=reference,
            academic_year=academic_year,
            payment_date=payment_date,
            status='COMPLETED'  # Auto-complete manual payments
        )

        reconcile_student_balance(payment.student, payment.academic_year)

    @transaction.atomic
    def perform_update(self, serializer):
        previous = TuitionPayment.objects.select_for_update().get(pk=serializer.instance.pk)
        old_pair = (previous.student, previous.academic_year)
        payment = serializer.save()
        reconcile_balance_pairs(old_pair, (payment.student, payment.academic_year))

    @transaction.atomic
    def perform_destroy(self, instance):
        payment = TuitionPayment.objects.select_for_update().get(pk=instance.pk)
        pair = (payment.student, payment.academic_year)
        payment.delete()
        reconcile_student_balance(*pair)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):
        """Approve a pending payment."""
        payment = self.get_object()
        if payment.status != 'PENDING':
            return Response(
                {"error": "Le paiement n'est pas en attente"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'COMPLETED'
        if not payment.payment_date:
            payment.payment_date = timezone.now().date()
        payment.save()
        
        reconcile_student_balance(payment.student, payment.academic_year)
        return Response({"status": "approved", "message": "Paiement validé avec succès"})
    
    @action(detail=False, methods=['get'])
    def by_student(self, request):
        """
        Get all payments for a specific student.
        
        Query parameters:
        - student_id: Student ID (required)
        - academic_year_id: Filter by academic year (optional)
        """
        student_id = request.query_params.get('student_id')
        
        if not student_id:
            return Response(
                {"error": "student_id est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payments = self.queryset.filter(student_id=student_id)
        
        academic_year_id = request.query_params.get('academic_year_id')
        if academic_year_id:
            payments = payments.filter(academic_year_id=academic_year_id)
        
        payments = payments.order_by('-payment_date')
        
        serializer = TuitionPaymentListSerializer(payments, many=True)
        total_paid = payments.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return Response({
            'count': payments.count(),
            'total_paid': total_paid,
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export filtered payments to Excel."""
        queryset = self.filter_queryset(self.get_queryset())
        excel_file = PaymentExcelService.export_payments(queryset)

        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="paiements.xlsx"'
        return response

    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download import template for payments."""
        excel_file = PaymentExcelService.download_template()

        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_import_paiements.xlsx"'
        return response

    @action(detail=False, methods=['post'])
    def import_excel(self, request):
        """Import payments from Excel."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success_count, errors = PaymentExcelService.import_payments(file_obj, request.user)

        return Response({
            "success_count": success_count,
            "errors": errors
        }, status=status.HTTP_201_CREATED if success_count > 0 else status.HTTP_400_BAD_REQUEST)


class TuitionFeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tuition fees.
    
    Provides:
    - List: GET /api/v1/tuition-fees/
    - Create: POST /api/v1/tuition-fees/
    - Retrieve: GET /api/v1/tuition-fees/{id}/
    - Update: PUT/PATCH /api/v1/tuition-fees/{id}/
    - Delete: DELETE /api/v1/tuition-fees/{id}/
    
    Permissions:
    - All operations: Accountant and Admin only
    
    Filtering:
    - program: Filter by program
    - academic_year: Filter by academic year
    
    Searching:
    - program name, program code
    
    Ordering:
    - amount, due_date, created_at
    """
    
    queryset = TuitionFee.objects.select_related(
        'program', 'program__department', 'program__department__faculty',
        'academic_year'
    ).all()

    def get_queryset(self):
        """Filter by current academic year by default."""
        queryset = super().get_queryset()
        
        # Filter by current academic year if requested (default True)
        current_year_only = self.request.query_params.get('current_year_only', 'true').lower() == 'true'

        if current_year_only and 'academic_year' not in self.request.query_params:
            from apps.university.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                queryset = queryset.filter(academic_year=current_year)
        return queryset

    permission_classes = [IsAuthenticated, IsFinanceViewer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['program', 'academic_year']
    search_fields = ['program__name', 'program__code']
    ordering_fields = ['amount', 'due_date']
    ordering = ['academic_year', 'program']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TuitionFeeListSerializer
        elif self.action == 'retrieve':
            return TuitionFeeDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TuitionFeeCreateSerializer
        return TuitionFeeSerializer


class StudentBalanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student balances.
    
    Provides:
    - List: GET /api/v1/student-balances/
    - Create: POST /api/v1/student-balances/
    - Retrieve: GET /api/v1/student-balances/{id}/
    - Update: PUT/PATCH /api/v1/student-balances/{id}/
    - Delete: DELETE /api/v1/student-balances/{id}/
    
    Custom Actions:
    - outstanding: GET /api/v1/student-balances/outstanding/
    - recalculate: POST /api/v1/student-balances/{id}/recalculate/
    
    Permissions:
    - All operations: Accountant and Admin only
    
    Filtering:
    - student: Filter by student
    - academic_year: Filter by academic year
    
    Searching:
    - student name, student ID
    
    Ordering:
    - total_due, total_paid, updated_at
    """
    
    queryset = StudentBalance.objects.select_related(
        'student', 'student__user', 'student__program',
        'academic_year'
    ).all()

    def get_queryset(self):
        """Filter by current academic year by default."""
        queryset = super().get_queryset()
        
        # Filter by current academic year if requested (default True)
        current_year_only = self.request.query_params.get('current_year_only', 'true').lower() == 'true'

        if current_year_only and 'academic_year' not in self.request.query_params:
            from apps.university.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                queryset = queryset.filter(academic_year=current_year)
        return queryset

    permission_classes = [IsAuthenticated, IsFinanceViewer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'academic_year']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'student__student_id']
    ordering_fields = ['total_due', 'total_paid', 'updated_at']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['list', 'outstanding']:
            return StudentBalanceListSerializer
        elif self.action == 'retrieve':
            return StudentBalanceDetailSerializer
        return StudentBalanceSerializer

    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        """
        Get all students with outstanding (unpaid) balances.
        
        Query parameters:
        - academic_year_id: Filter by academic year (optional)
        - min_balance: Minimum outstanding balance to include (optional)
        
        Returns students where total_paid < total_due.
        """
        # Annotate with computed balance field for filtering/ordering
        queryset = self.get_queryset().annotate(
            computed_balance=F('total_due') - F('total_paid')
        ).filter(computed_balance__gt=0)
        
        academic_year_id = request.query_params.get('academic_year_id')
        if academic_year_id:
            queryset = queryset.filter(academic_year_id=academic_year_id)
        
        min_balance = request.query_params.get('min_balance')
        if min_balance:
            try:
                queryset = queryset.filter(computed_balance__gte=float(min_balance))
            except ValueError:
                pass
        
        queryset = queryset.order_by('-computed_balance')
        
        total_outstanding = queryset.aggregate(total=Sum('computed_balance'))['total'] or 0
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = StudentBalanceListSerializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            # Add custom field to paginated response
            response.data['total_outstanding'] = total_outstanding
            return response

        serializer = StudentBalanceListSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'total_outstanding': total_outstanding,
            'results': serializer.data
        })

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate student balance based on payments.
        
        Updates total_paid from all completed payments.
        """
        balance = self.get_object()
        
        balance = reconcile_student_balance(balance.student, balance.academic_year)
        serializer = StudentBalanceDetailSerializer(balance)
        
        return Response({
            "message": "Solde recalculé avec succès",
            "balance": serializer.data
        })

    @action(detail=False, methods=['get'])
    def statement(self, request):
        """
        Get financial statement for a student.
        
        Query parameters:
        - student_id: Student ID (required)
        - academic_year_id: Academic Year ID (optional)
        """
        student_id = request.query_params.get('student_id')
        academic_year_id = request.query_params.get('academic_year_id')
        
        if not student_id:
            return Response({'error': 'student_id est requis'}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.students.models import Student
        from apps.finance.services.reporting import FinancialReportService
        from apps.university.models import AcademicYear
        
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Étudiant introuvable'}, status=status.HTTP_404_NOT_FOUND)
            
        academic_year = None
        if academic_year_id:
            try:
                academic_year = AcademicYear.objects.get(pk=academic_year_id)
            except AcademicYear.DoesNotExist:
                return Response({'error': 'Année académique introuvable'}, status=status.HTTP_404_NOT_FOUND)
                
        statement = FinancialReportService.generate_statement(student, academic_year)
        return Response(statement)

    @action(detail=False, methods=['get'])
    def download_statement(self, request):
        """
        Download Financial Statement as PDF.
        Same params as statement action.
        """
        student_id = request.query_params.get('student_id')
        academic_year_id = request.query_params.get('academic_year_id')
        
        if not student_id:
            return Response({'error': 'student_id est requis'}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.students.models import Student
        from apps.finance.services.reporting import FinancialReportService
        from apps.university.models import AcademicYear
        from apps.core.services.pdf import PDFService
        from django.http import HttpResponse
        
        try:
            student = Student.objects.get(pk=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Étudiant introuvable'}, status=status.HTTP_404_NOT_FOUND)
            
        academic_year = None
        if academic_year_id:
            try:
                academic_year = AcademicYear.objects.get(pk=academic_year_id)
            except AcademicYear.DoesNotExist:
                return Response({'error': 'Année académique introuvable'}, status=status.HTTP_404_NOT_FOUND)
                
        # Generate statement data
        statement_data = FinancialReportService.generate_statement(student, academic_year)
        
        # Generate PDF
        buffer = PDFService.generate_financial_statement(statement_data)
        
        filename = f"Releve_Financier_{student.student_id}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class SalaryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing employee salaries.
    
    Provides:
    - List: GET /api/v1/salaries/
    - Create: POST /api/v1/salaries/
    - Retrieve: GET /api/v1/salaries/{id}/
    - Update: PUT/PATCH /api/v1/salaries/{id}/
    - Delete: DELETE /api/v1/salaries/{id}/
    
    Custom Actions:
    - pay: POST /api/v1/salaries/{id}/pay/
    - pending: GET /api/v1/salaries/pending/
    
    Permissions:
    - All operations: Accountant and Admin only
    
    Filtering:
    - employee: Filter by employee
    - month: Filter by month (1-12)
    - year: Filter by year
    - status: Filter by status (PENDING, PAID, CANCELLED)
    
    Searching:
    - employee name, employee email
    
    Ordering:
    - year, month, net_salary, created_at
    """
    
    queryset = Salary.objects.select_related(
        'employee', 'processed_by'
    ).all()

    def get_queryset(self):
        """Filter by current academic year date range by default."""
        queryset = super().get_queryset()
        
        # If explicit year/month filter, don't override
        if 'year' in self.request.query_params or 'month' in self.request.query_params:
            return queryset

        # Filter by current academic year if requested (default True)
        current_year_only = self.request.query_params.get('current_year_only', 'true').lower() == 'true'

        if current_year_only:
            from apps.university.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            
            if current_year:
                start = current_year.start_date
                end = current_year.end_date
                
                queryset = queryset.filter(
                    Q(year__gt=start.year) | Q(year=start.year, month__gte=start.month)
                ).filter(
                    Q(year__lt=end.year) | Q(year=end.year, month__lte=end.month)
                )
            
        return queryset

    permission_classes = [IsAuthenticated, IsFinanceViewer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'month', 'year', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['year', 'month', 'net_salary', 'created_at']
    ordering = ['-year', '-month']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SalaryListSerializer
        elif self.action == 'retrieve':
            return SalaryDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SalaryCreateSerializer
        return SalarySerializer
    
    def perform_create(self, serializer):
        """
        Set processed_by to current user on creation.
        Calculate net_salary from base_salary, bonuses, and deductions.
        Prevent duplicate salary records.
        """
        validated_data = serializer.validated_data
        employee = validated_data['employee']
        month = validated_data['month']
        year = validated_data['year']
        
        # Check for duplicate
        existing = Salary.objects.filter(
            employee=employee,
            month=month,
            year=year
        ).exists()
        
        if existing:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "non_field_errors": [
                    f"Un enregistrement de salaire existe déjà pour cet employé en {month}/{year}"
                ]
            })
        
        # Calculate net salary
        base_salary = validated_data.get('base_salary', 0)
        bonuses = validated_data.get('bonuses', 0)
        deductions = validated_data.get('deductions', 0)
        net_salary = base_salary + bonuses - deductions
        
        serializer.save(
            processed_by=self.request.user,
            net_salary=net_salary
        )

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """
        Mark a salary as paid.
        
        Updates status to PAID and records payment date.
        """
        salary = self.get_object()
        
        if salary.status == 'PAID':
            return Response(
                {"message": "Ce salaire est déjà payé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if salary.status == 'CANCELLED':
            return Response(
                {"error": "Impossible de payer un salaire annulé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        salary.status = 'PAID'
        salary.payment_date = timezone.now().date()
        salary.save()
        
        serializer = SalaryDetailSerializer(salary)
        return Response({
            "message": "Salaire marqué comme payé",
            "salary": serializer.data
        })

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get all pending salary payments.
        
        Query parameters:
        - month: Filter by month (optional)
        - year: Filter by year (optional)
        
        Returns all salaries with PENDING status.
        """
        queryset = self.queryset.filter(status='PENDING')
        
        month = request.query_params.get('month')
        if month:
            try:
                queryset = queryset.filter(month=int(month))
            except ValueError:
                pass
        
        year = request.query_params.get('year')
        if year:
            try:
                queryset = queryset.filter(year=int(year))
            except ValueError:
                pass
        
        total_pending = queryset.aggregate(total=Sum('net_salary'))['total'] or 0
        
        serializer = SalaryListSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'total_pending': total_pending,
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export filtered salaries to Excel."""
        queryset = self.filter_queryset(self.get_queryset())
        excel_file = SalaryExcelService.export_salaries(queryset)
        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="salaires.xlsx"'
        return response

    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download import template for salaries."""
        excel_file = SalaryExcelService.download_template()
        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_import_salaires.xlsx"'
        return response

    @action(detail=False, methods=['post'])
    def import_excel(self, request):
        """Import salaries from Excel."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )
        success_count, errors = SalaryExcelService.import_salaries(file_obj, request.user)
        return Response({
            "success_count": success_count,
            "errors": errors
        }, status=status.HTTP_201_CREATED if success_count > 0 else status.HTTP_400_BAD_REQUEST)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing university expenses.
    
    Provides:
    - List: GET /api/v1/expenses/
    - Create: POST /api/v1/expenses/
    - Retrieve: GET /api/v1/expenses/{id}/
    - Update: PUT/PATCH /api/v1/expenses/{id}/
    - Delete: DELETE /api/v1/expenses/{id}/
    
    Custom Actions:
    - summary: GET /api/v1/expenses/summary/
    
    Permissions:
    - All operations: Accountant and Admin only
    
    Filtering:
    - category: Filter by category (SALARIES, UTILITIES, MAINTENANCE, EQUIPMENT, SUPPLIES, OTHER)
    - approved_by: Filter by approver
    - created_by: Filter by creator
    
    Searching:
    - description, category
    
    Ordering:
    - date, amount, created_at
    """
    
    queryset = Expense.objects.select_related(
        'approved_by', 'created_by'
    ).all()

    def get_queryset(self):
        """Filter by current academic year date range by default."""
        queryset = super().get_queryset()
        
        # If explicit date filter, don't override strongly (or intersect? let's user decide)
        # Assuming if user didn't request specific range, they want current year context
        if 'start_date' in self.request.query_params or 'end_date' in self.request.query_params:
            return queryset

        # Filter by current academic year if requested (default True)
        current_year_only = self.request.query_params.get('current_year_only', 'true').lower() == 'true'

        if current_year_only:
            from apps.university.models import AcademicYear
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if current_year:
                queryset = queryset.filter(date__range=(current_year.start_date, current_year.end_date))
            
        return queryset

    permission_classes = [IsAuthenticated, IsFinanceViewer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'approved_by', 'created_by']
    search_fields = ['description', 'category']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ExpenseListSerializer
        elif self.action == 'retrieve':
            return ExpenseDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ExpenseCreateSerializer
        return ExpenseSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user on creation."""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get expense summary by category.
        
        Query parameters:
        - start_date: Filter from date (YYYY-MM-DD)
        - end_date: Filter to date (YYYY-MM-DD)
        
        Returns total expenses grouped by category.
        """
        from django.db.models import Count
        
        queryset = self.queryset
        
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # Group by category
        summary = queryset.values('category').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        total = queryset.aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_expenses': total,
            'by_category': list(summary)
        })

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export filtered expenses to Excel."""
        queryset = self.filter_queryset(self.get_queryset())
        excel_file = ExpenseExcelService.export_expenses(queryset)
        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="depenses.xlsx"'
        return response

    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download import template for expenses."""
        excel_file = ExpenseExcelService.download_template()
        response = HttpResponse(
            excel_file,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_import_depenses.xlsx"'
        return response

    @action(detail=False, methods=['post'])
    def import_excel(self, request):
        """Import expenses from Excel."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"error": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )
        success_count, errors = ExpenseExcelService.import_expenses(file_obj, request.user)
        return Response({
            "success_count": success_count,
            "errors": errors
        }, status=status.HTTP_201_CREATED if success_count > 0 else status.HTTP_400_BAD_REQUEST)


class FinanceDashboardView(APIView):
    """
    Dashboard for financial overview.
    
    Provides:
    - GET /api/v1/finance/dashboard/
    
    Returns:
    - current_year: Current academic year name
    - total_tuition_collected: Total tuition payments collected
    - total_salaries_paid: Total salaries paid
    - total_expenses: Total expenses
    - pending_payments_count: Number of pending payments
    - outstanding_balances: Total outstanding student balances
    - net_balance: Net financial balance
    
    Permissions:
    - Accountant and Admin only
    """
    permission_classes = [IsAuthenticated, IsFinanceViewer]

    def get(self, request):
        from apps.university.models import AcademicYear

        current_year = AcademicYear.objects.filter(is_current=True).first()
        if not current_year:
            return Response({'error': 'No current academic year set'})

        # Calculate totals
        total_tuition = TuitionPayment.objects.filter(
            academic_year=current_year,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_salaries = Salary.objects.filter(
            status='PAID',
            # Filter salaries within academic year range
            payment_date__range=(current_year.start_date, current_year.end_date)
        ).aggregate(total=Sum('net_salary'))['total'] or 0

        total_expenses = Expense.objects.filter(
            # Filter expenses within academic year range
            date__range=(current_year.start_date, current_year.end_date)
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0

        pending_payments = TuitionPayment.objects.filter(
            academic_year=current_year,
            status='PENDING'
        ).count()
        
        # Outstanding balances
        outstanding = StudentBalance.objects.filter(
            academic_year=current_year
        ).aggregate(
            total=Sum(F('total_due') - F('total_paid'))
        )['total'] or 0

        completed_payments = TuitionPayment.objects.filter(
            academic_year=current_year,
            status='COMPLETED',
        )
        paid_salaries = Salary.objects.filter(
            status='PAID',
            payment_date__range=(current_year.start_date, current_year.end_date),
        )
        year_expenses = Expense.objects.filter(
            date__range=(current_year.start_date, current_year.end_date),
        )

        def month_key(value):
            return value.strftime('%Y-%m') if value else ''

        monthly_revenue = {
            month_key(row['period_month']): row['total'] or 0
            for row in completed_payments.annotate(
                period_month=TruncMonth('payment_date')
            ).values('period_month').annotate(total=Sum('amount')).order_by('period_month')
        }
        monthly_salaries = {
            month_key(row['period_month']): row['total'] or 0
            for row in paid_salaries.annotate(
                period_month=TruncMonth('payment_date')
            ).values('period_month').annotate(total=Sum('net_salary')).order_by('period_month')
        }
        monthly_expenses = {
            month_key(row['period_month']): row['total'] or 0
            for row in year_expenses.annotate(
                period_month=TruncMonth('date')
            ).values('period_month').annotate(total=Sum('amount')).order_by('period_month')
        }

        monthly_cash_flow = []
        cursor = date(current_year.start_date.year, current_year.start_date.month, 1)
        end_month = date(current_year.end_date.year, current_year.end_date.month, 1)
        while cursor <= end_month:
            key = cursor.strftime('%Y-%m')
            revenue = monthly_revenue.get(key, 0)
            salaries = monthly_salaries.get(key, 0)
            expenses = monthly_expenses.get(key, 0)
            monthly_cash_flow.append({
                'month': key,
                'revenue': revenue,
                'salaries': salaries,
                'expenses': expenses,
                'net': revenue - salaries - expenses,
            })
            cursor = date(
                cursor.year + (1 if cursor.month == 12 else 0),
                1 if cursor.month == 12 else cursor.month + 1,
                1,
            )

        expense_category_rows = list(
            year_expenses.values('category')
            .annotate(amount=Sum('amount'), count=Count('id'))
            .order_by('-amount')
        )
        category_labels = dict(Expense.ExpenseCategory.choices)
        expense_categories = [
            {
                'category': row['category'],
                'label': category_labels.get(row['category'], row['category']),
                'amount': row['amount'] or 0,
                'count': row['count'],
                'percentage': round(float(row['amount'] or 0) / float(total_expenses) * 100, 1)
                if total_expenses else 0,
            }
            for row in expense_category_rows
        ]

        payment_method_rows = list(
            completed_payments.values('payment_method')
            .annotate(amount=Sum('amount'), count=Count('id'))
            .order_by('-amount')
        )
        method_labels = dict(TuitionPayment.PaymentMethod.choices)
        payment_methods = [
            {
                'method': row['payment_method'],
                'label': method_labels.get(row['payment_method'], row['payment_method']),
                'amount': row['amount'] or 0,
                'count': row['count'],
                'percentage': round(float(row['amount'] or 0) / float(total_tuition) * 100, 1)
                if total_tuition else 0,
            }
            for row in payment_method_rows
        ]

        payment_status_labels = dict(TuitionPayment.PaymentStatus.choices)
        payment_statuses = [
            {
                'status': row['status'],
                'label': payment_status_labels.get(row['status'], row['status']),
                'amount': row['amount'] or 0,
                'count': row['count'],
            }
            for row in TuitionPayment.objects.filter(
                academic_year=current_year
            ).values('status').annotate(
                amount=Sum('amount'), count=Count('id')
            ).order_by('-count')
        ]

        expected_revenue = total_tuition + max(outstanding, 0)
        collection_rate = (
            round(float(total_tuition) / float(expected_revenue) * 100, 1)
            if expected_revenue else 0
        )

        return Response({
            'current_year': current_year.name,
            'total_tuition_collected': total_tuition,
            'total_salaries_paid': total_salaries,
            'total_expenses': total_expenses,
            'pending_payments_count': pending_payments,
            'outstanding_balances': max(outstanding, 0),
            'net_balance': total_tuition - total_salaries - total_expenses,
            'expected_revenue': expected_revenue,
            'collection_rate': collection_rate,
            'monthly_cash_flow': monthly_cash_flow,
            'expense_categories': expense_categories,
            'payment_methods': payment_methods,
            'payment_statuses': payment_statuses,
        })
