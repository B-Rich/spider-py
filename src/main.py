from html.parser    import HTMLParser  
from urllib.request import urlopen  
from time           import sleep
from os             import path as os_path
from pymongo        import MongoClient

import urllib.parse
import urllib.error
import argparse
import json
import re


class Crawler(HTMLParser):
    ''' Root of the crawler. All defined as a single object that is responsible for
    iterating over itself and making comparisons. '''
    def __init__(self, args):
        HTMLParser.__init__(self)
        self.root_url   = args.URL                                      # Original URL passed.
        self.netloc     = urllib.parse.urlparse(self.root_url).netloc   # Netloc of the URL.
        self.depth      = args.depth                                    # Distance (pages) to travel.
        self.timer      = args.time                                     # Amount of time per page.
        self.db         = MongoClient()[args.db][args.coll]               # Database that stores data.
        self.sub        = args.sub                                      # Subdirectory to set as root of webpage.
        self.verbose    = args.verbose                                  # Verbosity setting.
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  
        self.key_terms      = ["buy", "sell", "trade", "trading"]
        self.count          = 0                 # Amount of pages processed.
        self.posts          = 0                 # Amount of posts scanned.
        self.urlBlacklist   = []                # Already completed URLS.
        self.urlDNU         = []                # Do not use URLS, duplicates.
        self.urlList        = [self.root_url]   # List of URLS to scan.
        self.items          = []                # Items to look for.
        self.discovered     = {}                # Items discovered + [URLs]
        self.BigDict        = {}                # Dictionary containing ThreadID + [URLS] <- urlDNU list?.
        # # # # # # # # # # # # # # # # # # # # #
        self.li_main            = False     # Start of play contribution
        self.blockquote_main    = False     # Start of the message
        self.div_quote_main     = False     # Start of Quote Container
        self.div_quote_xpand    = False     # Start of QuoteExpand
        self.blockquote_quote   = False     # Start of Quote Message
        self.text_lock          = True      # Locks the abilty to print text or use it.
        self.li_name            = None      # Name of original author
        self.blockquote_name    = None      # Name of person being quoted.
        # # # # # # # # # # # # # # # # # # #
        self.queryDB()      # Loads the self.items list.


    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for (key, value) in attrs:
                if key  == 'href':
                    value = value.split()
                    value = "".join(value)
                    newUrl = urllib.parse.urljoin(self.root_url, value)
                    le_url = urllib.parse.urlparse(newUrl)
                    if newUrl.find("#post-") != -1:
                        index = newUrl.find("#post-")
                        newUrl = newUrl[:index]
                    if newUrl.find(".rss") != -1:
                        #print(">> Skipping .rss: %s" % newUrl)
                        #self.urlBlacklist += [newUrl]
                        #return False
                        continue
                    proper_directory = le_url.path.split("/")
                    if self.sub not in proper_directory and self.sub:
                        #return False
                        continue
                    if le_url.netloc == self.netloc and newUrl not in self.urlBlacklist + self.urlList: 
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

        elif tag == 'input':
            stat = 0
            for (key, value) in attrs:
                if key == 'type' and value == 'checkbox':
                    stat += 1
                    continue
                elif key == 'name' and value == 'type[post][thread_id]':
                    stat += 1
                    continue
                elif key == 'value' and stat == 2:
                    if value in self.BigDict:
                        self.BigDict[value] += [self.current_url]
                    else:
                        self.BigDict[value] = [self.current_url]
                    for url in self.BigDict[value]:
                        if url in self.urlList:
                            self.urlList.remove(url)
                            if self.verbose:
                                print(">> Removed %s as duplicate!" % url)

        elif tag == 'blockquote':
            for (key, value) in attrs:
                #print("  [ DEBUG ]  %s: %s" % (key, value))
                if self.li_main and not self.blockquote_main and key == 'class' and value == 'messageText SelectQuoteContainer ugc baseHtml':
                    #print("\n============================================")
                    #print("  [ DEBUG ] This is in 1st blockquote")
                    self.posts += 1
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
            '''
            if data.strip():
                print("%s said: " % self.li_name)
                print(data.strip())
            '''
            self.handle_parse(data.strip().lower())
            self.text_lock = True
        elif self.blockquote_quote and self.div_quote_main and not self.text_lock:
            '''
            print(" QUOTE %s: " % self.blockquote_name)
            print(data.strip())
            '''
            self.text_lock = True


    def handle_parse(self, data):
        for item in self.items:
            for key_term in self.key_terms:
                if data.find(item) > 0 and data.find(key_term) > 0:
                    if self.verbose:
                        print("--> Found item: [ %s: %s ]" % (key_term, item))


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


    def handle_url(self, url):
        try:
            response = urlopen(url)
            self.current_url = url
            if 'text/html' in response.headers['Content-Type']:
                htmlpage = response.read()
                le_html = htmlpage.decode("utf-8")
                le_html = re.sub("<br />", "", le_html)
                self.feed(le_html)
                #return True #le_html
            #else:
                #return ""
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
                self.handle_url(url)

                self.urlList.pop(0)
                self.urlBlacklist += [url]
                if len(self.urlBlacklist) % 10 == 0 and self.verbose:
                    url_total = len(self.urlList) + len(self.urlBlacklist)
                    url_remain = len(self.urlList)
                    url_complete = url_total - url_remain
                    print(">> Total Discovered URLs: %s; %s yet to parse. Posts parsed: %s" % (url_total, url_remain, self.posts))
                    with open('BigDict.json', 'w') as big_dict:
                        big_dict.write(json.dumps(self.BigDict, sort_keys=True, indent=4, separators=(',', ':')))

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
opts.add_argument('--db', help="database that will read and store information.",
        default=False)
opts.add_argument('--coll', help="The collection (table) to use in the database.",
        default='items')

opts.add_argument('-t', '--time', help="interval between each crawl.",
        type=float, default=False)
opts.add_argument('-d', '--depth', help="depth of crawling.",
        type=int, default=-1)

args = opts.parse_args()
if args.db:
    print(" Using Database: [ %s ] and table: [ %s ]" % (args.db, args.coll))

crawler = Crawler(args)
crawler.crawl()
print("\n===================================================================================\n" * 2)
