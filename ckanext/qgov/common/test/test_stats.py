# encoding: utf-8

'''Tests for the ckanext.qgov extension resource URL filter.
'''

from datetime import datetime
import pytest

from ckan.tests import factories
from ckan.plugins.toolkit import check_ckan_version

from ckanext.qgov.common.stats import Stats


@pytest.fixture()
def migrate_db_for_plugins(migrate_db_for):
    if check_ckan_version('2.11'):
        migrate_db_for('activity')


@pytest.fixture()
def org(migrate_db_for_plugins):
    return factories.Organization()


@pytest.fixture()
def group(migrate_db_for_plugins):
    return factories.Group()


@pytest.fixture()
def dataset(org, group):
    return factories.Dataset(owner_org=org['id'], groups=[{"id": group['id']}], private=False)


@pytest.fixture()
def resource(dataset):
    return factories.Resource(package_id=dataset['id'])


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestStats():
    """ Test our URL validation.
    """

    def test_top_groups(self, group, resource):
        """ Test that the most-used categories can be retrieved.
        """
        top_categories = Stats().top_categories()
        assert len(top_categories) == 1
        assert top_categories[0][0].id == group['id']
        assert top_categories[0][1] == 1

    def test_top_orgs(self, org, resource):
        """ Test that the most-used organisations can be retrieved.
        """
        top_orgs = Stats().top_organisations()
        assert len(top_orgs) == 1
        assert top_orgs[0][0].id == org['id']
        assert top_orgs[0][1] == 1

    def test_resource_count(self, resource):
        """ Test that all resources can be counted.
        """
        assert Stats().resource_count() == 1

    def test_resource_report(self, org, dataset, resource):
        """ Test that the detailed resource report can be retrieved.
        """
        report = Stats().resource_report()
        assert len(report) == 1
        created_date = datetime.fromisoformat(resource['created']) if resource['created'] else None
        modified_date = datetime.fromisoformat(resource['last_modified']) if resource['last_modified'] else None
        assert report[0] == (
            org['title'], dataset['title'], resource['name'], resource['url'],
            created_date, modified_date,
            resource['format'], resource.get('webstore_url'), resource['resource_type']
        )

    def test_resource_org_count(self, org, resource):
        """ Test that the resources in an organisation can be counted.
        """
        assert Stats().resource_org_count(org['id']) == 1
