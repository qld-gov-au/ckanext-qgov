# encoding: utf-8

'''Tests for the ckanext.qgov extension MIME type validation.
'''

import unittest

from resource_type_validation import configure,\
    coalesce_mime_types, validate_resource_mimetype,\
    INVALID_UPLOAD_MESSAGE, MISMATCHING_UPLOAD_MESSAGE
from ckan.logic import ValidationError
from werkzeug.datastructures import FileStorage as FlaskFileStorage


generic_text_type = 'text/plain'
text_type = 'text/csv'
generic_binary_type = 'application/octet-stream'
application_type = 'application/pdf'
archive_type = 'application/zip'
sample_files = [
    ('foo.csv', 'CSV', 'text/csv'),
    ('example.docx', 'DOCX', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    ('example.kmz', 'KMZ', 'application/vnd.google-earth.kmz'),
    ('example.xml', 'XML', 'text/xml'),
    ('dummy.pdf', 'PDF', 'application/pdf'),
    # well-formed archives can specify any format, since they can contain anything
    ('example.zip', 'PDF', 'application/pdf'),
    ('example.zip', 'DOC', 'application/msword'),
]

sample_file_rejections = [
    # file contents and format are PDF, but extension is CSV
    ('dummy.pdf', 'example.csv', 'PDF'),
    # file contents and extension are PDF, but format is XML
    ('dummy.pdf', 'example.pdf', 'XML'),
    # file extension and format are PDF, but contents are text
    ('eicar.com.pdf', 'example.pdf', 'PDF'),
    # file is an archive, but has a different extension
    ('example.zip', 'example.pdf', 'PDF'),
    # extension is ZIP, but file isn't really an archive
    ('eicar.com.pdf', 'example.zip', 'PDF'),
    ('eicar.com.pdf', 'example.zip', 'ZIP'),
]


class TestMimeTypeValidation(unittest.TestCase):
    """ Test that potential MIME type candidates are correctly coalesced
    to a best fit.
    """

    def test_coalesce_candidates(self):
        """ Test that missing candidates are gracefully ignored.
        """
        self.assertEqual(coalesce_mime_types([text_type]), text_type)
        self.assertEqual(coalesce_mime_types([text_type, None]), text_type)
        self.assertEqual(coalesce_mime_types([application_type, None]), application_type)
        self.assertEqual(coalesce_mime_types([None, text_type]), text_type)
        self.assertEqual(coalesce_mime_types([None, application_type]), application_type)
        self.assertEqual(coalesce_mime_types([None, text_type, None, text_type, None]), text_type)

    def test_override_candidates(self):
        """ Test that more specific candidates can override 'text/plain'
        and 'application/octet-stream' if 'allow_override' is set.
        """
        self.assertEqual(coalesce_mime_types([generic_text_type, text_type]), text_type)
        self.assertEqual(coalesce_mime_types([None, generic_text_type]), generic_text_type)
        self.assertEqual(coalesce_mime_types([None, text_type, generic_text_type]), text_type)
        self.assertEqual(coalesce_mime_types([None, 'application/xml', generic_text_type]), 'application/xml')
        self.assertEqual(coalesce_mime_types([application_type, generic_binary_type]), application_type)
        self.assertEqual(coalesce_mime_types([None, application_type, generic_binary_type]), application_type)
        self.assertEqual(coalesce_mime_types([None, 'x-gis/x-shapefile', generic_binary_type]), 'x-gis/x-shapefile')
        self.assertEqual(coalesce_mime_types([None, archive_type]), archive_type)

    def test_reject_override_not_configured(self):
        """ Test that more specific candidates cannot override
        'text/plain' and 'application/octet-stream' if 'allow_override'
        is set to False.
        """
        self.assertRaises(ValidationError, coalesce_mime_types, [generic_text_type, text_type], False)
        self.assertRaises(ValidationError, coalesce_mime_types, [application_type, generic_binary_type], False)

    def test_reject_override_incompatible_prefix(self):
        """ Test that candidates cannot override 'text/plain'
        with a different prefix.
        """
        self.assertRaises(ValidationError, coalesce_mime_types, [generic_text_type, application_type])

    # Full validation tests

    def test_recognise_file_types(self):
        """ Test that sample files are correctly sniffed.
        """
        configure({})
        for sample_filename, sample_format, expected_type in sample_files:
            sample_file = open("test/resources/" + sample_filename, "rb")
            upload = FlaskFileStorage(filename=sample_filename, stream=sample_file)
            resource = {'url': sample_filename, 'format': sample_format, 'upload': upload}

            try:
                validate_resource_mimetype(resource)
                self.assertEqual(resource['mimetype'], expected_type)
            finally:
                sample_file.close()

    def test_reject_bad_file_types(self):
        """ Test that invalid filename/format/content combinations are rejected.
        """
        configure({})
        for sample_filename, sample_url, sample_format in sample_file_rejections:
            sample_file = open("test/resources/" + sample_filename, "rb")
            upload = FlaskFileStorage(filename=sample_filename, stream=sample_file)
            resource = {'url': sample_url, 'format': sample_format, 'upload': upload}
            try:
                self.assertRaises(ValidationError, validate_resource_mimetype, resource)
                self.assertIsNone(resource.get('mimetype'))
            finally:
                sample_file.close()

    def test_revalidate_uploads_without_file(self):
        """ Test that resource of type 'upload' with no upload data
        have their URL and format compared, just no content sniffing.
        """
        configure({})
        resource = {'url': 'example.csv', 'format': 'PDF'}
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)

        resource['format'] = 'CSV'
        validate_resource_mimetype(resource)

    def test_no_validation_on_link_resources(self):
        """ Test that link-type resources do not have their file types
        validated, since they're not under our control.
        """
        resource = {'url': 'http://example.com/foo.csv', 'format': 'PDF'}
        validate_resource_mimetype(resource)
        self.assertIsNone(resource.get('mimetype'))

    def test_error_contact(self):
        """ Test that the error messages are populated correctly.
        """
        self.assertEqual(INVALID_UPLOAD_MESSAGE, '''This file type is not supported.
If possible, upload the file in another format.
If you continue to have problems, contact Smart Service Queensland - onlineproducts@smartservice.qld.gov.au''')

        self.assertEqual(MISMATCHING_UPLOAD_MESSAGE, '''Mismatched file type. Please ensure that
the selected format is compatible with the file extension and file
contents. Unable to determine whether the file is of type '{}' or '{}'.
If possible, upload the file in another format.
If you continue to have problems, contact Smart Service Queensland - onlineproducts@smartservice.qld.gov.au''')


if __name__ == '__main__':
    unittest.main()
