from django.test import TestCase
from business_application.models import BusinessApplication
from business_application.filters import BusinessApplicationFilter

class BusinessApplicationFilterTestCase(TestCase):
    def setUp(self):
        BusinessApplication.objects.create(
            name="App One",
            appcode="APP001",
            description="Test app one",
            owner="Owner One",
        )
        BusinessApplication.objects.create(
            name="App Two",
            appcode="APP002",
            description="Test app two",
            owner="Owner Two",
        )

    def test_filter_by_name(self):
        """Test filtering BusinessApplication by name."""
        filterset = BusinessApplicationFilter(data={'name': 'App One'})
        self.assertTrue(filterset.is_valid())
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().name, "App One")

    def test_filter_by_appcode(self):
        """Test filtering BusinessApplication by appcode."""
        filterset = BusinessApplicationFilter(data={'appcode': 'APP002'})
        self.assertTrue(filterset.is_valid())
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().appcode, "APP002")
