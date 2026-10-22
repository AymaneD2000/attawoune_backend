from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class OpenApiSchemaTests(SimpleTestCase):
    def test_schema_generates_without_warnings(self):
        stdout = StringIO()
        stderr = StringIO()

        call_command(
            "spectacular",
            file="/tmp/university-openapi-test.yml",
            validate=True,
            fail_on_warn=True,
            stdout=stdout,
            stderr=stderr,
        )

        self.assertNotIn("Warning", stderr.getvalue())
        self.assertNotIn("Error", stderr.getvalue())
