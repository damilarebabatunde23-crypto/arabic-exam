from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BulkMCQFormSet, ChoiceFormSet, ExamForm, QuestionForm
from .models import Answer, Attempt, Choice, Exam, Question


def _is_teacher(user):
    return user.is_authenticated and user.profile.is_teacher


teacher_required = user_passes_test(_is_teacher, login_url='accounts:login')


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------

@login_required
def exam_list(request):
    now = timezone.now()
    exams = Exam.objects.filter(is_active=True).order_by('start_time')
    attempts = {a.exam_id: a for a in Attempt.objects.filter(student=request.user)}

    rows = []
    for exam in exams:
        rows.append({
            'exam': exam,
            'attempt': attempts.get(exam.id),
            'is_open': exam.is_open(),
            'has_ended': exam.has_ended(),
        })

    return render(request, 'exams/exam_list.html', {'rows': rows, 'now': now})


@login_required
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, is_active=True)

    existing = Attempt.objects.filter(exam=exam, student=request.user).first()
    if existing:
        if existing.status == Attempt.STATUS_IN_PROGRESS and not existing.is_time_up():
            return redirect('exams:take_exam', attempt_id=existing.id)
        return redirect('exams:result', attempt_id=existing.id)

    if not exam.is_open():
        messages.error(request, 'This exam is not available right now.')
        return redirect('exams:exam_list')

    attempt = Attempt.objects.create(exam=exam, student=request.user)
    return redirect('exams:take_exam', attempt_id=attempt.id)


@login_required
def take_exam(request, attempt_id):
    attempt = get_object_or_404(Attempt, pk=attempt_id, student=request.user)

    if attempt.status != Attempt.STATUS_IN_PROGRESS:
        return redirect('exams:result', attempt_id=attempt.id)

    if attempt.is_time_up():
        attempt.grade_auto_and_finalize()
        messages.info(request, "Time's up — the exam was submitted automatically.")
        return redirect('exams:result', attempt_id=attempt.id)

    questions = attempt.exam.questions.prefetch_related('choices').all()

    if request.method == 'POST':
        with transaction.atomic():
            for question in questions:
                answer, _ = Answer.objects.get_or_create(attempt=attempt, question=question)
                if question.question_type == Question.TYPE_MCQ:
                    choice_id = request.POST.get(f'question_{question.id}')
                    answer.selected_choice = Choice.objects.filter(pk=choice_id, question=question).first() if choice_id else None
                else:
                    answer.essay_text = request.POST.get(f'question_{question.id}', '')
                answer.save()

            action = request.POST.get('action')
            if action == 'submit' or attempt.is_time_up():
                attempt.grade_auto_and_finalize()
                messages.success(request, 'Exam submitted successfully.')
                return redirect('exams:result', attempt_id=attempt.id)

        messages.success(request, 'Your answers have been saved.')
        return redirect('exams:take_exam', attempt_id=attempt.id)

    existing_answers = {a.question_id: a for a in attempt.answers.all()}

    return render(request, 'exams/take_exam.html', {
        'attempt': attempt,
        'exam': attempt.exam,
        'questions': questions,
        'existing_answers': existing_answers,
        'time_left_seconds': attempt.time_left_seconds(),
    })


@login_required
def result(request, attempt_id):
    attempt = get_object_or_404(Attempt, pk=attempt_id, student=request.user)
    answers = attempt.answers.select_related('question', 'selected_choice').order_by('question__order') if attempt.is_released else []
    return render(request, 'exams/result.html', {'attempt': attempt, 'answers': answers})


# ---------------------------------------------------------------------------
# Teacher views
# ---------------------------------------------------------------------------

@teacher_required
def teacher_dashboard(request):
    exams = Exam.objects.filter(created_by=request.user).order_by('-start_time')
    data = []
    total_attempts = 0
    total_pending = 0
    for exam in exams:
        attempts = exam.attempts.all()
        attempt_count = attempts.count()
        pending_count = attempts.filter(status=Attempt.STATUS_SUBMITTED).count()
        total_attempts += attempt_count
        total_pending += pending_count
        data.append({
            'exam': exam,
            'total_attempts': attempt_count,
            'pending_grading': pending_count,
        })
    return render(request, 'exams/teacher_dashboard.html', {
        'data': data,
        'total_attempts': total_attempts,
        'total_pending': total_pending,
    })


@teacher_required
def exam_create(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            messages.success(request, 'Exam created. Now add the questions.')
            return redirect('exams:question_list', exam_id=exam.id)
    else:
        form = ExamForm()
    return render(request, 'exams/exam_form.html', {'form': form, 'is_new': True})


@teacher_required
def exam_edit(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, created_by=request.user)
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam details updated.')
            return redirect('exams:teacher_dashboard')
    else:
        form = ExamForm(instance=exam)
    return render(request, 'exams/exam_form.html', {'form': form, 'is_new': False, 'exam': exam})


@teacher_required
def question_list(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, created_by=request.user)
    questions = exam.questions.prefetch_related('choices').all()
    return render(request, 'exams/question_list.html', {'exam': exam, 'questions': questions})


@teacher_required
def question_add(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, created_by=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()
            if question.question_type == Question.TYPE_MCQ:
                formset = ChoiceFormSet(request.POST, instance=question)
                if formset.is_valid():
                    formset.save()
            messages.success(request, 'Question added.')
            return redirect('exams:question_list', exam_id=exam.id)
        formset = ChoiceFormSet(request.POST)
    else:
        form = QuestionForm()
        formset = ChoiceFormSet()
    return render(request, 'exams/question_form.html', {'form': form, 'formset': formset, 'exam': exam})


@teacher_required
def bulk_add_questions(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, created_by=request.user)

    if request.method == 'POST':
        formset = BulkMCQFormSet(request.POST)
        if formset.is_valid():
            next_order = (exam.questions.aggregate(Max('order'))['order__max'] or 0) + 1
            created = 0
            with transaction.atomic():
                for form in formset:
                    if not form.cleaned_data or form.is_blank():
                        continue
                    question = Question.objects.create(
                        exam=exam,
                        question_type=Question.TYPE_MCQ,
                        text=form.cleaned_data['text'].strip(),
                        marks=form.cleaned_data.get('marks') or 1,
                        order=next_order,
                    )
                    next_order += 1
                    correct_idx = int(form.cleaned_data['correct'])
                    for i, choice_text in enumerate(form.choices(), start=1):
                        if choice_text:
                            Choice.objects.create(question=question, text=choice_text, is_correct=(i == correct_idx))
                    created += 1

            if created:
                messages.success(request, f'{created} question(s) added.')
                return redirect('exams:question_list', exam_id=exam.id)
            messages.info(request, 'No questions were added — fill in at least one question with 2 or more choices.')
    else:
        formset = BulkMCQFormSet()

    return render(request, 'exams/bulk_add_questions.html', {'formset': formset, 'exam': exam})


@teacher_required
def question_edit(request, question_id):
    question = get_object_or_404(Question, pk=question_id, exam__created_by=request.user)
    exam = question.exam
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        formset = ChoiceFormSet(request.POST, instance=question)
        if form.is_valid() and (question.question_type != Question.TYPE_MCQ or formset.is_valid()):
            form.save()
            if question.question_type == Question.TYPE_MCQ:
                formset.save()
            messages.success(request, 'Question updated.')
            return redirect('exams:question_list', exam_id=exam.id)
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)
    return render(request, 'exams/question_form.html', {'form': form, 'formset': formset, 'exam': exam, 'question': question})


@teacher_required
def question_delete(request, question_id):
    question = get_object_or_404(Question, pk=question_id, exam__created_by=request.user)
    exam_id = question.exam_id
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted.')
    return redirect('exams:question_list', exam_id=exam_id)


@teacher_required
def submissions_list(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, created_by=request.user)
    attempts = exam.attempts.select_related('student').order_by('student__username')
    return render(request, 'exams/submissions_list.html', {'exam': exam, 'attempts': attempts})


@teacher_required
def grade_attempt(request, attempt_id):
    attempt = get_object_or_404(Attempt, pk=attempt_id, exam__created_by=request.user)
    essay_answers = attempt.answers.filter(question__question_type=Question.TYPE_ESSAY).select_related('question')
    mcq_answers = attempt.answers.filter(question__question_type=Question.TYPE_MCQ).select_related('question', 'selected_choice')

    if request.method == 'POST':
        for answer in essay_answers:
            raw = request.POST.get(f'marks_{answer.id}', '').strip()
            max_marks = answer.question.marks
            if raw == '':
                answer.awarded_marks = None
            else:
                try:
                    value = float(raw)
                except ValueError:
                    value = 0
                answer.awarded_marks = max(0, min(value, max_marks))
            answer.save()
        attempt.grade_essays_and_finalize()
        messages.success(request, 'Grades saved.')
        return redirect('exams:submissions_list', exam_id=attempt.exam_id)

    return render(request, 'exams/grade_attempt.html', {
        'attempt': attempt,
        'essay_answers': essay_answers,
        'mcq_answers': mcq_answers,
    })


@teacher_required
def release_results(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, created_by=request.user)
    if request.method == 'POST':
        updated = exam.attempts.filter(status=Attempt.STATUS_GRADED).update(is_released=True)
        messages.success(request, f'Results published for {updated} student(s).')
    return redirect('exams:submissions_list', exam_id=exam.id)
