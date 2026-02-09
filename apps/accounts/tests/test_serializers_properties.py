"""
Property-based tests for accounts serializers.

These tests verify universal properties that should hold for all valid inputs.
"""

from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer
)

User = get_user_model()


class UserSerializerPropertyTests(TestCase):
    """Property tests for UserSerializer."""
    
    @settings(max_examples=10)
    @given(
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        role=st.sampled_from([choice[0] for choice in User.Role.choices])
    )
    def test_property_1_foreign_key_representation(self, first_name, last_name, role):
        """
        Feature: backend-api-implementation, Property 1: Foreign Key Representation
        
        **Validates: Requirements 1.8**
        
        For any model instance with foreign key relationships, when serialized,
        the output should include readable representations (names, codes, or display values)
        of the related objects, not just IDs.
        
        For User model, this means the serializer should include:
        - full_name: computed property combining first_name and last_name
        - role_display: human-readable role name
        """
        # Create a user with the given attributes
        user = User.objects.create_user(
            username=f"user_{first_name}_{last_name}".lower()[:30],
            email=f"{first_name.lower()}@test.com",
            first_name=first_name,
            last_name=last_name,
            role=role,
            password="testpass123"
        )
        
        # Serialize the user
        serializer = UserSerializer(user)
        data = serializer.data
        
        # Verify readable representations are included
        self.assertIn('full_name', data)
        self.assertIn('role_display', data)
        
        # Verify full_name is computed correctly
        expected_full_name = f"{first_name} {last_name}".strip()
        self.assertEqual(data['full_name'], expected_full_name)
        
        # Verify role_display is human-readable
        self.assertEqual(data['role_display'], user.get_role_display())
        self.assertIsInstance(data['role_display'], str)
    
    @settings(max_examples=10)
    @given(
        username=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))),
        email=st.emails(),
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    def test_property_3_computed_properties_inclusion(self, username, email, first_name, last_name):
        """
        Feature: backend-api-implementation, Property 3: Computed Properties Inclusion
        
        **Validates: Requirements 1.10**
        
        For any model with computed properties (methods decorated with @property),
        the serializer should include those properties as read-only fields in the output.
        
        For User model, computed properties include:
        - full_name: combines first_name and last_name
        - role_display: human-readable role name
        """
        # Create a user
        user = User.objects.create_user(
            username=username[:20],
            email=email,
            first_name=first_name,
            last_name=last_name,
            password="testpass123"
        )
        
        # Serialize the user
        serializer = UserSerializer(user)
        data = serializer.data
        
        # Verify computed properties are included
        self.assertIn('full_name', data)
        self.assertIn('role_display', data)
        
        # Verify they are read-only (not in Meta.fields that can be written)
        self.assertIn('full_name', serializer.Meta.read_only_fields)
        self.assertIn('role_display', serializer.Meta.read_only_fields)
        
        # Verify computed values match model methods
        self.assertEqual(data['full_name'], user.get_full_name())
        self.assertEqual(data['role_display'], user.get_role_display())


class UserCreateSerializerPropertyTests(TestCase):
    """Property tests for UserCreateSerializer."""
    
    @settings(max_examples=10)
    @given(
        username=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))),
        email=st.emails(),
        password=st.text(min_size=8, max_size=20),
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    def test_property_2_validation_enforcement_password_mismatch(
        self, username, email, password, first_name, last_name
    ):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Password and password_confirm don't match.
        """
        # Create data with mismatched passwords
        data = {
            'username': username[:20],
            'email': email,
            'password': password,
            'password_confirm': password + 'x',  # Intentionally different
            'first_name': first_name,
            'last_name': last_name,
            'role': User.Role.STUDENT
        }
        
        # Validate with serializer
        serializer = UserCreateSerializer(data=data)
        
        # Should be invalid
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have password error
        self.assertIn('password', serializer.errors)
    
    @settings(max_examples=10)
    @given(
        username=st.text(
            min_size=5, 
            max_size=20, 
            alphabet=st.characters(
                whitelist_categories=('Ll', 'Nd'),
                blacklist_characters='\x00\n\r\t'
            )
        ),
        email=st.emails(),
        first_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    def test_property_2_validation_enforcement_duplicate_username(
        self, username, email, first_name, last_name
    ):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: Duplicate username should be rejected.
        """
        # Normalize username to ASCII-only to avoid Unicode edge cases
        username_normalized = ''.join(c for c in username if ord(c) < 128)[:20]
        if len(username_normalized) < 5:
            username_normalized = 'user' + username_normalized + '12345'
        username_normalized = username_normalized[:20]
        
        # Create an existing user
        existing_user = User.objects.create_user(
            username=username_normalized,
            email=f"existing_{email}",
            password="testpass123"
        )
        
        # Try to create another user with the same username
        data = {
            'username': username_normalized,
            'email': email,
            'password': 'ValidPass123!',
            'password_confirm': 'ValidPass123!',
            'first_name': first_name,
            'last_name': last_name,
            'role': User.Role.STUDENT
        }
        
        serializer = UserCreateSerializer(data=data)
        
        # Should be invalid due to duplicate username
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have username error
        self.assertIn('username', serializer.errors)


class PasswordChangeSerializerPropertyTests(TestCase):
    """Property tests for PasswordChangeSerializer."""
    
    @settings(max_examples=10)
    @given(
        old_password=st.text(
            min_size=8, 
            max_size=20,
            alphabet=st.characters(blacklist_characters='\x00\n\r\t', blacklist_categories=('Cc', 'Cs'))
        ),
        new_password=st.text(
            min_size=8, 
            max_size=20,
            alphabet=st.characters(blacklist_characters='\x00\n\r\t', blacklist_categories=('Cc', 'Cs'))
        )
    )
    def test_property_2_validation_enforcement_password_mismatch(
        self, old_password, new_password
    ):
        """
        Feature: backend-api-implementation, Property 2: Validation Enforcement
        
        **Validates: Requirements 1.9**
        
        For any invalid input data that violates model constraints or business rules,
        the serializer should reject it and return detailed validation errors.
        
        Test case: New password and confirmation don't match.
        """
        # Create data with mismatched new passwords
        data = {
            'old_password': old_password,
            'new_password': new_password,
            'new_password_confirm': new_password + 'x'  # Intentionally different
        }
        
        # Validate with serializer
        serializer = PasswordChangeSerializer(data=data)
        
        # Should be invalid
        is_valid = serializer.is_valid()
        self.assertFalse(is_valid)
        
        # Should have new_password error
        self.assertIn('new_password', serializer.errors)
