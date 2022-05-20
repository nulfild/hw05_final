from http import HTTPStatus
from django.test import TestCase, Client

from ..models import Follow, Post, Group, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовая группа для теста'
        )
        Post.objects.create(
            text='Тестовый пост',
            author=cls.user_author,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_of_post = Client()
        self.author_of_post.force_login(self.user_author)

    def test_urls_available_for_all_users(self):
        """URL адресы, которые доступны всем пользователям."""
        urls = [
            '/',
            '/group/test_group/',
            '/profile/author/',
            '/posts/1/',
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_available_for_auth_users(self):
        """URL адресы, доступные только авторизированным пользователям."""
        urls = [
            '/create/'
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """URL адрес, которого не существует."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_available_editing_post_for_author(self):
        """Проверка возможности редактирования поста для пользователя."""
        response = self.author_of_post.get('/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_redirect(self):
        """Проверка редиректа анонимного пользователя
            на странциу авторизации."""
        urls = {
            '/create/': '/auth/login/?next=/create/',
            '/posts/1/edit/': '/auth/login/?next=/posts/1/edit/',
        }
        for url, redirect in urls.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect)

    def test_redirect_auth_user_trying_edit(self):
        """Проверка редиректа не автора при попытке редактирования поста."""
        response = self.authorized_client.get('/posts/1/edit/', follow=True)
        self.assertRedirects(response, '/posts/1/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test_group/': 'posts/group_list.html',
            '/profile/author/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_of_post.get(address)
                self.assertTemplateUsed(response, template)

    def test_adding_comment_for_gusets(self):
        """Комментировать посты может только авторизованный пользователь."""
        response = self.guest_client.get('/posts/1/comment/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/posts/1/comment/')

    def test_follow(self):
        """Авторизированный пользователь может подписываться."""
        self.authorized_client.get(
            f'/profile/{self.user_author.username}/follow/'
        )
        self.assertTrue(
            Follow.objects.filter(user=self.user, author=self.user_author)
        )

    def test_unfollow(self):
        """Авторизированный пользователь может отписаться."""
        self.authorized_client.get(
            f'/profile/{self.user_author.username}/unfollow/'
        )
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=self.user_author)
        )
