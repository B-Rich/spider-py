{ "Current-Version": "0.1", "Tag": "v0.1-alpha" }
### Webcrawler/Spider 
A webcrawler designed around exploration of new content in the search of specified items in a database. It will store new information either locally in a db or remotely via PUT requests.

### Installation:
```bash
# Git way of installation:
git clone https://github.com/0x1p2/spider-py
cd spider-py/src
python main.py
```

#### Features:
+ Scans an html page for additional links. 
+ Filters duplicates, previous processed, and also links that are in the queue.
+ Loads information to search for from a database
+ Error recovery implemented on bad URLs and 403/404s.

##### Versions:
+ v0.1-alpha  (Dec 11th, 2015) - Intial commit of a working spider.
