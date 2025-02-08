import csv

import io
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from firebase_admin import db
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from . import serializers, paginators
from .models import Category, Activity, Participation, DisciplinePoint, Report, User, Comment, NewsFeed,Like,Message,Registration,EvaluationGroup, EvaluationCriteria,Department, Class
from scores import perms

class CategoryViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    pagination_class = paginators.ItemPaginator

class ActivityViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = Activity.objects.prefetch_related('tags').filter(active=True)
    serializer_class = serializers.ActivityDetailsSerializer
    pagination_class = paginators.ItemPaginator
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.queryset

        category_id = self.request.query_params.get('category_id')
        if category_id:
            query = query.filter(category_id=category_id)

        search_keyword = self.request.query_params.get('q')
        if search_keyword:
            query = query.filter(title__icontains=search_keyword)

        tag_name = self.request.query_params.get('tag')
        if tag_name:
            query = query.filter(tags__name=tag_name)

        return query

    @action(methods=['get'], url_path='participations', detail=True)
    def get_participations(self, request, pk):
        activity = self.get_object().participation_set.filter(active=True)
        return Response(serializers.ParticipationSerializer(activity, many=True, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        activity = self.get_object()

        if not perms.DestroyActivityPerms().has_object_permission(request, self, activity):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        activity.delete()
        return Response({'message': 'Activity deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        activity = self.get_object()
        serializer = self.serializer_class(activity, context={'request': request})
        return Response(serializer.data)


class ParticipationViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Participation.objects.filter(active=True)
    serializer_class = serializers.ParticipationSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = paginators.ItemPaginator

    @action(methods=['post'], url_path='complete', detail=True)
    def mark_complete(self, request, pk):
        participation = self.get_object()
        participation.is_completed = True
        participation.save()

        return Response(serializers.ParticipationSerializer(participation).data)

    @action(methods=['get'], url_path='student-history', detail=False,permission_classes=[permissions.IsAuthenticated])
    def student_participation_history(self, request):
        participations = Participation.objects.filter(student=request.user, active=True)
        return Response(serializers.ParticipationSerializer(participations, many=True).data)

    @action(methods=['post'], url_path='upload-csv', detail=False, permission_classes=[permissions.IsAdminUser])
    def upload_csv(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = file.read().decode('utf-8-sig')
            csv_file = io.StringIO(decoded_file)
            reader = csv.DictReader(csv_file)

            for row in reader:
                try:
                    # Xử lý Student ID
                    student_id_str = row['Student ID'].strip().replace('\ufeff', '').strip()
                    if not student_id_str.isdigit():
                        raise ValueError(f"Invalid Student ID: {student_id_str}")
                    student_id = int(student_id_str)
                    student = User.objects.get(id=student_id)

                    # Xử lý Activity ID
                    activity_id_str = row['Activity ID'].strip()
                    if not activity_id_str.isdigit():
                        raise ValueError(f"Invalid Activity ID: {activity_id_str}")
                    activity_id = int(activity_id_str)
                    activity = Activity.objects.get(id=activity_id)

                    # Kiểm tra tiêu chí đánh giá
                    criteria = EvaluationCriteria.objects.filter(activity=activity).first()
                    if not criteria:
                        raise ValueError(f"No valid criteria found for activity {activity_id}")

                    # Kiểm tra đăng ký hoạt động
                    registration = Registration.objects.filter(student=student, activity=activity).first()
                    if not registration:
                        raise ValueError(f"Student {student_id} is not registered for activity {activity_id}")

                    # Xử lý Attendance: Nếu khác null, đánh dấu hoàn thành
                    attendance = row.get('Attendance', '').strip().lower()
                    is_completed = bool(attendance)  # Nếu attendance khác rỗng thì là True

                    participation, created = Participation.objects.get_or_create(student=student, activity=activity)
                    participation.is_completed = is_completed
                    participation.save()

                    # Xử lý điểm kỷ luật
                    discipline_point = DisciplinePoint.objects.filter(student=student, activity=activity).first()
                    if discipline_point:
                        discipline_point.score = float(row.get('Score', 0))
                        discipline_point.criteria = criteria
                        discipline_point.save()
                    else:
                        discipline_point = DisciplinePoint(
                            student=student, activity=activity,
                            score=float(row.get('Score', 0)), criteria=criteria
                        )
                        discipline_point.save()

                except Exception as e:
                    return Response({"detail": f"Error processing row: {row} - {str(e)}"},
                                    status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "CSV processed successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class EvaluationGroupViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = EvaluationGroup.objects.all()
    serializer_class = serializers.EvaluationGroupSerializer
    permission_classes = [perms.IsAdminOrReadOnly]

class EvaluationCriteriaViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = EvaluationCriteria.objects.all()
    serializer_class = serializers.EvaluationCriteriaSerializer
    permission_classes = [perms.IsAdminOrReadOnly]

class DisciplinePointViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = DisciplinePoint.objects.all()
    serializer_class = serializers.DisciplinePointSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = paginators.ItemPaginator

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        query = self.queryset
        if self.request.user.is_superuser:
            return query

        if self.request.user.is_staff:
            student_id = self.request.query_params.get('student_id')
            if student_id:
                query = query.filter(student_id=student_id)

        if not self.request.user.is_staff and not self.request.user.is_superuser:
            query = query.filter(student=self.request.user)

        return query

class ReportViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    serializer_class = serializers.ReportSerializer
    pagination_class = paginators.ItemPaginator

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Report.objects.filter(active=True)
        return Report.objects.filter(active=True, student=self.request.user)

    def perform_create(self, serializer):
        activity_id = self.request.data.get('activity_id')
        activity = Activity.objects.get(id=activity_id)
        serializer.save(student=self.request.user, activity=activity)


    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]

        return [permissions.IsAdminUser()]

    @action(methods=['patch'], url_path='approve', detail=True)
    def approve_report(self, request, pk):
        report = self.get_object()
        report.status = 'approved'
        report.handled_by = request.user
        report.save()
        return Response(serializers.ReportSerializer(report).data)

    @action(methods=['patch'], url_path='reject', detail=True)
    def reject_report(self, request, pk):
        report = self.get_object()
        report.status = 'rejected'
        report.handled_by = request.user
        report.save()
        return Response(serializers.ReportSerializer(report).data)

class ClassViewSet(viewsets.ViewSet,generics.ListAPIView):
    queryset = Class.objects.all()
    serializer_class = serializers.ClassSerializer

class DepartmentViewSet(viewsets.ViewSet):
    @action(methods=['get'], detail=False, url_path='list')
    def list_departments(self, request):
        # Lấy tất cả phòng ban
        departments = Department.objects.all()
        department_data = [{'id': department.id, 'name': department.name} for department in departments]
        return Response(department_data, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    pagination_class = paginators.ItemPaginator

    @action(methods=['get'], detail=False, url_path='staff-by-department')
    def list_staff_by_department(self, request):
        department_id = request.query_params.get('department_id')
        if not department_id:
            return Response({'error': 'department_id là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            department = Department.objects.get(id=department_id)

            assistants = User.objects.filter(role='staff', department=department)

            assistant_data = [{'id': assistant.id, 'username': assistant.username} for assistant in assistants]
            return Response(assistant_data, status=status.HTTP_200_OK)

        except Department.DoesNotExist:
            return Response({'error': 'Không tìm thấy phòng ban.'}, status=status.HTTP_404_NOT_FOUND)

    @action(methods=['get'], url_path='current-user', detail=False, permission_classes=[permissions.IsAuthenticated])
    def get_current_user(self, request):
        serializer = serializers.UserSerializer(request.user,context={'request': request})  # Truyền request vào context
        return Response(serializer.data)

    @action(methods=['post'], url_path='change-password', detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        serializer = serializers.ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], url_path='create-staff', detail=False,
            permission_classes=[permissions.IsAdminUser])
    def create_staff(self, request):
        data = request.data
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_staff = True  # Đánh dấu quyền trợ lý sinh viên
            user.save()
            return Response({"message": "Staff account created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False, url_path='students', permission_classes=[permissions.IsAdminUser])
    def list_students(self, request):
        students = User.objects.filter(role='student')
        serializer = self.serializer_class(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class NewsFeedViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = NewsFeed.objects.filter(active=True)
    serializer_class = serializers.NewsFeedSerializer
    pagination_class = paginators.ItemPaginator
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_permissions(self):
        if self.action == 'list':
            return [permissions.AllowAny()]

        if self.action == 'create':
            return [permissions.IsAdminUser()]

        if self.action in ['get_comments', 'get_likes', 'likes_count', 'comments_count']:
            if self.request.method == 'POST':
                return [permissions.IsAuthenticated()]
            return [permissions.AllowAny()]

        return super().get_permissions()

    @action(methods=['get'], detail=True, url_path='likes-count')
    def likes_count(self, request, pk):
        newsfeed = self.get_object()
        count = newsfeed.like_set.count()
        return Response({'likes_count': count}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True, url_path='comments-count')
    def comments_count(self, request, pk):
        newsfeed = self.get_object()
        count = newsfeed.comment_set.count()
        return Response({'comments_count': count}, status=status.HTTP_200_OK)

    @action(methods=['get', 'post'], url_path='comments', detail=True)
    def get_comments(self, request, pk):
        if request.method.__eq__('POST'):
            content = request.data.get('content')
            c = Comment.objects.create(content=content, user=request.user, newsfeed=self.get_object())

            return Response(serializers.CommentSerializer(c).data)
        else:
            comments = self.get_object().comment_set.select_related('user').filter(active=True)
            return Response(serializers.CommentSerializer(comments, many=True).data)

    @action(methods=['get', 'post'], url_path='likes', detail=True)
    def get_likes(self, request, pk):
        newsfeed = self.get_object()

        if request.method.__eq__('GET'):
            likes = newsfeed.like_set.select_related('user')
            serializer = serializers.UserSerializer([like.user for like in likes], many=True)
            return Response(serializer.data)

        if request.method.__eq__('POST'):
            like, created = Like.objects.get_or_create(user=request.user, newsfeed=newsfeed)
            if not created:
                like.delete()
                return Response({'message': 'Unliked successfully.'}, status=status.HTTP_200_OK)

            return Response({'message': 'Liked successfully.'}, status=status.HTTP_201_CREATED)

class RegistrationViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = Registration.objects.filter(active=True)
    serializer_class = serializers.RegistrationSerializer
    pagination_class = paginators.ItemPaginator
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(methods=['get'], url_path='list', detail=False, permission_classes=[permissions.IsAdminUser])
    def get_list(self, request, activity_id=None):
        activity_id = request.query_params.get('activity_id')
        if activity_id:
            try:
                activity = Activity.objects.get(id=activity_id)
            except Activity.DoesNotExist:
                return Response({"detail": "Activity not found."}, status=404)

            registrations = Registration.objects.filter(activity=activity)
        else:
            registrations = Registration.objects.all()

        serializer = serializers.RegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    @action(methods=['get'], url_path='export-csv', detail=False, permission_classes=[permissions.IsAdminUser])
    def export_csv(self, request, activity_id=None):
        activity_id = request.query_params.get('activity_id')
        if not activity_id:
            return Response({"detail": "Activity ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            activity = Activity.objects.get(id=activity_id)
        except Activity.DoesNotExist:
            return Response({"detail": "Activity not found."}, status=status.HTTP_404_NOT_FOUND)

        registrations = Registration.objects.filter(activity=activity)

        response = HttpResponse(content_type='text/csv', charset='utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="registrations_{activity_id}.csv"'

        writer = csv.writer(response)

        writer.writerow(['Student ID', 'Student Name', 'Activity ID', 'Activity Title', 'Attendance','Score'])

        for registration in registrations:
            student_name = f"{registration.student.first_name} {registration.student.last_name}"

            writer.writerow(
                [registration.student.id, student_name, activity.id, activity.title, ''])

        return response

class CommentViewSet(viewsets.ViewSet, generics.DestroyAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = serializers.CommentSerializer
    permission_classes = [perms.OwnerPerms]
    pagination_class = paginators.ItemPaginator

class MessageViewSet(viewsets.ViewSet):
    queryset = Message.objects.all()
    serializer_class = serializers.MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=['get'], detail=False, url_path='list')
    def list_messages(self, request):
        user = request.user
        receiver_id = request.query_params.get('receiver_id')  # Đổi 'staff_id' thành 'receiver_id'

        if not receiver_id:
            return Response({'error': 'receiver_id là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver = User.objects.get(id=receiver_id)  # Không giới hạn role
        except User.DoesNotExist:
            return Response({'error': 'Không tìm thấy người nhận.'}, status=status.HTTP_404_NOT_FOUND)

        queryset = Message.objects.filter(
            (Q(sender=user) & Q(receiver=receiver)) | (Q(sender=receiver) & Q(receiver=user))
        ).order_by('-timestamp')

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='create')
    def create_message(self, request):
        sender = request.user
        receiver_id = request.data.get('receiver_id')
        content = request.data.get('content')

        if not receiver_id or not content:
            return Response({'error': 'receiver_id và content là bắt buộc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receiver = User.objects.get(id=receiver_id)

            message = Message.objects.create(sender=sender, receiver=receiver, content=content)

            ref = db.reference('messages')
            firebase_message = ref.push({
                'sender': sender.username,
                'receiver': receiver.username,
                'content': content,
                'timestamp': str(message.timestamp)
            })

            message.firebase_id = firebase_message.key
            message.save()

            return Response({'success': True, 'message': 'Tin nhắn đã được tạo thành công.'}, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response({'error': 'Không tìm thấy người nhận.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': 'Đã xảy ra lỗi khi tạo tin nhắn.', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['get'], detail=True, url_path='detail')
    def get_message_detail(self, request, pk=None):
        user = request.user
        try:
            message = Message.objects.get(Q(pk=pk) & (Q(sender=user) | Q(receiver=user)))
            serializer = self.serializer_class(message)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Message.DoesNotExist:
            return Response({'error': 'Không tìm thấy tin nhắn hoặc bạn không có quyền truy cập.'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(methods=['get'], detail=False, url_path='get-sent-students', permission_classes=[permissions.IsAdminUser])
    def get_sent_students(self, request):
        user = request.user

        students = Message.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).values('sender', 'receiver')

        participant_ids = set()
        for student in students:
            participant_ids.add(student['sender'])
            participant_ids.add(student['receiver'])

        student_list = User.objects.filter(id__in=participant_ids, role='student')

        if not student_list.exists():
            return Response({'error': 'Không tìm thấy sinh viên nào đã nhắn tin với bạn.'},
                            status=status.HTTP_404_NOT_FOUND)

        students_serializer = serializers.UserSerializer(student_list, many=True)
        return Response(students_serializer.data, status=status.HTTP_200_OK)

class ScoreStatsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(methods=['get'], detail=False)
    def get(self, request):
        selected_class_id = request.GET.get('class')

        if selected_class_id:
            stats_by_class = (
                User.objects.filter(student_class__id=selected_class_id)
                .values('student_class__name')
                .annotate(
                    total_score=Sum('total_score'),
                    student_count=Count('id')
                )
            )

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
            stats_by_class = (
                User.objects.values('student_class__name')
                .annotate(
                    total_score=Sum('total_score'),
                    student_count=Count('id')
                )
            )

            for stat in stats_by_class:
                stat['avg_score'] = round(stat['total_score'] / stat['student_count'], 2) if stat[
                                                                                                 'student_count'] > 0 else 0

            classification = (
                User.objects.values('student_class__name')
                .annotate(
                    excellent=Count('total_score', filter=Q(total_score__gte=90)),
                    good=Count('total_score', filter=Q(total_score__gte=75, total_score__lt=90)),
                    average=Count('total_score', filter=Q(total_score__gte=50, total_score__lt=75)),
                    poor=Count('total_score', filter=Q(total_score__lt=50)),
                )
            )

        return Response({
            "stats_by_class": list(stats_by_class),
            "classification": list(classification)
        })

class ExportCSVViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(methods=['get'], detail=False, url_path="download")  # Đổi thành @action để hiển thị API
    def download_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_scores.csv"'

        writer = csv.writer(response)
        writer.writerow(['Student', 'Class', 'Department', 'Score', 'Classification'])

        users = User.objects.select_related('student_class', 'department')
        for user in users:
            classification = (
                "Excellent" if user.total_score >= 90 else
                "Good" if user.total_score >= 75 else
                "Average" if user.total_score >= 50 else
                "Poor"
            )
            writer.writerow([
                user.username,
                user.student_class.name if user.student_class else "N/A",
                user.department.name if user.department else "N/A",
                user.total_score,
                classification
            ])

        return response

class ExportPDFViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(methods=['get'], detail=False, url_path="download")  # Thêm action để gọi API dễ dàng hơn
    def download_pdf(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="user_scores.pdf"'

        pdf_canvas = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        pdf_canvas.setFont("Helvetica-Bold", 16)
        pdf_canvas.drawString(200, height - 50, "Danh sách Điểm số Sinh viên")

        data = [["Tên sinh viên", "Lớp", "Khoa", "Điểm số", "Xếp loại"]]

        users = User.objects.select_related('student_class', 'department')
        for user in users:
            classification = (
                "Xuất sắc" if user.total_score >= 90 else
                "Giỏi" if user.total_score >= 75 else
                "Khá" if user.total_score >= 50 else
                "Yếu"
            )
            data.append([
                user.username,
                user.student_class.name if user.student_class else "N/A",
                user.department.name if user.department else "N/A",
                str(user.total_score),
                classification
            ])

        table = Table(data, colWidths=[100, 80, 100, 60, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        table.wrapOn(pdf_canvas, width, height)
        table.drawOn(pdf_canvas, 50, height - 100 - (len(data) * 20))

        pdf_canvas.save()
        return response
