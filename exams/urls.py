from django.urls import path

from . import views

app_name = 'exams'

urlpatterns = [
    # Student
    path('', views.exam_list, name='exam_list'),
    path('<int:exam_id>/start/', views.start_exam, name='start_exam'),
    path('attempt/<int:attempt_id>/take/', views.take_exam, name='take_exam'),
    path('attempt/<int:attempt_id>/result/', views.result, name='result'),

    # Teacher
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/exams/create/', views.exam_create, name='exam_create'),
    path('teacher/exams/<int:exam_id>/edit/', views.exam_edit, name='exam_edit'),
    path('teacher/exams/<int:exam_id>/questions/', views.question_list, name='question_list'),
    path('teacher/exams/<int:exam_id>/questions/add/', views.question_add, name='question_add'),
    path('teacher/exams/<int:exam_id>/questions/bulk-add/', views.bulk_add_questions, name='bulk_add_questions'),
    path('teacher/questions/<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('teacher/questions/<int:question_id>/delete/', views.question_delete, name='question_delete'),
    path('teacher/exams/<int:exam_id>/submissions/', views.submissions_list, name='submissions_list'),
    path('teacher/attempts/<int:attempt_id>/grade/', views.grade_attempt, name='grade_attempt'),
    path('teacher/exams/<int:exam_id>/release/', views.release_results, name='release_results'),
]
