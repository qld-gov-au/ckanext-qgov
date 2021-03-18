# encoding: utf-8

'''Tests for the ckanext.qgov extension MIME type validation.
'''

import textwrap
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
    ('example.kmz', 'KMZ', 'application/vnd.google-earth.kmz')
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

    def test_validate_upload_filename_and_format(self):
        """ Test that uploaded resources have their file extension and
        format compared to each other.
        """
        configure({})

        # file contents and format are PDF, but extension is CSV - fail
        upload = FlaskFileStorage(filename="dummy.pdf", stream=open("test/resources/dummy.pdf"))
        resource = {'url': 'example.csv', 'format': 'PDF', 'upload': upload}
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)
        self.assertIsNone(resource.get('mimetype'))

        # file contents and extension are PDF, but format is XML - fail
        resource['url'] = 'example.pdf'
        resource['format'] = 'XML'
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)
        self.assertIsNone(resource.get('mimetype'))

        # format is now PDF - succeed
        resource['format'] = 'PDF'
        validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'application/pdf')

    def test_recognise_file_types(self):
        """ Test that sample files are correctly sniffed.
        """
        configure({})
        for sample_file, sample_format, expected_type in sample_files:
            upload = FlaskFileStorage(filename=sample_file, stream=open("test/resources/" + sample_file))
            resource = {'url': sample_file, 'format': sample_format, 'upload': upload}

            validate_resource_mimetype(resource)
            self.assertEqual(resource['mimetype'], expected_type)

    def test_validate_upload_content(self):
        """ Test that uploaded resources have their contents compared
        to their claimed file format and extension.
        """
        # file extension and format are PDF, but contents are text - fail
        upload = FlaskFileStorage(filename="eicar.com.pdf", stream=open("test/resources/eicar.com.pdf"))
        resource = {'url': 'example.pdf', 'format': 'PDF', 'upload': upload}
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)

        # file extension, format and contents are now plain text - succeed
        resource['url'] = 'example.txt'
        resource['format'] = 'TXT'
        validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'text/plain')

    def test_validate_upload_archive(self):
        """ Test that uploaded archives can claim any resource format,
        but must still be well formed with matching file extension.
        """
        # file is an archive, but has a different extension - fail
        upload = FlaskFileStorage(filename="example.zip", stream=open("test/resources/example.zip"))
        resource = {'url': 'example.pdf', 'format': 'PDF', 'upload': upload}
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)

        # extension fixed, but format is PDF - succeed
        resource['url'] = 'example.zip'
        validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'application/pdf')

        # extension and contents are ZIP, format is DOC - succeed
        del resource['mimetype']
        resource['format'] = 'DOC'
        validate_resource_mimetype(resource)
        self.assertEqual(resource['mimetype'], 'application/msword')

        # extension is ZIP, but file isn't really an archive - fail
        upload = FlaskFileStorage(filename="eicar.zip", stream=open("test/resources/eicar.com.pdf"))
        resource = {'url': 'example.zip', 'format': 'PDF', 'upload': upload}
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)
        resource['format'] = 'ZIP'
        self.assertRaises(ValidationError, validate_resource_mimetype, resource)

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
        self.assertEqual(INVALID_UPLOAD_MESSAGE, textwrap.dedent('''This file type is not supported.
                         If possible, upload the file in another format.
                         If you continue to have problems, contact Smart Service Queensland - onlineproducts@smartservice.qld.gov.au'''))

        self.assertEqual(MISMATCHING_UPLOAD_MESSAGE, textwrap.dedent('''Mismatched file type. Please ensure that
                         the selected format is compatible with the file extension and file
                         contents. Unable to determine whether the file is of type '{}' or '{}'.
                         If possible, upload the file in another format.
                         If you continue to have problems, contact Smart Service Queensland - onlineproducts@smartservice.qld.gov.au'''))


if __name__ == '__main__':
    unittest.main()
