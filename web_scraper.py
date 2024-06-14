import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Opening JSON file
data_json = open('global_policy-6_jun_2024.json', 'r')
# Returns JSON object as a dictionary
data = json.load(data_json)

# Generator to extract JSON data
def item_generator(json_input, lookup_key):
    if isinstance(json_input, dict):
        for k, v in json_input.items():
            if k == lookup_key and v:
                yield v
            else:
                yield from item_generator(v, lookup_key)
    elif isinstance(json_input, list):
        for item in json_input:
            yield from item_generator(item, lookup_key)

# Get all policy number in json
output = []
for i in item_generator(data, 'PolicyBaseNbr'):
    output.append(i)

newlist = [] # empty list to hold unique elements from the list
duplist = [] # empty list to hold the duplicate elements from the list
for i in output:
    if i not in newlist:
        newlist.append(i)
    else:
        duplist.append(i) # this method catches the first duplicate entries, and appends them to the list

print('Unique Item List', len(newlist))
print('List of duplicates', len(duplist))

service = Service('webdriver/chromedriver') # Path to WebDriver executable
service.start()
options = webdriver.ChromeOptions()
options.add_argument(r"user-data-dir=" + 'webdriver/userdata') # Path to get or save user data in chrome driver
# options.add_argument('--headless')  # Run Chrome in headless mode
driver = webdriver.Remote(service.service_url, options=options)

def extract_content(url):
    # Create empty dict
    result = {}
    driver.get(url)
    # Explicit wait page load until target element present
    wait = WebDriverWait(driver, 100)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'overview-page-purpose-content')))
    
    ## Extract dynamic content using Selenium
    # Get Policy title
    title = driver.find_element(By.CLASS_NAME, 'policy-banner-title')
    result['title'] = title.text

    # Get Policy overview
    policy_overview = driver.find_element(By.CLASS_NAME, 'overview-page-purpose-content')
    result['overview'] = policy_overview.text

    # Locate and navigate beetwen policy tab
    container = driver.find_element(By.CLASS_NAME, 'policy-detail-item')
    tabs = container.find_elements(By.CLASS_NAME, 'policy-tab')
    # Get Policy detail
    tabs[1].click()
    time.sleep(10) # Wait until page load
    policy_detail = container.find_elements(By.XPATH, "//div[contains(@class, 'policy-details')]/div/div/*")
    total_value = ''
    for i in range(len(policy_detail)):
        tagName = policy_detail[i].tag_name
        if tagName.startswith('p'):
            value = policy_detail[i].text
            if value:
                total_value = total_value + value + '\n'

        if tagName.startswith('ul'):
            bullets = policy_detail[i].text.strip()
            if bullets:
                total_value = total_value + bullets + '\n\n'

        if tagName.startswith('table'):
            table_body = policy_detail[i].find_element(By.TAG_NAME, 'tbody')
            entries = table_body.find_elements(By.TAG_NAME, 'tr')
            for i in range(len(entries)):
                cols = entries[i].find_elements(By.TAG_NAME, 'td')
                table_row = ''
                for j in range(len(cols)):
                    elements = cols[j].find_elements(By.XPATH, ".//p|.//ul")
                    element_text = ''
                    for k in range(len(elements)):
                        element = elements[k].tag_name
                        if element.startswith('ul'):
                            col_bullets = elements[k].find_elements(By.TAG_NAME, 'li')
                            bullet = []
                            for l in range(len(col_bullets)):
                                col_bullet = col_bullets[l].text.strip()
                                if col_bullet:
                                    bullet.append(col_bullet)
                            concat_bullet = ','.join(bullet)
                            if k == len(elements) - 1:
                                element_text = element_text + concat_bullet
                            else:
                                element_text = element_text + concat_bullet + ','
                        if element.startswith('p'):
                            text = elements[k].text.strip()
                            if text:
                                if k == len(elements) - 1:
                                    element_text = element_text + text
                                else:
                                    element_text = element_text + text + ','

                    table_row = table_row + element_text + '\n'
                total_value = total_value + table_row + '\n'

    result['policy'] = total_value
    # For debugging purpose
    # file = open('result.txt', 'w')
    # file.write(total_value)

    return result

titles = []
overviews = []
policies = []

for policy in newlist:
    print('Scraping ', policy)
    url = 'https://policies.accenture.com/policy/' + policy
    result = extract_content(url)
    titles.append(result['title'])
    overviews.append(result['overview'])
    policies.append(result['policy'])

print('Done Scraping', len(newlist), 'policy')

# save in pandas dataFrame
data = pd.DataFrame(
    list(zip(newlist, titles, overviews, policies)),
    columns=['Id', 'Title', 'Overview', 'Policy']
    )
# export data into a csv file.
data.to_csv('acn_policy.csv', index=False)

# Close the browser
driver.quit()