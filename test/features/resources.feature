@resources
Feature: Resource UI

    Scenario Outline: Link resource should create a link to its URL
        Given "SysAdmin" as the persona
        When I log in
        And I open the new resource form for dataset "test-dataset"
        And I create a resource with key-value parameters "name=<name>::url=<url>"
        And I press the element with xpath "//a[contains(@title, '<name>') and contains(string(), '<name>')]"
        Then I should see "<url>"

        Examples:
        | name | url |
        | Good link | http://www.qld.gov.au |
        | Good IP address | http://1.2.3.4 |
        | Domain starting with numbers | http://1.2.3.4.example.com |
        | Domain ending with numbers | http://example.com.1.2.3.4 |
        | Domain ending with private | http://example.com.private |

    Scenario: Link resource with missing or invalid protocol should use HTTP
        Given "SysAdmin" as the persona
        When I log in
        And I create a dataset and resource with key-value parameters "notes=Testing invalid link protocol" and "name=Non-HTTP link::url=git+https://github.com/ckan/ckan.git"
        And I press "Non-HTTP link"
        Then I should see "http://git+https://github.com/ckan/ckan.git"
