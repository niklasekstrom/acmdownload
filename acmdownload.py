from HTMLParser import HTMLParser
import json
import requests
import sqlite3

FILE_NAME = 'docs.json'
DB_NAME = 'docs.db'

def load_docs_file():
    try:
        with open(FILE_NAME, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_docs_file(docs):
    with open(FILE_NAME, 'w') as f:
        json.dump(docs, f)

def copy_file_to_db():
    docs = load_docs_file()
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS docs (uid TEXT NOT NULL PRIMARY KEY, doc TEXT NOT NULL)')
    con.commit()
    for uid in docs:
        doc = docs[uid]
        cur.execute('INSERT INTO docs (uid, doc) VALUES (?, ?)', (uid, json.dumps(doc, ensure_ascii = False)))
    con.commit()
    con.close()

def load_docs():
    docs = {}
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS docs (uid TEXT NOT NULL PRIMARY KEY, doc TEXT NOT NULL)')
    con.commit()
    cur.execute('SELECT uid, doc FROM docs')
    for row in cur.fetchall():
        docs[row[0]] = json.loads(row[1])
    con.close()
    return docs

def save_doc(uid, doc):
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute('INSERT INTO docs (uid, doc) VALUES (?, ?)', (uid, json.dumps(doc, ensure_ascii = False)))
    con.commit()
    con.close()

class PageParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.doc = {'references':[], 'citedby':[]}
        self.section = None

    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            d = dict(attrs)
            if 'name' in d and d['name'].startswith('citation_'):
                name = d['name'][9:]
                content = d['content']
                self.doc[name] = content
        elif tag == 'a':
            d = dict(attrs)
            if 'name' in d:
                name = d['name']
                self.section = name if name in ['references', 'citedby'] else None
            if self.section is not None and 'href' in d and d['href'].startswith('citation.cfm?'):
                query = d['href'][13:]
                for p in query.split('&'):
                    a = p.split('=')
                    if a[0] == 'id':
                        self.doc[self.section].append(a[1])

cookies = {}
def download_doc(uid):
    global cookies
    url = 'http://dl.acm.org/citation.cfm?id=' + uid + '&preflayout=flat'
    r = requests.get(url, cookies = cookies, headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.114 Safari/537.36'})
    cookies.update(r.cookies)
    parser = PageParser()
    parser.feed(r.text)
    return parser.doc

def get_top_ranked(docs, missing):
    r = {uid:0 for uid in missing}
    c = {uid:0 for uid in missing}
    for doc in docs.values():
        for uid in doc['references']:
            if uid in r:
                r[uid] = r[uid] + 1
        for uid in doc['citedby']:
            if uid in c:
                c[uid] = c[uid] + 1
    queue = set()
    queue.add(max(r.items(), key = lambda x: x[1])[0])
    queue.add(max(c.items(), key = lambda x: x[1])[0])
    return queue

def download(orig, num_docs):
    all_docs = load_docs()

    docs = {}
    uids = set([orig])
    queue = set([orig])

    while len(docs) < num_docs:
        if len(queue) == 0:
            missing = uids - set(docs.keys())
            if len(missing) == 0:
                print 'No documents are missing, stopping.'
                exit()
            queue |= get_top_ranked(docs, missing)

        uid = queue.pop()
        if uid in all_docs:
            print '%s: Taking %s from store' % (len(docs) + 1, uid)
            doc = all_docs[uid]
        else:
            print '%s: Downloading %s...' % (len(docs) + 1, uid)
            doc = download_doc(uid)
            all_docs[uid] = doc
            save_doc(uid, doc)
            #save_docs(all_docs)

        docs[uid] = doc
        doc_uids = set(doc['references']) | set(doc['citedby'])
        uids |= doc_uids

        if uid == orig:
            queue |= doc_uids - set([orig]) # Possibly unnecessary, to guard against paper that references itself.

    return docs

def mostreferenced(docs, orig):
    rank = {uid:0 for uid in docs}

    for doc in docs.values():
        for uid in set(doc['references']):
            if uid in rank:
                rank[uid] = rank[uid] + 1

    rank = sorted(rank.items(), key = lambda x: -x[1])

    for i in range(min(100, len(docs))):
        uid, cnt = rank[i]
        doc = docs[uid]
        print '%3d, %8s, %3d (%3d), %s. %s: %s' % (i + 1, uid, cnt, len(doc['citedby']), doc['date'] if 'date' in doc else '??/??/????', doc['authors'] if 'authors' in doc else '???', doc['title'] if 'title' in doc else '???')

def info(doc):
    for (key, value) in doc.items():
        if key not in ['references', 'citedby']:
            print '%s: %s' % (key, value)
    print 'references: %s' % len(doc['references'])
    print 'cited by: %s' % len(doc['citedby'])

def remove_uid_file(uid):
    docs = load_docs_file()
    if uid in docs:
        del docs[uid]
    save_docs_file(docs)

def remove_uid(uid):
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute('DELETE FROM docs WHERE uid=?', (uid,))
    con.commit()
    con.close()

def remove_missing_meta():
    docs = load_docs()
    uids = list(docs.keys())
    for uid in uids:
        doc = docs[uid]
        if len(set(doc.keys()) - set(['references', 'citedby'])) == 0:
            remove_uid(uid)
            del docs[uid]
    #save_docs(docs)

uid = '2387905'
documents_to_download = 250
docs = download(uid, documents_to_download)
info(docs[uid])
mostreferenced(docs, uid)
#remove_uid('2611484')
#remove_missing_meta()
