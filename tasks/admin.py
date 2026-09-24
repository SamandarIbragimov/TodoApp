from django.contrib import admin

from .models import Comment, Tag, Task


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'due_date', 'created_by', 'assigned_to')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description')
    filter_horizontal = ('tags',)
    inlines = [CommentInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'user')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'created_at')
