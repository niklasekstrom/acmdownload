from html.parser import HTMLParser
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
        self.in_title = False
        self.in_references_item = False
        self.refs = []
        self.cbu = None
        self.title = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'h1' and 'citation__title' in d['class']:
            self.in_title = True
        elif tag == 'a' and 'data-ajaxurl' in d:
            cited_by_url = d['data-ajaxurl']
            if cited_by_url.startswith('/action/ajaxShowCitedBy'):
                self.cbu = cited_by_url
        elif self.in_references_item:
            if tag == 'a':
                link = d['href']
                if link.startswith('https://dl.acm.org/doi/'):
                    link = link[23:]
                    self.refs.append(link)
        else:
            if tag == 'li' and 'class' in d and 'references__item' in d['class']:
                self.in_references_item = True

    def handle_endtag(self, tag):
        if self.in_title:
            self.in_title = False
        elif self.in_references_item:
            if tag == 'li':
                self.in_references_item = False

    def handle_data(self, data):
        if self.in_title:
            self.title = data

class CitationParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'a':
            link = d['href']
            if link.startswith('https://doi.org/'):
                link = link[16:]
                self.links.append(link)

def download_doc(doi):
    r = requests.get('https://dl.acm.org/doi/' + doi)
    page_parser = PageParser()
    page_parser.feed(r.text)

    doc = {'references': page_parser.refs}

    if page_parser.title:
        doc['title'] = page_parser.title

    if page_parser.cbu:
        r = requests.get('https://dl.acm.org' + page_parser.cbu)
        citation_parser = CitationParser()
        citation_parser.feed(r.text)
        doc['citedby'] = citation_parser.links
    else:
        doc['citedby'] = []

    r = requests.post('https://dl.acm.org/action/exportCiteProcCitation', data={
        'dois': doi,
        'targetFile': 'custom-bibtex',
        'format': 'bibTex'
    })

    j = json.loads(r.text)
    kvs = list(j['items'][0].items())[0][1]

    if 'title' not in doc and 'title' in kvs:
        doc['title'] = kvs['title']

    for k in ['original-date', 'issued']:
        if k in kvs:
            date = kvs[k]
            ds = map(str, date['date-parts'][0])
            doc['date'] = '/'.join(ds)
            break

    if 'author' in kvs:
        l = []
        for a in kvs['author']:
            name = ''
            if 'given' in a:
                name += a['given']
            if 'family' in a:
                if name:
                    name += ' '
                name += a['family']
            l.append(name)
        doc['authors'] = ', '.join(l)

    return doc

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
                print('No documents are missing, stopping.')
                exit()
            queue |= get_top_ranked(docs, missing)

        uid = queue.pop()
        if uid in all_docs:
            print('%s: Taking %s from store' % (len(docs) + 1, uid))
            doc = all_docs[uid]
        else:
            print('%s: Downloading %s...' % (len(docs) + 1, uid))
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
        print('%3d, %8s, %3d (%3d), %s. %s: %s' % (i + 1, uid, cnt, len(doc['citedby']), doc['date'] if 'date' in doc else '??/??/????', doc['authors'] if 'authors' in doc else '???', doc['title'] if 'title' in doc else '???'))

def info(doc):
    for (key, value) in doc.items():
        if key not in ['references', 'citedby']:
            print('%s: %s' % (key, value))
    print('references: %s' % len(doc['references']))
    print('cited by: %s' % len(doc['citedby']))

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

doi = '10.5555/2387880.2387905'
documents_to_download = 300
docs = download(doi, documents_to_download)
info(docs[doi])
mostreferenced(docs, doi)
