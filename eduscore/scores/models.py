from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField

class User(AbstractUser):
    ROLES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('student', 'Student'),
    ]
    image = models.ImageField(upload_to='users/%Y/%m/', null=True, blank=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    student_class = models.ForeignKey('Class', on_delete=models.SET_NULL, null=True, blank=True)
    total_score = models.FloatField(default=0)
    role = models.CharField(max_length=10, choices=ROLES, default='student')

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_date']

class Department(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name

class Class(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.department.name}"

class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Activity(BaseModel):
    title = models.CharField(max_length=255)
    description = RichTextField()
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField()
    image = models.ImageField(upload_to='activities/%Y/%m/', null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('open', 'Open'), ('closed', 'Closed'), ('canceled', 'Canceled')],
        default='open'
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    tags = models.ManyToManyField('Tag')
    max_score = models.FloatField(default=0)

    def __str__(self):
        return self.title

class Participation(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    image = models.ImageField(upload_to='proofs/%Y/%m/', null=True, blank=True)

    class Meta:
        unique_together = ('student', 'activity')


class EvaluationGroup(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    max_score = models.FloatField()

    def __str__(self):
        return self.name


class EvaluationCriteria(BaseModel):
    group = models.ForeignKey(EvaluationGroup, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    score= models.FloatField(default=0)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='evaluation_criteria', null=True,blank=True)

    def __str__(self):
        return f"{self.name} ({self.group.name})"


class DisciplinePoint(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    criteria = models.ForeignKey(EvaluationCriteria, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    group_total_score = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)

        self.calculate_group_total_score()

        super().save(update_fields=['group_total_score'])

        self.update_student_total_score()

    def calculate_group_total_score(self):
        evaluation_group = self.criteria.group

        group_total = DisciplinePoint.objects.filter(
        student=self.student,
        activity=self.activity,
        criteria__group=evaluation_group
    ).exclude(id=self.id).aggregate(total=models.Sum('score'))['total'] or 0

        group_total += self.score

        self.group_total_score = min(group_total, evaluation_group.max_score)

    def update_student_total_score(self):
        evaluation_groups = EvaluationGroup.objects.all()

        total_score = 0

        for group in evaluation_groups:
            group_total = DisciplinePoint.objects.filter(
                student=self.student,
                criteria__group=group
            ).aggregate(total=models.Sum('score'))['total'] or 0

            total_score += min(group_total, group.max_score)

        self.student.total_score = total_score
        self.student.save()

class Report(BaseModel):
    student = models.ForeignKey(User,  related_name='student_reports', on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='reports/%Y/%m/')
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    handled_by = models.ForeignKey(User, related_name='handled_reports', null=True, blank=True, on_delete=models.SET_NULL)


class NewsFeed(BaseModel):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    description = RichTextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.activity.title

class Registration(BaseModel):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'activity')

    def __str__(self):
        return f"{self.student.username} - {self.activity.title}"

class Tag(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name

class Interaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    newsfeed = models.ForeignKey(NewsFeed, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class Like(Interaction):
    class Meta:
        unique_together = ('user', 'newsfeed')

class Comment(Interaction):
    content = RichTextField()

class Message(BaseModel):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User,related_name='received_messages', on_delete=models.CASCADE)
    content = RichTextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    firebase_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"