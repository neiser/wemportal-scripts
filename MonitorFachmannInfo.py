import os
import time
from timeit import default_timer as timer

from prometheus_client import start_http_server, PLATFORM_COLLECTOR, PROCESS_COLLECTOR, GC_COLLECTOR
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from prometheus_client.metrics_core import InfoMetricFamily
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

MAP_METRICS = {
    'Zeitstempel': {'name': 'timestamp', 'type': 'info'},
    'Außentemperatur': {'name': 'current_outside_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'AT Mittelwert': {'name': 'average_outside_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'AT Langzeitwert': {'name': 'longtime_outside_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Raumsolltemperatur': {'name': 'room_set_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Vorlaufsolltemperatur': {'name': 'water_inlet_set_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Vorlauftemperatur': {'name': 'water_inlet_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Warmwassertemperatur': {'name': 'hot_water_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Leistungsanforderung': {'name': 'performance_request_ratio', 'type': 'gauge', 'strip': len(' %')},
    'Schaltdifferenz dynamisch': {'name': 'dynamic_switch_temperature_difference_kelvin', 'type': 'gauge',
                                  'strip': len(' K')},
    'LWT': {'name': 'lwt_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Rücklauftemperatur': {'name': 'water_outlet_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Drehzahl Pumpe': {'name': 'pump_rotation_ratio', 'type': 'gauge', 'strip': len(' %')},
    'Volumenstrom': {'name': 'volume_flow_cubicmeter_per_hour', 'type': 'gauge', 'strip': len('m3/h')},
    'Stellung Umschaltventil': {'name': 'crossover_valve_setting', 'type': 'info'},
    'Soll Frequenz Verdichter': {'name': 'set_frequency_compressor_hertz', 'type': 'gauge', 'strip': len(' Hz')},
    'Ist Frequenz Verdichter': {'name': 'frequency_compressor_hertz', 'type': 'gauge', 'strip': len(' Hz')},
    'Luftansaugtemperatur': {'name': 'air_inlet_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Wärmetauscher AG Eintritt': {'name': 'outside_heat_exchanger_inlet_temperature_celsius', 'type': 'gauge',
                                  'strip': len(' °C')},
    'Wärmetauscher AG Mitte': {'name': 'outside_heat_exchanger_middle_temperature_celsius', 'type': 'gauge',
                               'strip': len(' °C')},
    'Druckgas': {'name': 'pressure_gas_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Wärmetauscher Innen': {'name': 'inside_heat_exchanger_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
    'Kältemittel Innen': {'name': 'refrigerant_inside_temperature_celsius', 'type': 'gauge', 'strip': len(' °C')},
}


# Betriebsstd. Verdichter=103 h
# Schaltspiele Verdichter=836
# Schaltspiele Abtauen=0
# Außengerät Variante=WWP LS X-B R(-E)
# Status E-Heizung 1=Aus
# Status E-Heizung 2=Aus
# Betriebsstunden E1=0 h
# Betriebsstunden E2=0 h
# Schaltspiele E1=0
# Schaltspiele E2=0
# Gesamt Energie Tage=6.299 KWh
# Gesamt Energie Monate=299.715 KWh
# Gesamt Energie Jahre=367.594 KWh
# Heizen Energie Tage=0.502 KWh
# Heizen Energie Monat=148.636 KWh
# Heizen Energie Jahre=148.636 KWh
# WW Energie Tag=5.796 KWh
# WW Energie Monat=151.075 KWh
# WW Energie Jahr=218.954 KWh
# Kühlen Energie Tage=0.000 KWh
# Kühlen Energie Monate=0.000 KWh
# Kühlen Energie Jahre=0.000 KWh

chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)


def refresh_page():
    print("Refreshing page...")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "ctl00_DeviceContextControl1_RefreshDeviceDataButton"))
    ).click()
    wait_until_page_loaded()


def login_and_load_fachmann_page():
    wemportal_user = os.environ['WEMPORTAL_USER']
    wemportal_password = os.environ['WEMPORTAL_PASSWORD']
    fachmann_password = os.environ['FACHMANN_PASSWORD']

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


def wait_until_page_loaded():
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


def parse_page():
    timestamp = driver.find_element(By.ID, "ctl00_DeviceContextControl1_lblDeviceLastDataUpdateInfo").text
    result = {"Zeitstempel": timestamp}
    print("Parsing page with timestamp {}".format(timestamp))

    map_id_to_name = {}

    for element in driver.find_elements(By.CLASS_NAME, "simpleDataName"):
        stripped_id = element.get_attribute('id')[:-8]
        value = element.text
        map_id_to_name[stripped_id] = value

    for element in driver.find_elements(By.CLASS_NAME, "simpleDataValue"):
        stripped_id = element.get_attribute('id')[:-9]
        value = element.text
        result[map_id_to_name[stripped_id]] = value
    print("Found {} data points".format(len(result)))
    return result


def parse_aus_value(str, strip=None):
    if str == 'Aus':
        return 0
    elif strip is not None:
        return str[:-int(strip)]
    else:
        return str


def collect_metrics():
    refresh_page()
    result = parse_page()

    for key, value in result.items():
        print("{}={}".format(key, value))
        metric = MAP_METRICS.get(key)
        if metric is not None:
            name = 'wemportal_' + metric['name']
            t = metric.get('type', 'gauge')
            if t is 'gauge':
                value = parse_aus_value(value, metric.get('strip'))
                yield GaugeMetricFamily(name, key, value=value)
            if t is 'info':
                yield InfoMetricFamily(name, key, value={'value': value})


class CustomCollector(object):
    def collect(self):
        metrics = list(collect_metrics())
        print("Exporting {} metrics".format(len(metrics)))
        return metrics


if __name__ == "__main__":
    try:
        for c in [PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR]:
            REGISTRY.unregister(c)
        login_and_load_fachmann_page()
        wait_until_page_loaded()
        REGISTRY.register(CustomCollector())
        start_http_server(8000)
        print("Running...")
        while True:
            time.sleep(100)
    finally:
        driver.quit()
