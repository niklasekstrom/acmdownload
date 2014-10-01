acmdownload
===========

Python script to automatically download metadata about research papers, starting with some paper and transitively downloading the most relevant papers, from ACM digital library.

## WARNING:
Do not try to modify the script to download many documents in parallel; at some point the dl.acm.org site will notice this and temporarily block your IP.

# Installing and running:

* Download and install the latest release of [Python 2](https://www.python.org/downloads/).
* Download and install pip: download [this script](https://bootstrap.pypa.io/get-pip.py) and run python get-pip.py at the command line. [More info](https://pip.pypa.io/en/latest/installing.html).
* Install the [requests](http://docs.python-requests.org/en/latest/) library: run the command pip install requests. [More info](http://docs.python-requests.org/en/latest/user/install/).

Run using the command line python acmdownload.py.

# Finding the UID of a paper

Search for a paper on [dl.acm.org](dl.acm.org) and go to its page. For example the page for the paper "Spanner: Google's globally-distributed database" from OSDI'12 has the url [http://dl.acm.org/citation.cfm?id=2387880.2387905&coll=DL&dl=GUIDE&CFID=236350197&CFTOKEN=90827288](http://dl.acm.org/citation.cfm?id=2387880.2387905&coll=DL&dl=GUIDE&CFID=236350197&CFTOKEN=90827288). The UID is the string 2387905, which is the part of the id argument after the dot. If there is no dot then the UID is the entire id argument.

Change the uid global variable in the script to the uid for your paper. The documents_to_download global variable is the total number of documents to include in the set before ranking them according to number of references from within the set.
