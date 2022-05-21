from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.cache import cache

from ..models import Group, Post, User


class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовая группа для теста'
        )
        for i in range(12):
            Post.objects.create(
                text=f'Тестовый пост {i}',
                author=cls.user_author,
                group=cls.group
            )
        # Последний пост
        cls.post = Post.objects.create(
            text='Тестовый пост 12',
            author=cls.user_author,
            group=cls.group
        )

        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': 'test_group'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': 'author'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': '1'}): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': '1'}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_of_post = Client()
        self.author_of_post.force_login(self.user_author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_of_post.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.author_of_post.get(reverse('posts:index'))
        self.assertEqual(response.context.get('page_obj')[0].text,
                         self.post.text)
        self.assertEqual(response.context.get('page_obj')[0].author,
                         self.user_author)

        if response.context.get('page_obj')[0].group:
            self.assertEqual(response.context.get('page_obj')[0].group,
                             self.group)

    def test_group_posts(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.author_of_post.get(
            reverse('posts:group_list', kwargs={'slug': 'test_group'})
        )
        self.assertEqual(response.context.get('page_obj')[0].text,
                         'Тестовый пост 12')
        self.assertEqual(response.context.get('page_obj')[0].author,
                         self.user_author)
        self.assertEqual(response.context.get('page_obj')[0].group,
                         self.group)

    def test_profile(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.author_of_post.get(
            reverse('posts:profile', kwargs={'username': 'author'})
        )
        self.assertEqual(response.context.get('page_obj')[0].text,
                         'Тестовый пост 12')
        self.assertEqual(response.context.get('page_obj')[0].author,
                         self.user_author)
        if response.context.get('page_obj')[0].group:
            self.assertEqual(response.context.get('page_obj')[0].group,
                             self.group)

    def test_post_detail(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.author_of_post.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context.get('post').text,
                         'Тестовый пост 12')
        self.assertEqual(response.context.get('post').author,
                         self.user_author)
        if response.context.get('post').group:
            self.assertEqual(response.context.get('post').group,
                             self.group)

    def test_edit_post(self):
        """Шаблон create_post для редактирования поста сформирован
            с правильным контекстом."""
        response = self.author_of_post.get(
            reverse('posts:post_edit', kwargs={'post_id': '13'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post(self):
        """Шаблон create_post для создания поста сформирован
            с правильным контекстом."""
        response = self.author_of_post.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_firs_page_paginators(self):
        """Корректная работа паджинатора на первой странице."""
        paginators_list = {
            reverse('posts:index'): 10,
            reverse('posts:group_list', kwargs={'slug': 'test_group'}): 10,
            reverse('posts:profile', kwargs={'username': 'author'}): 10,
        }
        for reverse_name, count_of_posts in paginators_list.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_of_post.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), count_of_posts
                )

    def test_second_page_paginators(self):
        """Корректная работа паджинатора на второй странице."""
        paginators_list = {
            reverse('posts:index'): 3,
            reverse('posts:group_list', kwargs={'slug': 'test_group'}): 3,
            reverse('posts:profile', kwargs={'username': 'author'}): 3,
        }
        for reverse_name, count_of_posts in paginators_list.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_of_post.get(reverse_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']), count_of_posts
                )

    def test_check_post_on_create(self):
        """Пост правильно добавляется на все страницы."""
        post = Post.objects.create(
            text='Test',
            author=self.user,
            group=self.group
        )
        response = self.author_of_post.get(reverse('posts:index'))
        self.assertEqual(response.context.get('page_obj')[0], post)

        response = self.author_of_post.get(
            reverse('posts:group_list', kwargs={'slug': 'test_group'})
        )
        self.assertEqual(response.context.get('page_obj')[0], post)

        response = self.author_of_post.get(
            reverse('posts:profile', kwargs={'username': 'HasNoName'})
        )
        self.assertEqual(response.context.get('page_obj')[0], post)

    def test_cash(self):
        """Проверка кэша страницы index."""
        post = Post.objects.create(
            text='Пост для проверки кэша',
            author=self.user_author
        )
        response_1 = self.authorized_client.get(reverse("posts:index"))
        Post.objects.get(pk=post.pk).delete()
        response_2 = self.authorized_client.get(reverse("posts:index"))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_2 = self.authorized_client.get(reverse("posts:index"))
        self.assertNotEqual(response_1.content, response_2.content)

    # Тесты на то, что человек может отписаться, есть в файле test_urls
    def test_posts_in_follow_page(self):
        """Новая запись пользователя появляется в ленте тех,
           кто на него подписан и не появляется в ленте тех,
           кто не подписан."""
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.user_author.username}
            )
        )
        post = Post.objects.create(
            text='Test',
            author=self.user_author
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )

        self.assertEqual(response.context.get('page_obj')[0], post)

        user = User.objects.create_user(username='Another')
        authorized_client2 = Client()
        authorized_client2.force_login(user)
        response = authorized_client2.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response.context.get('page_obj')), 0)
