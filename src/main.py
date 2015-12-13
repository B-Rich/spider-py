from html.parser    import HTMLParser  
from urllib.request import urlopen  
from time           import sleep
from os             import path as os_path
from pymongo        import MongoClient

import urllib.parse
import urllib.error
import argparse


class Crawler(HTMLParser):

    def __init__(self, args):
        HTMLParser.__init__(self)
        self.root_url   = args.URL
        self.netloc     = urllib.parse.urlparse(self.root_url).netloc
        self.depth      = args.depth
        self.timer      = args.time
        self.db         = ClientMongo()[args.DATABASE]['items']
        self.sub        = args.sub
        self.verbose    = args.verbose
        # # # # # # # # # # # # # # # # # # # # # # 
        self.count      = 0
        self.urlVisited = []
        self.urlList    = [self.root_url]
        self.discovered = {}
        self.loadDB()


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

        self.db = self.client['crawler']
        self.collection = db['items']
    

    def queryDB(self):
        


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
            if self.verbose:
                print(">> %s: %s" % (e.code, e.reason))
            return ""
        except urllib.error.URLError as e:
            print(">> " + e.reason)
            return ""


    def crawl(self):
        while self.count != self.depth and self.urlList != []:
            try:
                url = self.urlList[0]
                self.count += 1
                if self.verbose:
                    print("   [%s]URL: %s" % (self.count, url))
                le_html = self.grabLinks(url)
                for item in self.db:
                    if " " + item + " " in le_html and (("buy" in le_html) or ("sell" in le_html)):
                        if self.verbose:
                            print("--> Found item: %s" % item)
                        if item not in self.discovered:
                            self.discovered[item] = [url]
                        else:
                            self.discovered[item] += [url]

                self.urlList.pop(0)
                self.urlVisited += [url]
                if len(self.urlVisited) % 10 == 0 and self.verbose:
                    url_total = len(self.urlList) + len(self.urlVisited)
                    url_remain = len(self.urlList)
                    url_complete = url_total - url_remain
                    print(">> Total Discovered URLs: %s; %s yet to parse." % (url_total, url_remain))

                if self.timer:
                    sleep(self.timer)
            except KeyboardInterrupt:
                print("\n Caught keyboard interrupt. Exiting...")
                return False



opts = argparse.ArgumentParser(description="A webspider used to discover and store information interest.")
group = opts.add_mutually_exclusive_group()
group.add_argument('-q', '--quiet', help="no output from spider.",
        action='store_false', dest="verbose")
group.add_argument('-v', '--verbose', help="set verbose output [default]",
        action='store_true', dest="verbose")

opts.add_argument('URL', help="url to start the crawl.")
opts.add_argument('-s', '--sub', help="directory of url to use as the root.")
opts.add_argument('DATABASE', help="database that will read and store information.",
        default=None)

opts.add_argument('-t', '--time', help="interval between each crawl.",
        type=float, default=False)
opts.add_argument('-d', '--depth', help="depth of crawling.",
        type=int, default=-1)

args = opts.parse_args()


if not os_path.isfile(args.DATABASE):
    print(" Bad database: %s" % args.DATABASE)
    exit()

crawler = Crawler(args)
crawler.crawl()
