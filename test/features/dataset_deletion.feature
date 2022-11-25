@dataset_deletion
Feature: Dataset deletion

    Scenario: Sysadmin creates and deletes a dataset
        Given "SysAdmin" as the persona
        When I log in
        And I go to "/dataset/new"
        Then I fill in "title" with "Dataset deletion"
        And I fill in "name" with "dataset-deletion" if present
        Then I fill in "notes" with "notes"
        Then I execute the script "document.getElementById('field-organizations').value=jQuery('#field-organizations option').filter(function () { return $(this).html() == 'Test Organisation'; }).attr('value')"
        Then I select "False" from "private"
        Then I fill in "version" with "1"
        Then I fill in "author_email" with "test@test.com"
        And I press the element with xpath "//form[contains(@class, 'dataset-form')]//button[contains(@class, 'btn-primary')]"
        And I wait for 10 seconds
        Then I execute the script "document.getElementById('field-image-url').value='https://example.com'"
        Then I fill in "name" with "res1"
        Then I fill in "description" with "description"
        Then I fill in "size" with "1024" if present
        Then I press the element with xpath "//button[@value='go-metadata']"
        And I wait for 10 seconds
        Then I should see "Data and Resources"

        When I go to "/dataset/edit/dataset-deletion"
        Then I press the element with xpath "//a[string()='Delete' and @data-module='confirm-action']"
        Then I press the element with xpath "//div[@class='modal-footer']//button[@class='btn btn-primary']"
        And I wait for 5 seconds
        Then I should see "Dataset has been deleted"
        And I should not see "Dataset deletion"
        When I go to "/ckan-admin/trash"
        Then I should see "Dataset deletion"
        Then I press the element with xpath "//form[contains(@id, 'form-purge-package')]//*[contains(text(), 'Purge')]"
