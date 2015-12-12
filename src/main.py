from html.parser import HTMLParser  
from urllib.request import urlopen  
import urllib.parse
import urllib.error
from time import sleep
from optparse import OptionParser

import re

url = "http://ultima-shards.com/forums/index.php"

class Crawler(HTMLParser):

    def __init__(self, url=None, depth=-1, sleep=False, database=None, sub=False):
        HTMLParser.__init__(self)
        self.root_url = url
        self.netloc = urllib.parse.urlparse(self.root_url).netloc
        self.depth = depth
        self.timer = sleep
        self.db = database
        self.sub = sub

        self.count = 0
        self.urlVisited = []
        self.urlList = [self.root_url]
        self.discovered = {}


    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for (key, value) in attrs:
                if key  == 'href':
                    value = value.split()
                    value = "".join(value)

                    newUrl = urllib.parse.urljoin(self.root_url, value)
                    le_url = urllib.parse.urlparse(newUrl)
                    proper_directory = le_url.path.split("/")
                    if self.sub not in proper_directory and self.sub:
                        return False
                    if le_url.netloc == self.netloc and newUrl not in self.urlVisited + self.urlList: 
                        self.urlList += [newUrl]


    def grabLinks(self, url):
        try:
            response = urlopen(url)
            if 'text/html' in response.headers['Content-Type']:
                htmlpage = response.read()
                le_html = htmlpage.decode("utf-8")
                self.feed(le_html)
                return le_html
            else:
                return ""
        except urllib.error.HTTPError as e:
            print(">> %s: %s" % (e.code, e.reason))
            return ""
        except urllib.error.URLError as e:
            print(">> " + e.reason)
            return ""


    def crawl(self):
        while self.count != self.depth and self.urlList != []:
            url = self.urlList[0]
            self.count += 1    
            print("   [%s]URL: %s" % (self.count, url))
            le_html = self.grabLinks(url)
            for item in self.db:
                if " " + item + " " in le_html and (("buy" in le_html) or ("sell" in le_html)):
                    print("--> Found item: %s" % item)
                    if item not in self.discovered:
                        self.discovered[item] = [url]
                    else:
                        self.discovered[item] += [url]

            self.urlList.pop(0)
            self.urlVisited += [url]
            if len(self.urlVisited) % 10 == 0:
                url_total = len(self.urlList) + len(self.urlVisited)
                url_remain = len(self.urlList)
                url_complete = url_total - url_remain
                print(">> Total Discovered URLs: %s; %s yet to parse." % (url_total, url_remain))

            if self.timer:
                sleep(self.timer)


with open('list.txt', 'r') as my_db:
    data_info = my_db.read().lower().strip('\n').split(';')

crawler = Crawler(url, sleep=30.0, database=data_info, sub="forums")
crawler.crawl()

