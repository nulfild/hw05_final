import tempfile
import shutil

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import Client, override_settings, TestCase
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовая группа для теста'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_creating_post(self):
        """Новый пост добавляется в БД."""
        posts_count = Post.objects.count()

        form_data = {
            'text': 'Тестируем опять',
            'author': self.user
        }

        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестируем опять',
                author=self.user
            ).exists()
        )

    def test_editing_post(self):
        """Пост имзенется в БД при его редактировании."""
        form_data = {
            'text': 'Тестируем не опять, а снова',
            'author': self.user,
        }
        self.authorized_client.post(
            reverse('posts:post_edit', args=('1',)),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            Post.objects.get(pk=1).text, 'Тестируем не опять, а снова'
        )

    def test_creating_post_with_image(self):
        """Новый пост добавляется в БД."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост с картинкой',
            'author': self.user,
            'image': uploaded
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост с картинкой',
                author=self.user,
                image='posts/small.gif'
            ).exists()
        )

    def test_pages_show_correct_context_with_image(self):
        """Шаблоны страниц сформированы с правильным контекстом."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small2.gif',
            content=small_gif,
            content_type='image/gif'
        )
        Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестовый пост',
            image=uploaded,
        )
        reverses = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': 'auth'}),
            reverse('posts:group_list', kwargs={'slug': 'test_group'})
        ]
        for rev in reverses:
            with self.subTest(rev=rev):
                response = self.authorized_client.get(rev)
                self.assertEqual(response.context.get('page_obj')[0].image,
                                 'posts/small2.gif')

    def test_post_detail_correct_context(self):
        """Шаблоны страницы post_detail сформированы
            с правильным контекстом."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small3.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестовый пост',
            image=uploaded,
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post.pk})
        )
        self.assertEqual(response.context.get('post').image,
                         'posts/small3.gif')

    def test_adding_new_commnet(self):
        """После успешной отправки комментарий появляется на странице поста"""
        comments_count = Comment.objects.count()

        form_data = {
            'text': 'Добавляем тестовый комментарий',
        }

        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
        )

        self.assertEqual(Post.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='Добавляем тестовый комментарий',
                post=self.post,
                author=self.user,
            ).exists()
        )
