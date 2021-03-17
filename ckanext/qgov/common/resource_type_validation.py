# encoding: utf-8
""" Verify that uploaded resources have consistent types;
file extension, file contents, and resource format should match.
"""

import json
from logging import getLogger
import magic
import mimetypes
import os
import re
import six

from ckan.lib.uploader import ALLOWED_UPLOAD_TYPES
import ckan.logic
from werkzeug.datastructures import FileStorage as FlaskFileStorage

LOG = getLogger(__name__)

file_mime_config = json.load(open(
    os.path.join(os.path.dirname(__file__), 'resources', 'resource_types.json')
))

# Add allowed upload types that don't seem to be standard.
# NB It's more important to match a sniffable type than an RFC type.
for extension, mime_type in six.iteritems(file_mime_config.get('extra_mimetypes', {})):
    mimetypes.add_type(mime_type, extension)

ALLOWED_EXTENSIONS = file_mime_config.get('allowed_extensions', [])
ALLOWED_EXTENSIONS_PATTERN = re.compile(r'.*\.(' + '|'.join(ALLOWED_EXTENSIONS) + ')$', re.I)
ALLOWED_OVERRIDES = file_mime_config.get('allowed_overrides', {})
ARCHIVE_MIMETYPES = file_mime_config.get('archive_types', [])
for archive_type in ARCHIVE_MIMETYPES:
    ALLOWED_OVERRIDES[archive_type] = ["*"]
GENERIC_MIMETYPES = ALLOWED_OVERRIDES.keys()

INVALID_UPLOAD_MESSAGE = '''This file type is not supported.
If possible, upload the file in another format.
If you continue to have problems, email
Smart Service Queensland - online.products@smartservice.qld.gov.au
'''
MISMATCHING_UPLOAD_MESSAGE = '''Mismatched file type. Please ensure that
the selected format is compatible with the file extension and file
contents. Unable to determine whether the file is of type '{}' or '{}'.
If possible, upload the file with a different format.
If you continue to have problems, email
Smart Service Queensland - online.products@smartservice.qld.gov.au
'''
IS_REMOTE_URL_PATTERN = re.compile(r'^[a-z+]+://')


def _get_underlying_file(wrapper):
    if isinstance(wrapper, FlaskFileStorage):
        return wrapper.stream
    return wrapper.file


def configure(config):
    global allowed_mime_types

    allowed_mime_types = config.get('ckan.mimetypes_allowed', '*').split(',')


def validate_resource_mimetype(resource):
    upload_field_storage = resource.get('upload', None)
    if isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):
        filename = upload_field_storage.filename

        mime = magic.Magic(mime=True)
        upload_file = _get_underlying_file(upload_field_storage)
        # needs to be at least 2048 bytes to recognise DOCX properly
        sniffed_mimetype = mime.from_buffer(upload_file.read(2048))
        # go back to the beginning of the file buffer
        upload_file.seek(0, os.SEEK_SET)
        LOG.debug("Upload sniffing indicates MIME type %s", sniffed_mimetype)
    elif IS_REMOTE_URL_PATTERN.search(resource.get('url', 'http://example.com')):
        LOG.debug("%s is not an uploaded resource; don't validate", resource.get('id', 'New resource'))
        return
    else:
        LOG.debug("No upload in progress for %s; just sanity-check metadata", resource.get('id', 'new resource'))
        filename = resource.get('url')
        sniffed_mimetype = None

    if not ALLOWED_EXTENSIONS_PATTERN.search(filename):
        raise ckan.logic.ValidationError(
            {'upload': [INVALID_UPLOAD_MESSAGE]}
        )

    filename_mimetype = mimetypes.guess_type(resource.get('url'), strict=False)[0]
    LOG.debug("Upload filename indicates MIME type %s", filename_mimetype)

    format_mimetype = mimetypes.guess_type('example.' + resource.get('format', ''), strict=False)[0]
    LOG.debug("Upload format indicates MIME type %s", format_mimetype)

    # Archives can declare any format, but only if they're well formed
    if any(type in ARCHIVE_MIMETYPES
           for type in (filename_mimetype, sniffed_mimetype))\
            and filename_mimetype != sniffed_mimetype\
            and not is_valid_override(filename_mimetype, sniffed_mimetype):
        raise ckan.logic.ValidationError(
            {'upload': [MISMATCHING_UPLOAD_MESSAGE.format(filename_mimetype, sniffed_mimetype)]}
        )

    # If the file extension or format matches a generic type,
    # then sniffing should say the same.
    # This is to prevent attacks based on browser sniffing.
    allow_override = filename_mimetype not in GENERIC_MIMETYPES\
        and format_mimetype not in GENERIC_MIMETYPES\
        or filename_mimetype in ARCHIVE_MIMETYPES

    claimed_mimetype = resource.get('mimetype')
    LOG.debug("Upload claims to have MIME type %s", claimed_mimetype)

    best_guess_mimetype = resource['mimetype'] = coalesce_mime_types(
        [filename_mimetype, format_mimetype, sniffed_mimetype, claimed_mimetype],
        allow_override=allow_override
    )
    LOG.debug("Best guess at MIME type is %s", best_guess_mimetype)
    if not is_mimetype_allowed(best_guess_mimetype):
        raise ckan.logic.ValidationError(
            {'upload': [INVALID_UPLOAD_MESSAGE]}
        )


def coalesce_mime_types(mime_types, allow_override=True):
    """ Compares a list of potential mime types and identifies
    the best candidate, ignoring any that are None.

    Throws ckan.logic.ValidationError if any candidates conflict.
    Returns 'application/octet-stream' if all candidates are None.

    'allow_override' controls the treatment of 'application/octet-stream'
    and 'text/plain' candidates. If True, then more specific types will
    be able to override these types (within limits, eg 'text/csv' and
    'application/xml' can override 'text/plain', but 'application/pdf'
    cannot). If False, then all types must exactly match, or
    ValidationError will be thrown.
    """
    best_candidate = None
    for mime_type in mime_types:
        if not mime_type or mime_type == best_candidate:
            continue
        if not best_candidate:
            best_candidate = mime_type
            continue
        if allow_override and is_valid_override(best_candidate, mime_type):
            if best_candidate in GENERIC_MIMETYPES:
                best_candidate = mime_type
                continue
            if mime_type in GENERIC_MIMETYPES:
                continue
        raise ckan.logic.ValidationError(
            {'upload': [MISMATCHING_UPLOAD_MESSAGE.format(best_candidate, mime_type)]}
        )

    return best_candidate or 'application/octet-stream'


def is_valid_override(mime_type1, mime_type2):
    """ Returns True if one of the two types can be considered a subtype
    of the other, eg 'text/csv' can override 'text/plain'.
    """
    for generic_type, override_list in six.iteritems(ALLOWED_OVERRIDES):
        if generic_type in [mime_type1, mime_type2]:
            if mime_type1.split('/')[0] == mime_type2.split('/')[0]:
                # same prefix as the generic type we sniffed
                return True
            for override_type in override_list:
                if override_type == '*' or override_type in [mime_type1, mime_type2]:
                    return True
    else:
        return False


def is_mimetype_allowed(mime_type):
    for allowed_mime_type in allowed_mime_types:
        if allowed_mime_type == '*' or allowed_mime_type == mime_type:
            return True
    return False
