
#!/usr/bin/env sh
##
# Create some example content for extension BDD tests.
#
set -e

CKAN_ACTION_URL=http://ckan:3000/api/action
CKAN_INI_FILE=/app/ckan/default/production.ini

. /app/ckan/default/bin/activate \
    && cd /app/ckan/default/src/ckan

# We know the "admin" sysadmin account exists, so we'll use her API KEY to create further data
API_KEY=$(paster --plugin=ckan user admin -c ${CKAN_INI_FILE} | tr -d '\n' | sed -r 's/^(.*)apikey=(\S*)(.*)/\2/')

# Creating test data hierarchy which creates organisations assigned to datasets
paster create-test-data hierarchy -c ${CKAN_INI_FILE}

# Creating basic test data which has datasets with resources
paster create-test-data -c ${CKAN_INI_FILE}

paster --plugin=ckan user add group_admin email=group_admin@localhost password="Password123!" -c ${CKAN_INI_FILE}
paster --plugin=ckan user add publisher email=publisher@localhost password="Password123!" -c ${CKAN_INI_FILE}

echo "Updating annakarenina to use department-of-health Organisation:"
package_owner_org_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=annakarenina&organization_id=department-of-health" \
    ${CKAN_ACTION_URL}/package_owner_org_update
)
echo ${package_owner_org_update}

echo "Updating group_admin to have admin privileges in the department-of-health Organisation:"
group_admin_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=department-of-health&username=group_admin&role=admin" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${group_admin_update}

deactivate
