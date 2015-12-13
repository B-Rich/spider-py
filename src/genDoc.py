from pymongo import MongoClient
import json

client = MongoClient()
db = client.crawler
coll = db.items
WriteDB = True

def genDoc(name, aliases, url, price):
    doc = {
            "name": name,
            "alias": aliases,
            "url": url,
            "price": price
            }
    #doc = json.dumps(doc_str)
    return doc



while WriteDB:
    try:
        in_n = input("Item name: ")
        if not in_n:
            print("Bad name.")
            continue
        in_a = input("Aliases split by commas: ").split(',')
        in_u = input("URLs split by commands: ").split(',')
        in_p = input("Price: ")
        if not in_p:
            in_p = 0.00
        doc = genDoc(in_n, in_a, in_u, in_p)
        print(doc)
        coll.insert(doc)
        print(" - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")

    except KeyboardInterrupt:
        print("\nCaught a keyboard interrupt. Exiting.")
        WriteDB = False



