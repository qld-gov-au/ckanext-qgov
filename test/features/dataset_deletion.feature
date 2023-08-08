@dataset_deletion
Feature: Dataset deletion

    Scenario: Sysadmin creates and deletes a dataset
        Given "SysAdmin" as the persona
        When I log in
        And I create a dataset and resource with key-value parameters "notes=Testing dataset deletion" and "url=default"
        And I edit the "$last_generated_name" dataset
        And I press the element with xpath "//a[@data-module='confirm-action']"
        And I confirm dataset deletion
        And I reload page every 2 seconds until I see an element with xpath "//div[contains(@class, "alert") and contains(string(), "Dataset has been deleted")]" but not more than 5 times
        Then I should not see an element with xpath "//a[contains(@href, '/dataset/$last_generated_name')]"
        When I go to "/ckan-admin/trash"
        Then I should see an element with xpath "//a[contains(@href, '/dataset/$last_generated_name')]"
        When I press the element with xpath "//form[contains(@id, 'form-purge-package')]//*[contains(string(), 'Purge')]"
        And I confirm the dialog containing "Are you sure you want to purge datasets?" if present
        Then I should see "datasets have been purged"
