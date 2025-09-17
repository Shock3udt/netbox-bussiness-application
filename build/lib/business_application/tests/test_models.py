from django.test import TestCase
from business_application.models import BusinessApplication
from virtualization.models import VirtualMachine

class BusinessApplicationModelTestCase(TestCase):
    def setUp(self):
        # Create test data
        self.vm1 = VirtualMachine.objects.create(name="Test VM 1")
        self.vm2 = VirtualMachine.objects.create(name="Test VM 2")
        self.app = BusinessApplication.objects.create(
            name="Test App",
            appcode="APP001",
            description="A test business application",
            owner="Test Owner",
            delegate="Test Delegate",
            servicenow="https://example.com/servicenow"
        )
        self.app.virtual_machines.add(self.vm1, self.vm2)

    def test_business_application_creation(self):
        """Test that a BusinessApplication object is created correctly."""
        self.assertEqual(self.app.name, "Test App")
        self.assertEqual(self.app.appcode, "APP001")
        self.assertEqual(self.app.owner, "Test Owner")
        self.assertEqual(self.app.virtual_machines.count(), 2)

    def test_appcode_uniqueness(self):
        """Test that appcode is unique."""
        with self.assertRaises(Exception):
            BusinessApplication.objects.create(
                name="Duplicate App",
                appcode="APP001",  # Duplicate appcode
                owner="Another Owner"
            )
