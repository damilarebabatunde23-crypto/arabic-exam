from django.contrib import admin

from .models import Answer, Attempt, Choice, Exam, Question


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'start_time', 'end_time', 'is_active']
    list_filter = ['is_active']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question_type', 'marks', 'order']
    inlines = [ChoiceInline]


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'status', 'auto_score', 'essay_score', 'is_released']
    list_filter = ['status', 'is_released', 'exam']


admin.site.register(Answer)
