import os
import sys
import time
import json
import requests
from bs4 import BeautifulSoup
import smtplib

## Mode
test_mode = False  # Changes email subject, won't forward from account

## Min check frequency (seconds) between web queries for bike model "in stock" status
check_interval = 5
info_filename = os.path.join(sys.path[0], "info-yt-bikes.json")

## Email setup info
email_creds_file = os.path.join(sys.path[0], ".email_creds")
email_addr = ""
gmail_app_pwd = ""

def get_email_creds(creds_file):
    infile = open(creds_file)
    lines = infile.readlines()
    if lines is not None:
        if len(lines) >= 2:
            addr = str(lines[0].strip('\n'))
            pwd = str(lines[1].strip('\n'))
            print("email creds set to: %s %s (redacted)" % (addr, '#'*len(pwd)))
            return addr, pwd
    return None, None

def get_email_text(user, recipient, subject, body):
    FROM = user
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)

    print(message)

    return message

def load_bike_info(json_file):

    # Read bike info file from disk if it exists
    if os.path.exists(json_file):
        with open(json_file, 'r') as infile:
            data = json.load(infile)
            if data is not None:
                #print(type(data))
                if len(data.keys()) > 0:
                    return data
    return None

def save_bike_info(json_file, info_dict):
    with open(json_file, 'w') as outfile:
        json.dump(info_dict, outfile, indent=4)

# YT Query function
def yt_status(url, div_kwd):
    # the target we want to open
    # Example url='https://us.yt-industries.com/shopware.php?sViewport=detail&sArticle=2352'

    #open with GET method
    resp=requests.get(url)

    # 200 = OK
    if resp.status_code == 200:
        # we need a parser, Python built-in HTML parser is enough
        soup=BeautifulSoup(resp.text,'html.parser')

        # d is the list which contains page elements for this size and color
        # keyword: lieferangabe-4
        d = soup.find("div", {"class": div_kwd})

        # If d contains data, print it
        if d is not None:
            if test_mode:
                print(d.prettify())

            # Check warning first, if no warning and success, it's in stock
            warn = d.find("span", {"class": "warning"})
            if warn is not None:
                print("  Warning: %s" % warn.text.strip())
                return warn.text.strip()
            else:
                print("  (No Warning)")
                succ = d.find("span", {"class": "success"})
                if succ is not None:
                    print("  bike %s." % (succ.text.strip()))
                    return succ.text.strip()

    else:
        print("Error, code: %s" % resp.status_code)

if __name__ == "__main__":

    email_addr, gmail_app_pwd = get_email_creds(email_creds_file)
    if email_addr is None or gmail_app_pwd is None:
        print("Could not fetch email creds from %s" % email_info)
        exit

    # YT Jeffsy XL
    url = 'https://us.yt-industries.com/shopware.php?sViewport=detail&sArticle=2352'

    yt_bikes = {"2020 Jeffsy 27 Pro XL - ghostshipgreen":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2352/sCategory/511",
                  "div_kwd": "col-xs-12 col-sm-9 vcenter lieferangabe-4 nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0},
                "2020 Jeffsy 27 Pro XL - blackmagic":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2352/sCategory/511",
                  "div_kwd": "col-xs-12 col-sm-9 vcenter lieferangabe-13 nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0},
                "2019 Jeffsy 27 CF Pro XL - red":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2110",
                  "div_kwd": "col-xs-12 col-sm-8 col-md-5 col-lg-7 lieferangabe-4 xs-centered nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0},
                "2019 Jeffsy 27 CF Pro XL - white":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2111",
                  "div_kwd": "col-xs-12 col-sm-8 col-md-5 col-lg-7 lieferangabe-4 xs-centered nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0},
                "2019 Jeffsy 27 CF Pro-Race XL - silver":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2108",
                  "div_kwd": "col-xs-12 col-sm-8 col-md-5 col-lg-7 lieferangabe-4 xs-centered nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0}
                }
    # Test data
    test_dict = {
                "tues-LG-blackmagic":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2367/sCategory/261",
                  "div_kwd": "col-xs-12 col-sm-9 vcenter lieferangabe-12 nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0},
                "tues-XXL-green":
                  {"url": "https://us.yt-industries.com/detail/index/sArticle/2367/sCategory/261",
                  "div_kwd": "col-xs-12 col-sm-9 vcenter lieferangabe-5 nopadding-left",
                  "status": "out of stock",
                  "last_check": 0.0}
               }

    # For testing purposes, add Tues info
    if test_mode: yt_bikes.update(test_dict)

    # Read bike info file from disk if it exists
    bike_db = load_bike_info(info_filename)
    # Overwrite our template above if: template contains no new keys
    if bike_db is not None and len(bike_db.keys()) == len(yt_bikes.keys()):
        yt_bikes = bike_db
    else:
        print("Querying bikes from template...")

    # array to hold in-stock info
    instock_msg_list = []

    # Look for a bike's status
    for bike in yt_bikes:
        bike_info = yt_bikes[bike]
        status_before = bike_info["status"]
        dt = time.time() - bike_info["last_check"]
        if dt < check_interval:
            print("%s seconds since last check. interval: %s. breaking" % (dt, check_interval))
            break
        print("Checking on %s..." % bike)
        status = yt_status(bike_info["url"], bike_info["div_kwd"])

        # Update bike info dict, and write to disk
        bike_info["status"] = status
        bike_info["last_check"] = time.time()

        save_bike_info(info_filename, yt_bikes)

        #print("Bike '%s' status: %s" % (bike, status))
        email_subject = "YT bikes in stock" if not test_mode else "TEST MODE"
        print("Email Subject: %s" % email_subject)
        message_line = "- %s: %s" % (bike, bike_info["url"])

        # If any bikes are in stock, send email
        if status == "in stock" and status_before != status:
            print(message_line)
            instock_msg_list.append(message_line)

    if len(instock_msg_list) > 0:
        # Send message via gmail OAuth with app password
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.login(email_addr, gmail_app_pwd)
            email_body = "YT Bikes in Stock:\n" + '\n'.join(instock_msg_list)
            server.sendmail("yt-status@bot.com", email_addr, get_email_text("yt-status@bot.com", email_addr,
                                                    email_subject, email_body))
            server.quit()
        except Exception as err:
            print('Something went wrong sending email... \n %s' % err)
    else:
        print("No YT bike stock updates to report.")
