import os
from timeit import default_timer as timer

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def main():
    wemportal_user = os.environ['WEMPORTAL_USER']
    wemportal_password = os.environ['WEMPORTAL_PASSWORD']
    fachmann_password = os.environ['FACHMANN_PASSWORD']

    chrome_options = Options()
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        login_and_load_fachmann_page(driver, fachmann_password, wemportal_password, wemportal_user)
        wait_until_page_loaded(driver)
        parse_and_print_values(driver)

    finally:
        driver.quit()


def refresh_page(driver):
    print("Refreshing page...")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "ctl00_DeviceContextControl1_RefreshDeviceDataButton"))
    ).click()
    wait_until_page_loaded(driver)


def login_and_load_fachmann_page(driver, fachmann_password, wemportal_password, wemportal_user):
    driver.get("https://www.wemportal.com/Web/")
    print("Logging in...")
    driver.find_element(By.ID, "ctl00_content_tbxUserName").click()
    driver.find_element(By.ID, "ctl00_content_tbxUserName").send_keys(wemportal_user)
    driver.find_element(By.ID, "ctl00_content_tbxPassword").send_keys(wemportal_password)
    driver.find_element(By.ID, "ctl00_content_btnLogin").click()
    print("Go to Fachmann info page...")
    driver.find_element(By.CSS_SELECTOR, "#ctl00_RMTopMenu > ul > li.rmItem.rmFirst > a > span").click()
    driver.find_element(By.CSS_SELECTOR, "#ctl00_SubMenuControl1_subMenu > ul > li:nth-child(4) > a > span").click()
    driver.switch_to.frame(0)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "ctl00_DialogContent_tbxSecurityCode"))
    ).click()
    driver.find_element(By.ID, "ctl00_DialogContent_tbxSecurityCode").send_keys(fachmann_password)
    driver.find_element(By.ID, "ctl00_DialogContent_BtnSave").click()
    driver.switch_to.default_content()


def wait_until_page_loaded(driver):
    while True:
        refresh_button_span = driver.find_element(By.ID, "ctl00_DeviceContextControl1_RefreshDeviceDataButton")
        print("Waiting for refresh to be done...".format(refresh_button_span.id), end="")
        start = timer()
        try:
            WebDriverWait(driver, 8, poll_frequency=0.2).until(
                EC.staleness_of(refresh_button_span)
            )
            print("took {}".format(timer() - start))
        except TimeoutException:
            print("timed out")
            break
    print("Page loaded")


def parse_and_print_values(driver):
    timestamp = driver.find_element(By.ID, "ctl00_DeviceContextControl1_lblDeviceLastDataUpdateInfo").text
    print("Timestamp {}".format(timestamp))

    map_id_to_name = {}

    for element in driver.find_elements(By.CLASS_NAME, "simpleDataName"):
        stripped_id = element.get_attribute('id')[:-8]
        value = element.text
        map_id_to_name[stripped_id] = value

    print("Found {} data points".format(len(map_id_to_name)))

    for element in driver.find_elements(By.CLASS_NAME, "simpleDataValue"):
        stripped_id = element.get_attribute('id')[:-9]
        value = element.text
        print("{}={}".format(map_id_to_name[stripped_id], value))


if __name__ == "__main__": main()
