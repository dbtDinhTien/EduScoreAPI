from rest_framework import serializers
from .models import *
from django.contrib.auth.password_validation import validate_password

class BaseSerializer (serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='image')

    def get_image(self, activity):
        if activity.image:
            if activity.image.name.startswith("http"):
                return activity.image.name

            request = self.context.get('request')
            if request:
                return request.build_absolute_uri('/media/%s' % activity.image.name)
        return None

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class UserSerializer(BaseSerializer):
    image = serializers.ImageField(required=False)
    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()
        return u

    class Meta:
        model = User
        fields = ['id', 'username','password', 'first_name', 'last_name','image','role','total_score']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

class ActivitySerializer(BaseSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'created_by', 'capacity', 'status', 'category','image','tags','max_score']

class ActivityDetailsSerializer(ActivitySerializer):
    tags = TagSerializer(many=True, required=False)
    image = serializers.ImageField(required=False)
    class Meta:
        model = ActivitySerializer.Meta.model
        fields = ActivitySerializer.Meta.fields + ['title', 'tags']

class ParticipationSerializer(BaseSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = Participation
        fields = ['id', 'student', 'activity', 'is_completed', 'image']

class EvaluationCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCriteria
        fields = ['id', 'group', 'name', 'score']

class EvaluationGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationGroup
        fields = ['id', 'name', 'max_score']

class DisciplinePointSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    activity = ActivitySerializer(read_only=True)
    criteria = EvaluationCriteriaSerializer(read_only=True)
    class Meta:
        model = DisciplinePoint
        fields = ['id', 'student','activity', 'criteria', 'score', 'group_total_score']

    def create(self, validated_data):
        instance = DisciplinePoint(**validated_data)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ReportSerializer(BaseSerializer):
    activity_id = serializers.IntegerField(write_only=True)
    activity = ActivitySerializer(read_only=True)
    image = serializers.ImageField(required=False)
    class Meta:
        model = Report
        fields = ['id', 'activity', 'activity_id', 'image', 'status', 'handled_by']
        read_only_fields = ['student']

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ['student', 'activity', 'timestamp']
        read_only_fields = ['student']

class NewsFeedSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(read_only=True)
    class Meta:
        model = NewsFeed
        fields = ['id', 'activity', 'created_date']
        read_only_fields = ['created_by']

class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    newsfeed = NewsFeedSerializer()

    class Meta:
        model = Like
        fields = ['id', 'user', 'newsfeed']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'user', 'newsfeed', 'content', 'created_date']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "New passwords didn't match."})
        if attrs['new_password'] == attrs['old_password']:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the old password."})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'content', 'timestamp', 'firebase_id']
        read_only_fields = ['timestamp', 'firebase_id']

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['id', 'name', 'code', 'department']