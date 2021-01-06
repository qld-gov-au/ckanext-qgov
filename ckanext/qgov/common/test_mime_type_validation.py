# encoding: utf-8

'''Tests for the ckanext.qgov extension MIME type validation.
'''

import unittest

import intercepts
import ckan.logic


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
        self.assertEqual(intercepts.coalesce_mime_types([application_type, 'application/octet-stream']), application_type)
        self.assertEqual(intercepts.coalesce_mime_types([None, application_type, 'application/octet-stream']), application_type)

    def test_reject_override_not_configured(self):
        """ Test that more specific candidates cannot override
        'text/plain' and 'application/octet-stream' if 'allow_override'
        is set to False.
        """
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, ['text/plain', text_type], False)
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, [application_type, 'application/octet-stream'], False)

    def test_reject_override_incompatible_prefix(self):
        """ Test that candidates cannot override 'text/plain' and
        'application/octet-stream' with a different prefix.
        """
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, ['text/plain', application_type])
        self.assertRaises(ckan.logic.ValidationError, intercepts.coalesce_mime_types, [text_type, 'application/octet-stream'])


if __name__ == '__main__':
    unittest.main()
