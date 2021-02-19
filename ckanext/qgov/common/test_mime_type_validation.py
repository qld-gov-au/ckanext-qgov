# encoding: utf-8

'''Tests for the ckanext.qgov extension MIME type validation.
'''

import unittest

import intercepts
import ckan.logic
from werkzeug.datastructures import FileStorage as FlaskFileStorage


text_type = 'text/csv'
application_type = 'application/pdf'


class TestMimeTypeValidation(unittest.TestCase):
    """ Test that potential MIME type candidates are correctly coalesced
    to a best fit.
    """

    def test_coalesce_candidates(self):
        """ Test that missing candidates are gracefully ignored.
        """
        self.assertEqual(intercepts.coalesce_mime_types([text_type]), text_type)
        self.assertEqual(intercepts.coalesce_mime_types([text_type, None]), text_type)
        self.assertEqual(intercepts.coalesce_mime_types([application_type, None]), application_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, text_type]), text_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, application_type]), application_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, text_type, None, text_type, None]), text_type)

    def test_override_candidates(self):
        """ Test that more specific candidates can override 'text/plain'
        and 'application/octet-stream' if 'allow_override' is set.
        """
        self.assertEqual(intercepts.coalesce_mime_types(['text/plain', text_type]), text_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, text_type, 'text/plain']), text_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, 'application/xml', 'text/plain']), 'application/xml')
        self.assertEqual(intercepts.coalesce_mime_types([application_type, 'application/octet-stream']), application_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, application_type, 'application/octet-stream']), application_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, 'x-gis/x-shapefile', 'application/octet-stream']), 'x-gis/x-shapefile')

    def test_reject_override_not_configured(self):
        """ Test that more specific candidates cannot override
        'text/plain' and 'application/octet-stream' if 'allow_override'
        is set to False.
        """
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, ['text/plain', text_type], False)
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, [application_type, 'application/octet-stream'], False)

    def test_reject_override_incompatible_prefix(self):
        """ Test that candidates cannot override 'text/plain'
        with a different prefix.
        """
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, ['text/plain', application_type])

    # Full validation tests

    def test_validate_upload_filename_and_format(self):
        """ Test that uploaded resources have their file extension and
        format compared to each other.
        """
        intercepts.configure({})
        upload = FlaskFileStorage(filename="dummy.pdf", stream=open("test/resources/dummy.pdf"))
        resource = {'url': 'example.csv', 'format': 'PDF', 'upload': upload}
        self.assertRaises(ckan.logic.ValidationError, intercepts.validate_resource_mimetype, resource)
        self.assertIsNone(resource.get('mimetype'))

        resource['url'] = 'example.pdf'
        resource['format'] = 'XML'
        self.assertRaises(ckan.logic.ValidationError, intercepts.validate_resource_mimetype, resource)
        self.assertIsNone(resource.get('mimetype'))

        resource['format'] = 'PDF'
        intercepts.validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'application/pdf')

        upload = FlaskFileStorage(filename="example.csv", stream=open("test/resources/foo.csv"))
        resource = {'url': 'example.csv', 'format': 'CSV', 'upload': upload}
        intercepts.validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'text/csv')

    def test_validate_upload_content(self):
        """ Test that uploaded resources have their contents compared
        to their claimed file format and extension.
        """
        upload = FlaskFileStorage(filename="eicar.com.pdf", stream=open("test/resources/eicar.com.pdf"))
        resource = {'url': 'example.pdf', 'format': 'PDF', 'upload': upload}
        self.assertRaises(ckan.logic.ValidationError, intercepts.validate_resource_mimetype, resource)

        resource['url'] = 'example.txt'
        resource['format'] = 'TXT'
        intercepts.validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'text/plain')

    def test_revalidate_uploads_without_file(self):
        """ Test that resource of type 'upload' with no upload data
        have their URL and format compared, just no content sniffing.
        """
        intercepts.configure({})
        resource = {'url': 'example.csv', 'format': 'PDF'}
        self.assertRaises(ckan.logic.ValidationError, intercepts.validate_resource_mimetype, resource)

        resource['format'] = 'CSV'
        intercepts.validate_resource_mimetype(resource)


if __name__ == '__main__':
    unittest.main()
