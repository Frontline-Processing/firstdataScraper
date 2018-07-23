import os
import sys
import time
import stat
from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException, UnexpectedAlertPresentException, StaleElementReferenceException

direct = os.getcwd()
dwn = os.environ["path"]

if not os.path.isdir(dwn):
    os.makedirs(dwn)
def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    if len(l) % n == 0:
        r = int(len(l) / n)
    else:
        r = int(math.ceil(len(l) / n))
    for i in range(0, len(l), r):
        yield l[i:i + r]

def empty_folder(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            # elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)
            return False
    return True

class Main(object):
    def getmerch(self):
        from selenium import webdriver
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains
        from pyvirtualdisplay import Display
        from driver_builder import DriverBuilder

        file = os.path.join(dwn,"Merchants.xlsx")
        if os.path.exists(file):
            os.remove(file)

        """Setup options for chrome web browser"""
        mn = Main()
        #display = Display(visible=0, size=(800, 600))
        #display.start()

        driver_builder = DriverBuilder()
        self.browser = driver_builder.get_driver(dwn, headless=False)
        browser = self.browser

        browser.get("https://portal.elevateqs.com/login.aspx")

        username = browser.find_element_by_id("username")
        password = browser.find_element_by_id("password")
        print(os.environ["tri_username"])
        print(os.environ["tri_password"])
        username.send_keys(os.environ["tri_username"])
        password.send_keys(os.environ["tri_password"])

        browser.find_element_by_id("login").click()
        # go to chargebacks
        browser.get("https://portal.elevateqs.com/Reporting/merchantsearch.aspx")

        # open filter
        sortcode = browser.find_element_by_id("s2id_autogen1")
        sortcode.send_keys("6101")
        time.sleep(.4)
        browser.find_element_by_class_name("select2-results-dept-0").click()
        #ActionChains(sortcode).move_to_element().click().perform()
        browser.find_element_by_id("Search").click()
        time.sleep(1)
        browser.find_element_by_xpath("//*[text()=' Export']").click()
        time.sleep(5)
        browser.quit()
        try:
            #display.close()
            "ds"
        except AttributeError:
            print("The Display is already closed?")

        os.chmod(file, 0o777)

if __name__ == "__main__":
    import argparse
    mn = Main()
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", help="Run the selenium script to grab excel", action="store_true", default=False)
    args = parser.parse_args()
    if args.run:
        mn.getmerch()
