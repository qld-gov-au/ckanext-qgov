#!/usr/bin/env sh
##
# Create some example content for extension BDD tests.
#
set -e

CKAN_ACTION_URL=http://ckan:3000/api/action

if [ "$VENV_DIR" != "" ]; then
  . ${VENV_DIR}/bin/activate
fi

CKAN_USER_NAME="${CKAN_USER_NAME:-admin}"
CKAN_DISPLAY_NAME="${CKAN_DISPLAY_NAME:-Administrator}"
CKAN_USER_EMAIL="${CKAN_USER_EMAIL:-admin@localhost}"

add_user_if_needed () {
    echo "Adding user '$2' ($1) with email address [$3]"
    ckan_cli user show "$1" | grep "$1" || ckan_cli user add "$1"\
        fullname="$2"\
        email="$3"\
        password="${4:-Password123!}"
}

add_user_if_needed "$CKAN_USER_NAME" "$CKAN_DISPLAY_NAME" "$CKAN_USER_EMAIL"
ckan_cli sysadmin add "${CKAN_USER_NAME}"

# We know the "admin" sysadmin account exists, so we'll use her API KEY to create further data
API_KEY=$(ckan_cli user show "${CKAN_USER_NAME}" | tr -d '\n' | sed -r 's/^(.*)apikey=(\S*)(.*)/\2/')
if [ "$API_KEY" = "None" ]; then
    echo "No API Key found on ${CKAN_USER_NAME}, generating API Token..."
    API_KEY=$(ckan_cli user token add "${CKAN_USER_NAME}" test_setup |grep -v '^API Token created' | tr -d '[:space:]')
fi

# Creating test data hierarchy which creates organisations assigned to datasets
ckan_cli create-test-data hierarchy

# Creating basic test data which has datasets with resources
ckan_cli create-test-data basic

add_user_if_needed organisation_admin "Organisation Admin" organisation_admin@localhost
add_user_if_needed publisher "Publisher" publisher@localhost
add_user_if_needed foodie "Foodie" foodie@localhost
add_user_if_needed group_admin "Group Admin" group_admin@localhost
add_user_if_needed walker "Walker" walker@localhost

echo "Updating annakarenina to use department-of-health Organisation:"
package_owner_org_update=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "id=annakarenina&organization_id=department-of-health" \
    ${CKAN_ACTION_URL}/package_owner_org_update
)
echo ${package_owner_org_update}

echo "Updating organisation_admin to have admin privileges in the department-of-health Organisation:"
organisation_admin_update=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "id=department-of-health&username=organisation_admin&role=admin" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${organisation_admin_update}

echo "Updating publisher to have editor privileges in the department-of-health Organisation:"
publisher_update=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "id=department-of-health&username=publisher&role=editor" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${publisher_update}

echo "Updating foodie to have admin privileges in the food-standards-agency Organisation:"
foodie_update=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "id=food-standards-agency&username=foodie&role=admin" \
    ${CKAN_ACTION_URL}/organization_member_create
)
echo ${foodie_update}

echo "Creating non-organisation group:"
group_create=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "name=silly-walks" \
    ${CKAN_ACTION_URL}/group_create
)
echo ${group_create}

echo "Updating group_admin to have admin privileges in the silly-walks group:"
group_admin_update=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "id=silly-walks&username=group_admin&role=admin" \
    ${CKAN_ACTION_URL}/group_member_create
)
echo ${group_admin_update}

echo "Updating walker to have editor privileges in the silly-walks group:"
walker_update=$( \
    curl -LsH "Authorization: ${API_KEY}" \
    --data "id=silly-walks&username=walker&role=editor" \
    ${CKAN_ACTION_URL}/group_member_create
)
echo ${walker_update}

if [ "$VENV_DIR" != "" ]; then
  deactivate
fi
