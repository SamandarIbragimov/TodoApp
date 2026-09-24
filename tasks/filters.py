import django_filters

from .models import Task


class TaskFilter(django_filters.FilterSet):
    due_date_from = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_date_to = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')
    personal = django_filters.BooleanFilter(
        field_name='project', lookup_expr='isnull', label='Faqat shaxsiy tasklar'
    )
    mine = django_filters.BooleanFilter(method='filter_mine', label='Menga tayinlangan')

    class Meta:
        model = Task
        fields = ('status', 'priority', 'due_date', 'project', 'assigned_to', 'tags')

    def filter_mine(self, queryset, name, value):
        user = self.request.user
        return queryset.filter(assigned_to=user) if value else queryset.exclude(assigned_to=user)
