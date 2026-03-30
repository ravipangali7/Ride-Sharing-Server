import getpass

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import AdminUser, User


class Command(BaseCommand):
    help = (
        "Create or update a Django superuser with phone login plus an AdminUser profile (role=superadmin). "
        "Example: python manage.py seed_admin --phone 9800000000 --password secret"
    )

    def add_arguments(self, parser):
        parser.add_argument("--phone", type=str, default="", help="Unique phone (USERNAME_FIELD)")
        parser.add_argument("--password", type=str, default="", help="Password (omit to prompt)")
        parser.add_argument("--email", type=str, default="", help="Optional email")
        parser.add_argument("--full-name", type=str, default="System Administrator", dest="full_name")
        parser.add_argument(
            "--update",
            action="store_true",
            help="If user exists, reset password and AdminUser role instead of failing",
        )

    def handle(self, *args, **options):
        phone = (options["phone"] or "").strip()
        if not phone:
            phone = input("Phone: ").strip()
        if not phone:
            self.stderr.write(self.style.ERROR("phone is required"))
            return

        password = options["password"]
        if not password:
            password = getpass.getpass("Password: ")
        if not password:
            self.stderr.write(self.style.ERROR("password is required"))
            return

        email = (options["email"] or "").strip() or None
        full_name = options["full_name"] or "Admin"

        with transaction.atomic():
            user = User.objects.filter(phone=phone).first()
            if user and not options["update"]:
                self.stderr.write(self.style.ERROR(f"User {phone} already exists. Pass --update to reset password."))
                return
            if user and options["update"]:
                user.full_name = full_name
                if email is not None:
                    user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.WARNING(f"Updated password for {phone}"))
            else:
                user = User.objects.create_superuser(
                    phone=phone,
                    password=password,
                    full_name=full_name,
                    email=email,
                    gender="other",
                )

            admin_profile, created = AdminUser.objects.get_or_create(
                user=user,
                defaults={
                    "role": "superadmin",
                    "permissions": {"all": True},
                    "is_active": True,
                },
            )
            if not created:
                admin_profile.role = "superadmin"
                admin_profile.permissions = {"all": True}
                admin_profile.is_active = True
                admin_profile.save()
                self.stdout.write(self.style.SUCCESS(f"AdminUser profile refreshed for {phone}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created superuser + AdminUser for {phone}"))
