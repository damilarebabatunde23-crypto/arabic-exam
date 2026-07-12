from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_TEACHER = 'teacher'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_TEACHER, 'Teacher / Admin'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    @property
    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_profile(sender, instance, created, **kwargs):
    if created:
        # Superusers/staff created via createsuperuser are treated as teachers.
        role = Profile.ROLE_TEACHER if instance.is_superuser or instance.is_staff else Profile.ROLE_STUDENT
        Profile.objects.create(user=instance, role=role)
    elif not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
