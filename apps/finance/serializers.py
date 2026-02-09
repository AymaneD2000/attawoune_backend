from rest_framework import serializers
from decimal import Decimal
from .models import TuitionPayment, TuitionFee, StudentBalance, Salary, Expense


# TuitionPayment Serializers
class TuitionPaymentListSerializer(serializers.ModelSerializer):
    """List serializer for TuitionPayment with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    received_by_name = serializers.CharField(
        source='received_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = TuitionPayment
        fields = [
            'id', 'student', 'student_name', 'student_matricule',
            'academic_year', 'academic_year_name', 'amount', 'payment_method',
            'payment_method_display', 'status', 'status_display', 'reference',
            'payment_date', 'received_by', 'received_by_name'
        ]


class TuitionPaymentDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for TuitionPayment with all fields and computed properties."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    student_program = serializers.CharField(
        source='student.program.name', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    received_by_name = serializers.CharField(
        source='received_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = TuitionPayment
        fields = '__all__'


class TuitionPaymentCreateSerializer(serializers.ModelSerializer):
    """Create serializer for TuitionPayment with validation."""
    
    class Meta:
        model = TuitionPayment
        fields = [
            'student', 'academic_year', 'amount', 'payment_method',
            'status', 'reference', 'description', 'receipt_number',
            'payment_date', 'received_by'
        ]
        extra_kwargs = {
            'academic_year': {'required': False},
            'reference': {'required': False},
            'payment_date': {'required': False},
            'received_by': {'read_only': True}
        }
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être positif."
            )
        return value
    
    def validate_reference(self, value):
        """Validate that reference is unique."""
        if TuitionPayment.objects.filter(reference=value).exists():
            raise serializers.ValidationError(
                "Un paiement avec cette référence existe déjà."
            )
        return value


# TuitionFee Serializers
class TuitionFeeListSerializer(serializers.ModelSerializer):
    """List serializer for TuitionFee with basic fields."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    
    class Meta:
        model = TuitionFee
        fields = [
            'id', 'program', 'program_name', 'program_code',
            'academic_year', 'academic_year_name', 'amount',
            'installments_allowed', 'due_date'
        ]


class TuitionFeeDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for TuitionFee with all fields and computed properties."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    department_name = serializers.CharField(
        source='program.department.name', read_only=True
    )
    faculty_name = serializers.CharField(
        source='program.department.faculty.name', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    academic_year_is_current = serializers.BooleanField(
        source='academic_year.is_current', read_only=True
    )
    
    class Meta:
        model = TuitionFee
        fields = '__all__'


class TuitionFeeCreateSerializer(serializers.ModelSerializer):
    """Create serializer for TuitionFee with validation."""
    
    class Meta:
        model = TuitionFee
        fields = [
            'program', 'academic_year', 'amount', 'installments_allowed', 'due_date'
        ]
        # Remove default unique_together validator to use custom validation
        validators = []
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être positif."
            )
        return value
    
    def validate_installments_allowed(self, value):
        """Validate that installments_allowed is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le nombre de tranches doit être positif."
            )
        return value
    
    def validate(self, attrs):
        """Validate tuition fee constraints."""
        program = attrs.get('program')
        academic_year = attrs.get('academic_year')
        
        # Check for duplicate tuition fee
        if program and academic_year:
            # Only check for duplicates on create (when instance is None)
            if not self.instance:
                if TuitionFee.objects.filter(program=program, academic_year=academic_year).exists():
                    raise serializers.ValidationError({
                        "program": "Des frais de scolarité existent déjà pour ce programme et cette année académique."
                    })
        
        return attrs


# StudentBalance Serializers
class StudentBalanceListSerializer(serializers.ModelSerializer):
    """List serializer for StudentBalance with basic fields."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    student_program = serializers.CharField(
        source='student.program.name', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = StudentBalance
        fields = [
            'id', 'student', 'student_name', 'student_matricule', 'student_program',
            'academic_year', 'academic_year_name', 'total_due',
            'total_paid', 'balance', 'is_paid', 'updated_at'
        ]


class StudentBalanceDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for StudentBalance with all fields and computed properties."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    student_email = serializers.CharField(
        source='student.user.email', read_only=True
    )
    student_phone = serializers.CharField(
        source='student.user.phone', read_only=True
    )
    student_program = serializers.CharField(
        source='student.program.name', read_only=True
    )
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )
    academic_year_is_current = serializers.BooleanField(
        source='academic_year.is_current', read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_paid = serializers.BooleanField(read_only=True)
    payments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentBalance
        fields = '__all__'
    
    def get_payments_count(self, obj):
        return obj.student.tuition_payments.filter(
            academic_year=obj.academic_year,
            status='COMPLETED'
        ).count()


# Salary Serializers
class SalaryListSerializer(serializers.ModelSerializer):
    """List serializer for Salary with basic fields."""
    employee_name = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    employee_email = serializers.CharField(
        source='employee.email', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    processed_by_name = serializers.CharField(
        source='processed_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = Salary
        fields = [
            'id', 'employee', 'employee_name', 'employee_email',
            'month', 'year', 'base_salary', 'bonuses', 'deductions',
            'net_salary', 'status', 'status_display', 'payment_date',
            'processed_by', 'processed_by_name'
        ]


class SalaryDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Salary with all fields and computed properties."""
    employee_name = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    employee_email = serializers.CharField(
        source='employee.email', read_only=True
    )
    employee_phone = serializers.CharField(
        source='employee.phone', read_only=True
    )
    employee_role = serializers.CharField(
        source='employee.get_role_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    processed_by_name = serializers.CharField(
        source='processed_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = Salary
        fields = '__all__'


class SalaryCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Salary with validation and automatic net salary calculation."""
    
    class Meta:
        model = Salary
        fields = [
            'employee', 'month', 'year', 'base_salary', 'bonuses',
            'deductions', 'status', 'payment_date', 'remarks', 'processed_by'
        ]
        # Remove default unique_together validator to use custom validation
        validators = []
    
    def validate_month(self, value):
        """Validate that month is between 1 and 12."""
        if value < 1 or value > 12:
            raise serializers.ValidationError(
                "Le mois doit être entre 1 et 12."
            )
        return value
    
    def validate_year(self, value):
        """Validate that year is reasonable."""
        if value < 2000 or value > 2100:
            raise serializers.ValidationError(
                "L'année doit être entre 2000 et 2100."
            )
        return value
    
    def validate_base_salary(self, value):
        """Validate that base_salary is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le salaire de base doit être positif."
            )
        return value
    
    def validate_bonuses(self, value):
        """Validate that bonuses is non-negative."""
        if value < 0:
            raise serializers.ValidationError(
                "Les primes ne peuvent pas être négatives."
            )
        return value
    
    def validate_deductions(self, value):
        """Validate that deductions is non-negative."""
        if value < 0:
            raise serializers.ValidationError(
                "Les déductions ne peuvent pas être négatives."
            )
        return value
    
    def validate(self, attrs):
        """Validate salary constraints."""
        employee = attrs.get('employee')
        month = attrs.get('month')
        year = attrs.get('year')
        
        # Check for duplicate salary record
        if employee and month and year:
            # Only check for duplicates on create (when instance is None)
            if not self.instance:
                if Salary.objects.filter(employee=employee, month=month, year=year).exists():
                    raise serializers.ValidationError({
                        "employee": "Un enregistrement de salaire existe déjà pour cet employé, ce mois et cette année."
                    })
        
        return attrs


# Expense Serializers
class ExpenseListSerializer(serializers.ModelSerializer):
    """List serializer for Expense with basic fields."""
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_display', 'description',
            'amount', 'date', 'approved_by', 'approved_by_name',
            'created_by', 'created_by_name', 'created_at'
        ]


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for Expense with all fields and computed properties."""
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name', read_only=True
    )
    approved_by_email = serializers.CharField(
        source='approved_by.email', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    created_by_email = serializers.CharField(
        source='created_by.email', read_only=True
    )
    
    class Meta:
        model = Expense
        fields = '__all__'


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Create serializer for Expense with validation."""
    
    class Meta:
        model = Expense
        fields = [
            'category', 'description', 'amount', 'date',
            'receipt', 'approved_by', 'created_by'
        ]
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être positif."
            )
        return value


# Backward compatibility serializers
class TuitionPaymentSerializer(serializers.ModelSerializer):
    """Default serializer for TuitionPayment (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = TuitionPayment
        fields = '__all__'


class TuitionFeeSerializer(serializers.ModelSerializer):
    """Default serializer for TuitionFee (backward compatibility)."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    academic_year_name = serializers.CharField(
        source='academic_year.name', read_only=True
    )

    class Meta:
        model = TuitionFee
        fields = '__all__'


class StudentBalanceSerializer(serializers.ModelSerializer):
    """Default serializer for StudentBalance (backward compatibility)."""
    student_name = serializers.CharField(
        source='student.user.get_full_name', read_only=True
    )
    student_matricule = serializers.CharField(
        source='student.student_id', read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentBalance
        fields = '__all__'


class SalarySerializer(serializers.ModelSerializer):
    """Default serializer for Salary (backward compatibility)."""
    employee_name = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = Salary
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    """Default serializer for Expense (backward compatibility)."""
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )

    class Meta:
        model = Expense
        fields = '__all__'
