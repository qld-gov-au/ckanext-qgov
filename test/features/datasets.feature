Feature: Dataset APIs

    Scenario: Creative Commons BY-NC-SA 4.0 licence is an option for datasets
        Given "SysAdmin" as the persona
        When I log in
        And I edit the "warandpeace" dataset
        Then I should see an element with xpath "//li//*[text() = 'Creative Commons Attribution-NonCommercial-ShareAlike 4.0']"
