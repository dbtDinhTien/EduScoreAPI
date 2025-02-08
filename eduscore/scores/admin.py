from django.contrib import admin
from django.db.models import Count, Sum, Avg,Q
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from scores.models import *
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.urls import path
from django.http import HttpResponse
import csv
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

class MyScoreAdmin(admin.AdminSite):
    site_header = 'Edu Scores'
    site_title = "EduScore Admin"
    index_title = "Welcome to EduScore Admin"

    def get_urls(self):
        return [
            path('score-stats/', self.stats),
            path('export-csv/', self.export_csv),
            path('export-pdf/', self.export_pdf),
        ] + super().get_urls()

    def stats(self, request):
        all_classes = Class.objects.all()

        selected_class_id = request.GET.get('class')
        if selected_class_id:
            # Lấy thống kê điểm từ User theo lớp
            stats_by_class = (
                User.objects.filter(student_class__id=selected_class_id)
                .values('student_class__name')
                .annotate(
                    total_score=Sum('total_score'),
                    student_count=Count('id')
                )
            )

            # Tính điểm trung bình
            for stat in stats_by_class:
                stat['avg_score'] = stat['total_score'] / stat['student_count'] if stat['student_count'] > 0 else 0

            classification = (
                User.objects.filter(student_class__id=selected_class_id)
                .values('student_class__name')
                .annotate(
                    excellent=Count('total_score', filter=Q(total_score__gte=90)),
                    good=Count('total_score', filter=Q(total_score__gte=75, total_score__lt=90)),
                    average=Count('total_score', filter=Q(total_score__gte=50, total_score__lt=75)),
                    poor=Count('total_score', filter=Q(total_score__lt=50)),
                )
            )
        else:
            # Lấy thống kê điểm từ User cho tất cả các lớp
            stats_by_class = (
                User.objects.values('student_class__name')
                .annotate(
                    total_score=Sum('total_score'),
                    student_count=Count('id')
                )
            )

            # Tính điểm trung bình
            for stat in stats_by_class:
                stat['avg_score'] = round(stat['total_score'] / stat['student_count'], 2) if stat['student_count'] > 0 else 0
            classification = (
                User.objects.values('student_class__name')
                .annotate(
                    excellent=Count('total_score', filter=Q(total_score__gte=90)),
                    good=Count('total_score', filter=Q(total_score__gte=75, total_score__lt=90)),
                    average=Count('total_score', filter=Q(total_score__gte=50, total_score__lt=75)),
                    poor=Count('total_score', filter=Q(total_score__lt=50)),
                )
            )

        context = {
            'all_classes': all_classes,
            'selected_class_id': int(selected_class_id) if selected_class_id else None,
            'stats_by_class': stats_by_class,
            'classification': classification,
        }

        return TemplateResponse(request, 'admin/stats.html', context)

    def export_csv(self, request):
        # Xuất danh sách chi tiết dưới dạng CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_scores.csv"'

        writer = csv.writer(response)
        writer.writerow(['Student', 'Class', 'Department', 'Score', 'Classification'])

        users = User.objects.select_related('student_class', 'department')
        for user in users:
            if user.total_score >= 90:
                classification = 'Xuất Sắc'
            elif user.total_score >= 75:
                classification = 'Giỏi'
            elif user.total_score >= 50:
                classification = 'Khá'
            else:
                classification = 'Trung Bình'

            writer.writerow([
                user.username,
                user.student_class.code if user.student_class else '',
                user.department.code if user.department else '',
                user.total_score,
                classification,
            ])

        return response

    def export_pdf(self, request):
        # Xuất danh sách chi tiết dưới dạng PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="user_scores.pdf"'

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # Tiêu đề
        p.setFont("Helvetica-Bold", 16)
        p.drawString(200, 800, "User Scores Report")
        p.setFont("Helvetica", 12)

        # Kích thước và vị trí của bảng
        table_top = 750
        row_height = 20
        col_widths = [100, 80, 80, 80, 100]  # Chiều rộng các cột
        x_position = 50  # Vị trí bắt đầu vẽ bảng

        # Kẻ tiêu đề của bảng
        headers = ['Student', 'Class', 'Department', 'Score', 'Classification']
        for col_idx, header in enumerate(headers):
            p.drawString(x_position + sum(col_widths[:col_idx]), table_top, header)

        # Kẻ đường kẻ dưới tiêu đề
        p.line(x_position, table_top - 2, x_position + sum(col_widths), table_top - 2)

        # Dữ liệu sinh viên
        y = table_top - row_height
        users = User.objects.select_related('student_class', 'department')

        for user in users:
            # Xác định xếp loại của sinh viên
            if user.total_score >= 90:
                classification = 'Xuất Sắc'
            elif user.total_score >= 75:
                classification = 'Giỏi'
            elif user.total_score >= 50:
                classification = 'Khá'
            else:
                classification = 'Trung Bình'

            if y < 50:  # Tạo trang mới nếu hết chỗ
                p.showPage()
                y = 750
                # Vẽ lại tiêu đề và các đường kẻ
                for col_idx, header in enumerate(headers):
                    p.drawString(x_position + sum(col_widths[:col_idx]), y, header)
                p.line(x_position, y - 2, x_position + sum(col_widths), y - 2)
                y -= row_height

            # Vẽ các giá trị vào bảng
            p.drawString(x_position, y, user.username)
            p.drawString(x_position + col_widths[0], y, user.student_class.code if user.student_class else '')
            p.drawString(x_position + col_widths[0] + col_widths[1], y, user.department.code if user.department else '')
            p.drawString(x_position + col_widths[0] + col_widths[1] + col_widths[2], y, str(user.total_score))
            p.drawString(x_position + col_widths[0] + col_widths[1] + col_widths[2] + col_widths[3], y, classification)

            # Kẻ đường kẻ cho mỗi hàng
            p.line(x_position, y - 2, x_position + sum(col_widths), y - 2)

            y -= row_height

        # Kẻ đường kẻ dưới cùng bảng
        p.line(x_position, y - 2, x_position + sum(col_widths), y - 2)

        p.save()
        buffer.seek(0)
        response.write(buffer.getvalue())
        buffer.close()
        return response

class BaseAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('/static/css/styles.css',)
        }

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser')
    ordering = ('username',)

    def save_model(self, request, obj, form, change):
        if 'password' in form.changed_data:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)


class ActivityForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Activity
        fields = '__all__'

class ActivityAdmin(BaseAdmin):
    list_display = ('title', 'start_date', 'end_date', 'status', 'created_by')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description')
    ordering = ('start_date',)
    form=ActivityForm
    readonly_fields = ['IMAGE']

    def IMAGE(self, activity):
        if activity.image:
            return mark_safe(f"<img src='/media/{activity.image.name}' width='120'/>")
        return "No image"

class ParticipationAdmin(BaseAdmin):
    list_display = ('student', 'activity', 'is_completed')
    list_filter = ('is_completed', 'activity')
    readonly_fields = ['image']

    def image(self, participation):
        if participation.proof:
            return mark_safe(f"<img src='/media/{participation.proof.name}' width='120'/>")
        return "No image"

class EvaluationCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'score', 'active', 'created_date')
    list_filter = ('group', 'active', 'created_date')
    search_fields = ('name', 'group__name')
    ordering = ('group', 'name')
    list_editable = ('score', 'active')

class EvaluationGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_score', 'active', 'created_date')
    search_fields = ('name',)
    list_editable = ('max_score', 'active')

class DisciplinePointAdmin(BaseAdmin):
    list_display = ('student', 'criteria', 'score', 'group_total_score')
    list_filter = ('student',)
    readonly_fields = ('group_total_score',)
    def save_model(self, request, obj, form, change):
        obj.save()

class ReportAdmin(BaseAdmin):
    list_display = ('student', 'activity', 'status', 'handled_by')
    list_filter = ('status', 'activity', 'student')
    search_fields = ('student__username', 'activity__title')

    def image(self, report):
        if report.proof:
            return mark_safe(f"<img src='/static/{report.proof.name}' width='120'/>")
        return "No image"

class NewsFeedAdmin(BaseAdmin):
    list_display = ('activity', 'created_by', 'timestamp')
    search_fields = ('activity__title',)
    list_filter = ('created_date',)

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'activity', 'timestamp')
    search_fields = ('student__username', 'activity__title')
    list_filter = ('activity', 'timestamp')

class LikeAdmin(BaseAdmin):
    list_display = ('user', 'newsfeed')

class CommentAdmin(BaseAdmin):
    list_display = ('user', 'newsfeed', 'content')
    search_fields = ('content',)

class MessageAdmin(BaseAdmin):
    list_display = ('sender', 'receiver', 'content', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    list_filter = ('sender', 'receiver')

admin_site=MyScoreAdmin(name='EduScore')

admin_site.register(User, UserAdmin)
admin_site.register(Department)
admin_site.register(Class)
admin_site.register(Category)
admin_site.register(Activity, ActivityAdmin)
admin_site.register(Participation, ParticipationAdmin)
admin_site.register(EvaluationCriteria, EvaluationCriteriaAdmin)
admin_site.register(EvaluationGroup, EvaluationGroupAdmin)
admin_site.register(DisciplinePoint, DisciplinePointAdmin)
admin_site.register(Report, ReportAdmin)
admin_site.register(NewsFeed, NewsFeedAdmin)
admin_site.register(Registration, RegistrationAdmin)
admin_site.register(Like, LikeAdmin)
admin_site.register(Comment, CommentAdmin)
admin_site.register(Message, MessageAdmin)
admin_site.register(Tag)