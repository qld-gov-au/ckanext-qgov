#!/usr/bin/env sh
##
# Create some example content for extension BDD tests.
#
set -ex

CKAN_ACTION_URL=${CKAN_SITE_URL}api/action
CKAN_USER_NAME="${CKAN_USER_NAME:-admin}"
CKAN_DISPLAY_NAME="${CKAN_DISPLAY_NAME:-Administrator}"
CKAN_USER_EMAIL="${CKAN_USER_EMAIL:-admin@localhost}"

. ${APP_DIR}/bin/activate

add_user_if_needed () {
    echo "Adding user '$2' ($1) with email address [$3]"
    ckan_cli user show "$1" | grep "$1" || ckan_cli user add "$1"\
        fullname="$2"\
        email="$3"\
        password="${4:-Password123!}"
}

add_user_if_needed "$CKAN_USER_NAME" "$CKAN_DISPLAY_NAME" "$CKAN_USER_EMAIL"
ckan_cli sysadmin add "${CKAN_USER_NAME}"

API_KEY=$(ckan_cli user show "${CKAN_USER_NAME}" | tr -d '\n' | sed -r 's/^(.*)apikey=(\S*)(.*)/\2/')
if [ "$API_KEY" = "None" ]; then
    echo "No API Key found on ${CKAN_USER_NAME}, generating API Token..."
    API_KEY=$(ckan_cli user token add "${CKAN_USER_NAME}" test_setup |tail -1 | tr -d '[:space:]')
fi

##
# BEGIN: Create a test organisation with test users for admin, editor and member
#
TEST_ORG_NAME=test-organisation
TEST_ORG_TITLE="Test Organisation"

echo "Creating test users for ${TEST_ORG_TITLE} Organisation:"

add_user_if_needed ckan_user "CKAN User" ckan_user@localhost
add_user_if_needed test_org_admin "Test Admin" test_org_admin@localhost
add_user_if_needed test_org_editor "Test Editor" test_org_editor@localhost
add_user_if_needed test_org_member "Test Member" test_org_member@localhost

echo "Creating ${TEST_ORG_TITLE} organisation:"

api_call () {
    wget -O - --header="Authorization: ${API_KEY}" --post-data "$1" ${CKAN_ACTION_URL}/$2
}

TEST_ORG=$( \
    api_call '{"name": "'"${TEST_ORG_NAME}"'", "title": "'"${TEST_ORG_TITLE}"'",
        "description": "Organisation for testing issues"}' organization_create
)

TEST_ORG_ID=$(echo $TEST_ORG | $PYTHON ${APP_DIR}/bin/extract-id.py)

echo "Assigning test users to '${TEST_ORG_TITLE}' organisation (${TEST_ORG_ID}):"

api_call '{"id": "'"${TEST_ORG_ID}"'", "object": "test_org_admin", "object_type": "user", "capacity": "admin"}' member_create

api_call '{"id": "'"${TEST_ORG_ID}"'", "object": "test_org_editor", "object_type": "user", "capacity": "editor"}' member_create

api_call '{"id": "'"${TEST_ORG_ID}"'", "object": "test_org_member", "object_type": "user", "capacity": "member"}' member_create

##
# END.
#

add_user_if_needed group_admin "Group Admin" group_admin@localhost
add_user_if_needed walker "Walker" walker@localhost

# Create private test dataset with our standard fields
api_call '{"name": "test-dataset", "owner_org": "'"${TEST_ORG_ID}"'", "private": true,
"author_email": "admin@localhost", "license_id": "other-open", "notes": "private test"}' package_create

# Create public test dataset with our standard fields
api_call '{"name": "public-test-dataset", "owner_org": "'"${TEST_ORG_ID}"'",
"author_email": "admin@localhost", "license_id": "other-open", "notes": "public test"}' package_create

echo "Creating department-of-health organisation:"
organisation_create=$( \
    api_call "name=department-of-health&title=Department%20of%20Health" organization_create
)
echo ${organisation_create}

echo "Creating food-standards-agency organisation:"
organisation_create=$( \
    api_call "name=food-standards-agency&title=Food%20Standards%20Agency" organization_create
)
echo ${organisation_create}

echo "Creating non-organisation group:"
group_create=$( \
    api_call '{"name": "silly-walks", "title": "Silly walks", "description": "The Ministry of Silly Walks"}' group_create
)
echo ${group_create}

echo "Updating group_admin to have admin privileges in the silly-walks group:"
group_admin_update=$( \
    api_call '{"id": "silly-walks", "username": "group_admin", "role": "admin"}' group_member_create
)
echo ${group_admin_update}

echo "Updating walker to have editor privileges in the silly-walks group:"
walker_update=$( \
    api_call '{"id": "silly-walks", "username": "walker", "role": "editor"}' group_member_create
)
echo ${walker_update}

echo "Creating config value for excluded display name words:"

api_call '{"ckanext.data_qld.excluded_display_name_words": "gov"}' config_option_update

. ${APP_DIR}/bin/deactivate
