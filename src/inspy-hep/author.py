import requests
import numpy as np
import json

class Author():
    def __init__(self, identifier, max_papers=1000):
        """ Author()

            Parameters
            ----------
            identifier : str
                the author's identifier string (e.g. 'Steven.Weinberg.1')
            max_papers : int, optional
                Number of papers requested from INSPIRE-HEP, by default 1000


            Modified from
                * https://github.com/efranzin/python 
                * https://github.com/motloch/track_inspire-hep_citations

        """

        self.identifier    = identifier
        self.max_papers    = max_papers
        self.max_title_length = 100


        # Query Inspire-HEP for author's information
        _inspire_query = 'https://inspirehep.net/api/literature?sort=mostrecent'
        self.author_query = f'{_inspire_query}&size={self.max_papers}&q=a%20{self.identifier}'

        self.full_record = self.get_full_record_from_query(self.author_query)
        self.json_record = json.loads(self.full_record)

        # how many records found?
        self.num_hits = self.json_record['hits']['total']

        # Fill in information about author's papers from the website response
        for i in range(num_hits):
            biblio[i]['id']          = data['hits']['hits'][i]['id']
            biblio[i]['title']       = data['hits']['hits'][i]['metadata']['titles'][0]['title']
            biblio[i]['cits']        = data['hits']['hits'][i]['metadata']['citation_count']
            biblio[i]['cits_noself'] = data['hits']['hits'][i]['metadata']['citation_count_without_self_citations']


    def get_record_json(self, json_record) -> dict:
        """get_record_json get a dictionary of all inspire records for this author

        Parameters
        ----------
        json_record : str
            str with json output of inspires query

        Returns
        -------
        dict
            a dictionary with keys containing instances of the InspireRecord class,
            accessible with inspire texkeys (e.g., dic['weinberd:2002abc'])
        """
        self.inspire_record = {}
        for record in json_record['hits']['hits']:
            r = InspiresRecord(record)
            self.inspire_record[f'{r.texkey}'] = r
        return self.inspire_record

    def get_full_record_from_query(self, query) -> str:
        """get_full_record_from_query get the full result of the author query to Inspires

        Parameters
        ----------
        query : str
            url string with the author query following Inspires API

        Returns
        -------
        str
            full string output from the Inpires query
        """

        # Load the full record of the author
        response = requests.get(self.author_query)
        if response.status_code == 200:
            return (response.content).decode("utf-8")
        else:
            print(f"Could not find Inspire entry for author identified = {self.identifier}.")
            return None

    def get_bibtex_from_key(self, key) -> str:
        """get_bibtex_from_key get the bibtex entry for a record from the Inspires key

        Parameters
        ----------
        key : str
            Inspires key for the record (e.g., Weinberg:1967tq)
        """
        response = requests.get(f"https://inspirehep.net/api/literature?q=texkeys:{key}&format=bibtex")
        if response.status_code == 200:
            return (response.content).decode("utf-8")
        else:
            print(f"Could not find Inspire entry for texkey={key}.")
            return None
            
# Print the total number of citations and the total number of citations excluding self cites
print(
        '\nTotal number of citations: ', 
        sum(biblio['cits']), 
        '; Excluding self cites: ', 
        sum(biblio['cits_noself']), 
        '\n',
        sep=''
    )

# Function to save current snapshot of the author's citations
def save_snapshot():
    """
    Saves a current snapshot of the bibliography. 
    If NEED_WRITE_CONFIRM is True, asks the user for permission first.
    """

    if NEED_WRITE_CONFIRM:
        rewrite = input('\nDo you want to save a snapshot [y/n]? ')
        if rewrite != 'y':
            print('Not saved.')
            return

    np.save(FILENAME, biblio)
    print('Saved.')
    return

#If snapshot does not exist, create it (potentially confirming with the user) and exit
from os.path import exists
if not exists(FILENAME):
    save_snapshot()
    exit()

#Load snapshot
old_biblio = np.load(FILENAME)

#Get a set of paper IDs that were added/removed/stayed
new_paper_ids = set(    biblio['id'])
old_paper_ids = set(old_biblio['id'])

added_paper_ids   = new_paper_ids.difference(old_paper_ids)
removed_paper_ids = old_paper_ids.difference(new_paper_ids)
stayed_paper_ids  = new_paper_ids.intersection(old_paper_ids)

#Keep track of whether we had any changes
changes_present = False

#Print information about papers that were added or removed
for i in removed_paper_ids:
    changes_present = True

    idx       = np.argmax(old_biblio['id'] == i)
    title     = old_biblio[idx]['title'] 
    num_cites = old_biblio[idx]['cits']

    if num_cites == 1:
        print('Removed paper: "' + title + '" with ' +  str(num_cites) + ' citation')
    else:
        print('Removed paper: "' + title + '" with ' +  str(num_cites) + ' citations')

for i in added_paper_ids:
    changes_present = True

    idx       = np.argmax(biblio['id'] == i)
    title     = biblio[idx]['title'] 
    num_cites = biblio[idx]['cits']

    if num_cites == 1:
        print('Added paper: "' + title + '" with ' +  str(num_cites) + ' citation')
    else:
        print('Added paper: "' + title + '" with ' +  str(num_cites) + ' citations')

#For papers not added or removed, check if number of citations has changed
for i in stayed_paper_ids:
    idx_old       = np.argmax(old_biblio['id'] == i)
    idx_new       = np.argmax(    biblio['id'] == i)
    title         = biblio[idx_new]['title'] 
    num_new_cites = biblio[idx_new]['cits'] - old_biblio[idx_old]['cits']

    if num_new_cites != 0:
        changes_present = True

        if   num_new_cites == 1:
            print('1 new citation: "' + title + '"')
        elif num_new_cites == -1:
            print('1 citation removed: "' + title + '"')
        elif num_new_cites  > 1:
            print(str(num_new_cites) + ' new citations: "' + title + '"')
        elif num_new_cites  < -1:
            print(str(abs(num_new_cites)) + ' citations removed: "' + title + '"')

#Save current snapshot if anything changed (potentially confirming with the user)
if changes_present:
    save_snapshot()