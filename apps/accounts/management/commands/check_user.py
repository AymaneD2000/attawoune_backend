"""
Management command to check, verify, and diagnose user accounts.

Usage:
    python manage.py check_user <username>
    python manage.py check_user <username> --verify-password <password>
    python manage.py check_user <username> --set-password <new_password>
    python manage.py check_user --list-staff
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Diagnose, check, or reset user accounts for troubleshooting login issues."

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", type=str, help="Username to check")
        parser.add_argument(
            "--verify-password",
            type=str,
            dest="verify_password",
            help="Verify if password matches for the specified username",
        )
        parser.add_argument(
            "--set-password",
            type=str,
            dest="set_password",
            help="Reset password for the specified username",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Activate user if inactive (sets is_active=True)",
        )
        parser.add_argument(
            "--list-staff",
            action="store_true",
            help="List all administrative and staff users with their roles and status",
        )

    def handle(self, *args, **options):
        if options["list_staff"]:
            staff_users = User.objects.filter(role__in=["ADMIN", "DEAN", "ACCOUNTANT", "SECRETARY", "TEACHER"])
            self.stdout.write(self.style.MIGRATE_HEADING("Staff and Administrative Users:"))
            for u in staff_users:
                status_icon = "✅" if u.is_active else "❌ INACTIVE"
                self.stdout.write(f" - {u.username} | Role: {u.role} | Active: {status_icon} | Email: {u.email}")
            return

        username = options["username"]
        if not username:
            self.stderr.write(self.style.ERROR("Error: Please provide a username or use --list-staff."))
            return

        user = User.objects.filter(username=username).first()
        if not user:
            # Check by email as a helper
            by_email = User.objects.filter(email=username).first()
            if by_email:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ User with email '{username}' found, but their actual username is '{by_email.username}'."
                    )
                )
                user = by_email
            else:
                self.stderr.write(self.style.ERROR(f"❌ User '{username}' does not exist."))
                return

        self.stdout.write(self.style.SUCCESS(f"User Found: {user.username}"))
        self.stdout.write(f" - ID: {user.id}")
        self.stdout.write(f" - Full Name: {user.get_full_name()}")
        self.stdout.write(f" - Email: {user.email}")
        self.stdout.write(f" - Role: {user.role}")
        self.stdout.write(f" - Is Active: {'✅ Yes' if user.is_active else '❌ No (Account disabled)'}")
        self.stdout.write(f" - Is Staff: {user.is_staff}")
        self.stdout.write(f" - Last Login: {user.last_login}")

        # Activate if requested
        if options["activate"] and not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            self.stdout.write(self.style.SUCCESS("✅ Account has been activated (is_active=True)."))

        # Verify password if provided
        if options["verify_password"]:
            matches = user.check_password(options["verify_password"])
            if matches:
                self.stdout.write(self.style.SUCCESS("✅ Password matches successfully."))
            else:
                self.stdout.write(self.style.ERROR("❌ Password does NOT match."))

        # Set new password if provided
        if options["set_password"]:
            user.set_password(options["set_password"])
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Password for '{user.username}' updated successfully."))
