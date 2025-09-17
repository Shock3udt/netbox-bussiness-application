from django.test import TestCase
from django.urls import reverse
from business_application.models import BusinessApplication

class BusinessApplicationViewTestCase(TestCase):
    def setUp(self):
        self.app = BusinessApplication.objects.create(
            name="Test App",
            appcode="APP001",
            description="A test business application",
            owner="Test Owner",
            delegate="Test Delegate",
            servicenow="https://example.com/servicenow"
        )

    def test_list_view(self):
        """Test the list view of BusinessApplication."""
        response = self.client.get(reverse('businessapplication_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test App")

    def test_detail_view(self):
        """Test the detail view of BusinessApplication."""
        response = self.client.get(reverse('businessapplication_detail', args=[self.app.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test App")
        self.assertContains(response, "APP001")

    def test_add_view(self):
        """Test adding a new BusinessApplication."""
        response = self.client.post(reverse('businessapplication_add'), {
            'name': 'New App',
            'appcode': 'APP002',
            'description': 'Another test app',
            'owner': 'New Owner',
            'delegate': 'New Delegate',
            'servicenow': 'https://example.com/new'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect after success
        self.assertTrue(BusinessApplication.objects.filter(name="New App").exists())
