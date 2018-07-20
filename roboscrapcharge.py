import time
import sys
import os
import csv
import shutil
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.common.action_chains import ActionChains
from decimal import Decimal, getcontext

direct = os.getcwd()
dwn = os.path.join(direct, 'csv')

firstdata = {
    'drivername': 'mysql+pymysql',
    'host': os.environ["host"],
    'port': os.environ["port"],
    'username': os.environ["rds_user"],
    'password': os.environ["rds_pass"],
    'database': 'firstdata',
}

card_dict = {
    'vi': 'Visa',
    'ae': 'Amex',
    'mc': 'MasterCard',
    'dv': 'Discover',
    'eb': 'EBT',
    'db': 'PinDebit'
}


def firstConn():
    """Connect to firstdata db"""
    firsty = create_engine(URL(**firstdata), strategy='threadlocal')
    firsty.echo = False
    return firsty


def callConnection(conn, sql):
    # open a transaction - this runs in the context of method_a's transaction
    trans = conn.begin()
    try:
        inst = conn.execute(sql)
        trans.commit()  # transaction is not committed yet
    except:
        print(sys.exc_info())
        inst = sys.exc_info()
        trans.rollback()  # this rolls back the transaction unconditionally
        raise
    return inst


def to_type(x):
    y = x.lower()
    if y in card_dict:
        return card_dict[y]
    else:
        return 'Other'

def to_cent(x):
    getcontext().prec = 6
    y = str(x)
    y = y.replace('$', '').replace(',', '')
    try:
        y = y.replace('(', '').replace(')', '')
    except:
        """Justing holding this up"""
    y = Decimal(y)
    return int(y * 100)


def manage_firstdata(method):
    def decorated_method(self, *args, **kwargs):
        """Befor the method call do this"""
        self.first = firstConn()
        self.confir = self.first.connect()

        """actual method call"""
        result = method(self, *args, **kwargs)

        """after the method call"""
        self.confir.close()

        return result
    return decorated_method


class Main(object):
    """Main class object"""
    @manage_firstdata
    def parse_csv(self):
        """Parse the given csv"""
        for file in os.listdir("csv"):
            my_file = os.path.join(dwn, file)
            with open(my_file) as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                next(readCSV)
                for row in readCSV:
                    my_row = row
                    break
                try:
                    mid = my_row[0].split(':')[1].strip()
                except UnboundLocalError:
                    print("No mid to grab from the csv")
                    continue
                print(mid)
            if file.endswith(".csv"):
                print(my_file)
                my_panda = pd.read_csv(
                    my_file, header=2, index_col='CB Sequence Number', parse_dates=True, infer_datetime_format=True)
                my_panda = my_panda.drop(my_panda.index[len(my_panda) - 1])
                my_panda['mid'] = mid
                #my_panda.reset_index(level=0, inplace=True)
                my_panda.rename(columns={'Report Date': 'processing-date', 'Trans Date': 'transaction-date', 'Trans Date': 'transaction-date', 'File Source': 'file_source', 'Card Type': 'card-type', 'Cardholder Number': 'card-number', 'CB Type': 'tran-type',
                                         'Reason Text': 'reason-desc', 'Disposition': 'disposition', 'Reference Number': 'reference-number', 'CB Sequence Number': 'ID', 'CB Reason Code': 'record-type', 'Reason Text': 'message', 'CB Amount': 'amount', '1st CB Amount': '1st_amount'}, inplace=True)
                my_panda = my_panda.fillna(0)
                my_panda['processing-date'] = pd.to_datetime(
                    my_panda['processing-date']).astype('datetime64[ns]', copy=True)
                my_panda['transaction-date'] = pd.to_datetime(
                    my_panda['transaction-date']).astype('datetime64[ns]', copy=True)
                my_panda['tran-type'] = my_panda['tran-type'].apply(
                    int).apply(str)
                my_panda['record-type'] = my_panda['record-type'].apply(
                    int).apply(str)
                my_panda['card-type'] = my_panda['card-type'].apply(to_type)
                my_panda['1st_amount'] = my_panda['1st_amount'].apply(to_cent)
                my_panda['amount'] = my_panda['amount'].apply(to_cent)
                my_date = str(
                    my_panda.iloc[0]['processing-date']).replace('/', '-')
                headers = '`,`'.join(list(my_panda))
                try:
                    my_panda.to_sql('chargebacks', self.confir,
                                    if_exists='append', index=False, chunksize=1000)
                except:
                    m = 0
                    n = 100
                    if n > int(my_panda.shape[0]):
                        n = int(my_panda.shape[0])
                    print(my_panda.shape)
                    while n <= int(my_panda.shape[0]):
                        update_list = []
                        for j, item in my_panda[m:n].iterrows():
                            """Place in the update script"""
                            update = "','".join(str(k)
                                                for k in item.values.tolist())
                            update_list.append("('{}')".format(update))
                        print(update_list)
                        insert_me = "insert into chargebacks(`{0}`) VALUES{1}".format(
                            headers, ','.join(update_list))
                        print(insert_me)
                        if not callConnection(self.confir, insert_me):
                            for j, item in my_panda[m:n].iterrows():
                                """Place in the update script"""
                                update = '","'.join(str(k)
                                                    for k in item.values.tolist())
                                str_update = ','.join("`{0}`='{1}'".format(
                                    key, item) for key, item in item.items())
                                insert_me = "insert into chargebacks(`{}`) VALUES('{}') ON DUPLICATE KEY UPDATE {}".format(
                                    headers, update, str_update)
                                print(insert_me)
                                if not callConnection(self.confir, insert_me):
                                    print("Something went wronge")
                                    break

                        if n == my_panda.shape[0]:
                            break
                        elif n + 100 > my_panda.shape[0]:
                            n = my_panda.shape[0]
                            m += 100
                        else:
                            n += 100
                            m += 100

            print(my_panda)
            if not os.path.exists('done'):
                os.makedirs('done')
            locy = 'done/{}{}.csv'.format(str(my_date), mid)
            shutil.move(my_file, locy)

    def getchargeback(self):
        """Setup options for chrome web browser"""
        from selenium import webdriver
        from selenium.webdriver.common.keys import Keys
        from pyvirtualdisplay import Display
        from driver_builder import DriverBuilder
        from selenium.common.exceptions import NoSuchElementException

        display = Display(visible=0, size=(800, 600))
        display.start()

        driver_builder = DriverBuilder()
        self.browser = driver_builder.get_driver(dwn, headless=False)
        browser = self.browser

        browser.get('https://www.youraccessone.com')

        username = browser.find_element_by_id("txtUserName")
        password = browser.find_element_by_id("txtPassword")

        username.send_keys(os.environ['username'])
        password.send_keys(os.environ['password'])

        browser.find_element_by_name("uxLogin").click()

        """go to chargebacks"""
        browser.get('https://www.youraccessone.com/64_rpt_Chargebacks.aspx')

        """open filter"""
        browser.find_element_by_xpath("//*[text()='FILTER']").click()

        """toggle daily"""
        browser.find_element_by_xpath("//*[text()='Daily']").click()

        """This section for date range not currently used change Daily to Date Range then uncomment"""
        """get date range"""
        """start = browser.find_element_by_id("ctl00_ContentPage_uxFiltering_uxDateRangeFrom_dateInput")
        start.clear()
        start.send_keys('01-01-2018')

        end = browser.find_element_by_id('ctl00_ContentPage_uxFiltering_uxDateRangeTo_dateInput')
        end.clear()
        end.send_keys('05-01-2018')"""

        """check all merchants"""
        browser.find_element_by_id(
            "ctl00_ContentPage_uxFiltering_uxOmahaHierarchies_uxchbAllMerchants").click()

        """submit to apply filters"""
        browser.find_element_by_id(
            "ctl00_ContentPage_uxFiltering_uxbtnDisplayRunReport").click()

        time.sleep(5)

        window_before = browser.window_handles[0]
        print(browser.title)

        while True:
            time.sleep(3)
            table_id = browser.find_element_by_class_name("rgMasterTable")
            for i in range(0,10):
                mn.get_pdf_row(i, table_id)

            try:
                enabl = browser.find_element_by_name('ctl00$ContentPage$uxReportGrid$ctl00$ctl03$ctl01$ctl00$pagerNextButton')
                print(enabl.is_enabled())
                if enabl.is_enabled():
                    enabl.click()
                else:
                    break
                    time.sleep(5)
            except NoSuchElementException:
                break

        browser.quit()
        display.stop()

    def get_pdf_row(self, i, table_id):
        get_me="ctl00_ContentPage_uxReportGrid_ctl00__{}".format(i)
        print(get_me)
        browser = self.browser
        try:
            for row in table_id.find_elements_by_id(get_me):
                cell = [item for item in row.find_elements_by_css_selector("td")][0]
                ActionChains(browser).move_to_element(cell).click().perform()

                """go to new window"""
                window_after = browser.window_handles[1]
                browser.switch_to.window(window_after)
                print(browser.title)
                time.sleep(5)

                """download chargeback"""
                element_to_hover_over = browser.find_element_by_xpath("//*[text()='EXPORT']")
                hover = ActionChains(browser).move_to_element(element_to_hover_over)
                hover.perform()

                browser.find_element_by_xpath("//*[text()='CSV']").click()

                """go back to previus page"""
                browser.close()
                print(browser.window_handles)
                browser.switch_to.window(browser.window_handles[0])

        except UnexpectedAlertPresentException:
            alert = self.browser.switch_to.alert
            alert.accept()
            return 0
        return 1

if __name__ == '__main__':
    import argparse
    mn = Main()
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run", help="Run the selenium script to grab csv",
                        action='store_true', default=False)
    parser.add_argument("-p", "--parse", help="Parse the csv",
                        action='store_true', default=False)
    args = parser.parse_args()
    if args.run:
        mn.getchargeback()
    if args.parse:
        mn.parse_csv()
