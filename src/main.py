from html.parser    import HTMLParser  
from urllib.request import urlopen  
from time           import sleep
from os             import path as os_path
from pymongo        import MongoClient

import urllib.parse
import urllib.error
import argparse
import re


class Crawler(HTMLParser):

    def __init__(self, args):
        HTMLParser.__init__(self)
        self.root_url   = args.URL
        self.netloc     = urllib.parse.urlparse(self.root_url).netloc
        self.depth      = args.depth
        self.timer      = args.time
        self.db         = MongoClient()[args.DATABASE]['items']
        self.sub        = args.sub
        self.verbose    = args.verbose
        # # # # # # # # # # # # # # # # # # # # # # 
        self.count      = 0
        self.urlVisited = []
        self.urlList    = [self.root_url]
        self.discovered = {}
        self.items      = []
        # # # # # # # # # # # # # # # # # # # # # # 
        self.li_main            = False     # Start of play contribution
        self.blockquote_main    = False     # Start of the message
        self.div_quote_main     = False     # Start of Quote Container
        self.div_quote_xpand    = False
        self.blockquote_quote   = False     # Start of Quote Message
        self.text_lock          = True
        self.li_name            = None      # Name of original author
        self.blockquote_name    = None      # Name of person being quoted.

        self.queryDB()


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

        elif tag == 'li':
            for (key, value) in attrs:
                if key == 'id':
                    continue
                elif key == 'class':
                    continue
                elif key == 'data-author':
                    self.li_main = True
                    self.li_name = value
                else:
                    self.li_main = False

        elif tag == 'blockquote':
            for (key, value) in attrs:
                #print("  [ DEBUG ]  %s: %s" % (key, value))
                if self.li_main and not self.blockquote_main and key == 'class' and value == 'messageText SelectQuoteContainer ugc baseHtml':
                    print("\n============================================")
                    #print("  [ DEBUG ] This is in 1st blockquote")
                    self.blockquote_main = True
                    self.text_lock = False
                elif self.blockquote_main:
                    #print("  [ DEBUG ] This is in 2nd blockquote")
                    self.blockquote_quote = True

        elif tag == 'div' and self.blockquote_main and self.blockquote_quote:
            for (key, value) in attrs:
                if key == 'class' and value == 'quote' and self.blockquote_quote:
                    self.div_quote_main = True
                    self.text_lock = False
                    #break
                elif key == 'class' and value == 'quoteExpand':
                    self.div_quote_xpand = True
                elif key == 'data-author':
                    self.blockquote_name = value



    def handle_data(self, data):
        if self.blockquote_main and not self.div_quote_main and not self.text_lock:
            if data.strip():
                print("%s said: " % self.li_name)
                print(data.strip())
            self.text_lock = True
        elif self.blockquote_quote and self.div_quote_main and not self.text_lock:
            #print(" QUOTE %s: " % self.blockquote_name)
            #print(data.strip())
            self.text_lock = True


    def handle_endtag(self, tag):
        if tag == 'li' and self.li_main:
            self.li_main            = False
            self.blockquote_main    = False
            self.blockquote_quote   = False
            self.div_quote_main     = False
            self.text_lock          = True
            self.li_name            = None
            self.blockquote_main    = None
        elif tag == 'blockquote':
            if self.blockquote_main and self.blockquote_quote:
                self.blockquote_quote = False
            elif self.blockquote_main and not self.blockquote_quote:
                self.blockquote_main = False
        elif tag == 'div':
            if self.blockquote_quote:
                self.div_quote_main = False
            elif self.div_quote_xpand:
                self.div_quote_xpand = False
                self.text_lock = False


    def queryDB(self):
        if len(self.items) < 1:
            for doc in self.db.find({}, { "name": 1, "alias": 1, "_id": 0 }):
                self.items.append(doc['name'])
                for alias in doc['alias']:
                    self.items.append(alias)



    def grabLinks(self, url):
        try:
            response = urlopen(url)
            if 'text/html' in response.headers['Content-Type']:
                htmlpage = response.read()
                le_html = htmlpage.decode("utf-8")
                le_html = re.sub("<br />", "", le_html)
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
                for item in self.items:
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


def remove_all(substr, string):
    index = 0
    length = len(substr)
    while string.find(substr) != -1:
        index = string.find(substr)
        sring = string[0:index] + string[index+length:]
    return string

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

crawler = Crawler(args)
crawler.crawl()
print("\n===================================================================================" * 7)
