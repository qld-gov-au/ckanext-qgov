
#!/usr/bin/env sh
##
# Create some example content for extension BDD tests.
#
set -e

CKAN_ACTION_URL=http://ckan:3000/api/action

. ${APP_DIR}/bin/activate

# We know the "admin" sysadmin account exists, so we'll use her API KEY to create further data
API_KEY=$(ckan_cli user admin | tr -d '\n' | sed -r 's/^(.*)apikey=(\S*)(.*)/\2/')

# Creating test data hierarchy which creates organisations assigned to datasets
ckan_cli create-test-data hierarchy

# Creating basic test data which has datasets with resources
ckan_cli create-test-data

ckan_cli user add organisation_admin fullname="Organisation Admin" email=organisation_admin@localhost password="Password123!"
ckan_cli user add publisher fullname="Publisher" email=publisher@localhost password="Password123!"
ckan_cli user add foodie fullname="Foodie" email=foodie@localhost password="Password123!"
ckan_cli user add group_admin fullname="Group Admin" email=group_admin@localhost password="Password123!"
ckan_cli user add walker fullname="Walker" email=walker@localhost password="Password123!"

echo "Updating annakarenina to use department-of-health Organisation:"
package_owner_org_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=annakarenina&organization_id=department-of-health" \
    ${CKAN_ACTION_URL}/package_owner_org_update
)
echo ${package_owner_org_update}

echo "Updating organisation_admin to have admin privileges in the department-of-health Organisation:"
organisation_admin_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=department-of-health&username=organisation_admin&role=admin" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${organisation_admin_update}

echo "Updating publisher to have editor privileges in the department-of-health Organisation:"
publisher_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=department-of-health&username=publisher&role=editor" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${publisher_update}

echo "Updating foodie to have admin privileges in the food-standards-agency Organisation:"
foodie_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=food-standards-agency&username=foodie&role=admin" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${foodie_update}

echo "Creating non-organisation group:"
group_create=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "name=silly-walks" \
    ${CKAN_ACTION_URL}/group_create
)
echo ${group_create}

echo "Updating group_admin to have admin privileges in the silly-walks group:"
group_admin_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=silly-walks&username=group_admin&role=admin" \
    ${CKAN_ACTION_URL}/group_member_create
)
echo ${group_admin_update}

echo "Updating walker to have editor privileges in the silly-walks group:"
walker_update=$( \
    curl -L -s --header "Authorization: ${API_KEY}" \
    --data "id=silly-walks&username=walker&role=editor" \
    ${CKAN_ACTION_URL}/group_member_create
)
echo ${walker_update}

deactivate
