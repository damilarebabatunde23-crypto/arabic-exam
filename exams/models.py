from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Exam(models.Model):
    title = models.CharField('Exam Title', max_length=255)
    description = models.TextField('Description', blank=True)
    duration_minutes = models.PositiveIntegerField('Duration (minutes)', default=60)
    start_time = models.DateTimeField('Start Time')
    end_time = models.DateTimeField('End Time')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_exams',
    )
    is_active = models.BooleanField('Published to students', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Exam'
        verbose_name_plural = 'Exams'

    def __str__(self):
        return self.title

    @property
    def total_marks(self):
        return sum(q.marks for q in self.questions.all())

    @property
    def has_essay_questions(self):
        return self.questions.filter(question_type=Question.TYPE_ESSAY).exists()

    def is_open(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    def has_ended(self):
        return timezone.now() > self.end_time

    def has_started(self):
        return timezone.now() >= self.start_time


class Question(models.Model):
    TYPE_MCQ = 'mcq'
    TYPE_ESSAY = 'essay'
    TYPE_CHOICES = [
        (TYPE_MCQ, 'Multiple Choice'),
        (TYPE_ESSAY, 'Essay Question'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField('Question Type', max_length=10, choices=TYPE_CHOICES, default=TYPE_MCQ)
    text = models.TextField('Question Text')
    marks = models.PositiveIntegerField('Marks', default=1)
    order = models.PositiveIntegerField('Order', default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f'{self.exam.title} - Question {self.order}'


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField('Choice Text', max_length=500)
    is_correct = models.BooleanField('Correct Answer', default=False)

    class Meta:
        verbose_name = 'Choice'
        verbose_name_plural = 'Choices'

    def __str__(self):
        return self.text


class Attempt(models.Model):
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_GRADED = 'graded'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_SUBMITTED, 'Awaiting Grading'),
        (STATUS_GRADED, 'Graded'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    auto_score = models.FloatField(default=0)
    essay_score = models.FloatField(default=0)
    is_released = models.BooleanField(default=False)

    class Meta:
        unique_together = ('exam', 'student')
        verbose_name = 'Attempt'
        verbose_name_plural = 'Attempts'

    def __str__(self):
        return f'{self.student.username} - {self.exam.title}'

    @property
    def total_score(self):
        return self.auto_score + self.essay_score

    def deadline(self):
        return self.started_at + timedelta(minutes=self.exam.duration_minutes)

    def time_left_seconds(self):
        remaining = (self.deadline() - timezone.now()).total_seconds()
        return max(0, int(remaining))

    def is_time_up(self):
        return timezone.now() >= self.deadline()

    def grade_auto_and_finalize(self):
        """Auto-grade MCQ answers and move to the right status."""
        total = 0
        for answer in self.answers.select_related('question', 'selected_choice'):
            if answer.question.question_type == Question.TYPE_MCQ:
                if answer.selected_choice and answer.selected_choice.is_correct:
                    total += answer.question.marks
        self.auto_score = total
        self.submitted_at = timezone.now()
        if self.exam.has_essay_questions:
            self.status = self.STATUS_SUBMITTED
        else:
            self.status = self.STATUS_GRADED
        self.save()

    def grade_essays_and_finalize(self):
        total = 0
        for answer in self.answers.filter(question__question_type=Question.TYPE_ESSAY):
            total += answer.awarded_marks or 0
        self.essay_score = total
        self.status = self.STATUS_GRADED
        self.save()


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    essay_text = models.TextField('Student Answer', blank=True)
    awarded_marks = models.FloatField('Awarded Marks', null=True, blank=True)

    class Meta:
        unique_together = ('attempt', 'question')
        verbose_name = 'Answer'
        verbose_name_plural = 'Answers'

    def __str__(self):
        return f'{self.attempt} - {self.question}'
