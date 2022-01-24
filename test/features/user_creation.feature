@user_creation
Feature: User creation

    Scenario: SysAdmin can create 'Excluded display name words' in ckan admin config
        Given "SysAdmin" as the persona
        When I log in
        Then I go to "/ckan-admin/config"
        Then I should see "Excluded display name words"
        Then I fill in "ckanext.data_qld.excluded_display_name_words" with "gov"
        Then I press "save"


    Scenario: SysAdmin create a new user to the site.
        Given "SysAdmin" as the persona
        When I log in
        When I go to "/user/register"
        Then I should see "Displayed name"
        Then I fill in "name" with "publisher_user"
        Then I fill in "fullname" with "gov user"
        Then I press "save"
        And I wait for 10 seconds
        Then I should not see "The username cannot contain the word 'publisher'. Please enter another username."
        Then I should not see "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name."


    Scenario: Non logged-in user register to the site.
        Given "Unauthenticated" as the persona
        When I go to "/user/register"
        Then I should see "Displayed name"
        Then I fill in "name" with "publisher_user"
        Then I fill in "fullname" with "gov user"
        Then I press "save"
        And I wait for 10 seconds
        Then I should see "The username cannot contain the word 'publisher'. Please enter another username."
        Then I should see "The displayed name cannot contain certain words such as 'publisher', 'QLD Government' or similar. Please enter another display name."
