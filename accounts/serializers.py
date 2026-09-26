from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

MAX_AVATAR_SIZE = 2 * 1024 * 1024


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Parolni takrorlang')

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2')
        extra_kwargs = {'email': {'required': True, 'allow_blank': False}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Bu email bilan allaqachon ro'yxatdan o'tilgan.")
        return value.lower()

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'Parollar mos kelmadi.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(source='profile.avatar', required=False, allow_null=True)
    created_at = serializers.DateTimeField(source='profile.created_at', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'avatar', 'created_at')
        read_only_fields = ('username',)

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email bo'sh bo'lishi mumkin emas.")
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('Bu email boshqa foydalanuvchida bor.')
        return value.lower()

    def validate_avatar(self, value):
        if value and value.size > MAX_AVATAR_SIZE:
            raise serializers.ValidationError('Rasm hajmi 2 MB dan oshmasligi kerak.')
        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        instance = super().update(instance, validated_data)
        if 'avatar' in profile_data:
            instance.profile.avatar = profile_data['avatar']
            instance.profile.save()
        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(help_text='Username yoki email')
    password = serializers.CharField(style={'input_type': 'password'})
