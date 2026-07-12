from django import forms
from django.forms import formset_factory, inlineformset_factory

from .models import Choice, Exam, Question


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'description', 'duration_minutes', 'start_time', 'end_time', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError('End time must be after the start time.')
        return cleaned


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_type', 'text', 'marks', 'order']
        widgets = {
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    fields=['text', 'is_correct'],
    widgets={
        'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice text'}),
        'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    },
    extra=4,
    max_num=6,
    can_delete=True,
)


class BulkMCQQuestionForm(forms.Form):
    """One row in the bulk multiple-choice question builder. All fields are
    optional so unused rows in the formset are simply skipped."""

    text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Question text'}),
    )
    marks = forms.IntegerField(
        required=False, min_value=1, initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    choice_1 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice 1'}))
    choice_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice 2'}))
    choice_3 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice 3 (optional)'}))
    choice_4 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice 4 (optional)'}))
    correct = forms.ChoiceField(
        required=False,
        choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')],
        widget=forms.RadioSelect,
    )

    def choices(self):
        return [(self.cleaned_data.get(f'choice_{i}') or '').strip() for i in range(1, 5)]

    def is_blank(self):
        text = (self.cleaned_data.get('text') or '').strip()
        return not text and not any(self.choices())

    def clean(self):
        cleaned = super().clean()
        text = (cleaned.get('text') or '').strip()
        choice_values = [(cleaned.get(f'choice_{i}') or '').strip() for i in range(1, 5)]

        if not text and not any(choice_values):
            return cleaned

        if not text:
            raise forms.ValidationError('Question text is required.')

        filled = [c for c in choice_values if c]
        if len(filled) < 2:
            raise forms.ValidationError('Provide at least 2 choices.')

        correct = cleaned.get('correct')
        if not correct:
            raise forms.ValidationError('Select the correct choice.')
        if not choice_values[int(correct) - 1]:
            raise forms.ValidationError('The choice marked correct must have text.')

        return cleaned


BulkMCQFormSet = formset_factory(BulkMCQQuestionForm, extra=10, max_num=20, validate_max=True)
