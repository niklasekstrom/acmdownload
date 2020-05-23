acmdownload
===========

Python script to automatically download metadata about research papers, starting with some paper and transitively downloading the most relevant papers, from ACM digital library.

## WARNING:
Do not try to modify the script to download many documents in parallel; at some point the dl.acm.org site will notice this and temporarily block your IP.

# Installing and running:

* Download and install the latest release of [Python 3](https://www.python.org/downloads/).
* Install the [requests](https://pypi.org/project/requests/) library: run the command pip3 install requests.

Run using the command line python acmdownload.py.

# Finding the UID of a paper

Search for a paper on [dl.acm.org](dl.acm.org) and go to its page. For example the page for the paper "Spanner: Google's globally-distributed database" from OSDI'12 has the url [https://dl.acm.org/doi/10.5555/2387880.2387905](https://dl.acm.org/doi/10.5555/2387880.2387905). The DOI is the string 10.5555/2387880.2387905.

Change the doi global variable in the script to the DOI for your paper. The documents_to_download global variable is the total number of documents to include in the set before ranking them according to number of references from within the set.
