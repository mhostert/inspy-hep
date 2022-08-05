import warnings
from typing import Union
import json
import requests
from pylatexenc.latexencode import unicode_to_latex
from dataclasses import dataclass
import datetime

class InspireRecord:
    """Class for storing Inspire record information."""

    def __init__(self, info: Union[dict,str], cap_authors = 100):

        # if texkey was passed, then request json info from Inspire API
        if type(info) is str:
            _records_found = json.loads(self.get_record_from_inspire_query(texkey=info))['hits']['hits']
            if len(_records_found)>1:
                warnings.warn(f'More than one record found with key = {info}. Reading the first one.')
            self.json_record = _records_found[0]['metadata']
        # else, assume we have the json data already
        else:
            self.json_record = info
        
        self._cap_authors = cap_authors

        # Load all inspire record attributes as "ins_{key}"
        for key in self.json_record.keys():
            setattr(self, f'ins_{key}', self.json_record[key])

        # main key that identifies a record (used by latex)
        try:
            self.texkey = self.ins_texkeys[0]
        except AttributeError:
            warnings.warn(f"No texkey found for record {self.json_record}. Skipping it.")
            return None

        # title
        self.title = self.ins_titles[0]['title'] if hasattr(self, 'ins_titles') else None


        # main key that identifies a record (used by latex)
        self.document_type = self.ins_document_type[0]

        # first author
        self.first_author = unicode_to_latex(self.ins_first_author['full_name'])
        
        # number of authors
        self.author_count = self.ins_author_count
        
        # list of first, last, and full names
        self.authors_firstname = []
        self.authors_lastname = []
        self.authors_fullname = []
        for a in self.ins_authors:
            if 'first_name' in a.keys():
                self.authors_firstname.append(a['first_name'])
            else:
                self.authors_firstname.append('')
            if 'last_name' in a.keys():
                self.authors_lastname.append(a['last_name'])
            else:
                self.authors_lastname.append('')
            if 'full_name' in a.keys():
                self.authors_fullname.append(a['full_name'])
            else:
                self.authors_fullname.append('')
        
        # 'Salam, G. and Weinber, S.'
        self.authorlist = self.get_authorlist()
        # 'G. Salam, S. Weinberg'
        self.authorlist_bibtex_style = self.get_authorlist_bibtex_style()
        
        self.capped_at_1_authorlist = f'{self.authors_lastname[0]} et al'
        self.capped_at_3_authorlist = self.get_authorlist(cap=3, first_name=False)

        self.capped_at_1_authorlist_fullname = self.get_authorlist(cap=1)
        self.capped_at_3_authorlist_fullname = self.get_authorlist(cap=3)

        ''' Date information. Tries the following:
            1 - Inspire earliest_date
            2 - preprint date
            3 - Journal
            4 - info in texkeys
        '''
        try:
            self.year, self.month, self.day = self.get_date(self.json_record['earliest_date'])
        except KeyError:
            try:
                self.year, self.month, self.day = self.get_date(self.json_record['preprint_date'])
            except KeyError:
                try:
                    self.year, self.month, self.day = int(self.json_record['publication_info'][0]['year']), 1, 1
                except KeyError:
                    try:
                        self.year, self.month, self.day = self.get_year_from_texkeys(self.json_record['texkeys']), 1, 1
                    except KeyError:
                        warnings.warn("No date found in Inspire record.")
                        self.year = 1
                        self.month = 1
                        self.day = 1

        self.date = datetime.date(int(self.year), int(self.month), int(self.day))


        # Title of the Journal
        try:
            self.pub_title = self.json_record['publication_info'][0]['journal_title']
        except KeyError:
            self.pub_title = ''
        
        # Journal Volume
        try:
            self.pub_volume = self.json_record['publication_info'][0]['journal_volume']
        except KeyError:
            self.pub_volume = ''
        
        # Journal Issue
        try:
            self.pub_issue = self.json_record['publication_info'][0]['journal_issue']
        except KeyError:
            self.pub_issue = ''

        # Journal article id
        try:
            self.pub_artid = self.json_record['publication_info'][0]['artid']
        except KeyError:
            self.pub_artid = ''
        
        # publication id 
        try:
            self.pub_year = int(self.json_record['publication_info'][0]['year'])
        except KeyError:
            self.pub_year = ''

        # Is it published
        self.published = (len(self.pub_title)>0)
        self.journal = self.pub_title if self.published else None
        self.pub_info = f'{self.pub_title} {self.pub_volume} ({self.pub_year}) {self.pub_issue} {self.pub_artid}, {self.year}' if self.published else None

        # Is it a proceedings?
        self.proceedings = (['document_type'] == 'conference paper')
        # Is it citeable according to inspire? (can be reliably tracked)
        self.citeable = self.ins_citeable if hasattr(self, 'ins_citeable') else False

        # arXiv number (xxxx.yyyyy)
        try:
            self.arxiv_number = self.json_record['arxiv_eprints'][0]['value']
        except KeyError:
            self.arxiv_number = None
        
        # arXiv category (e.g., hep-ph)
        try:
            self.primary_arxiv_category = self.json_record['primary_arxiv_category']
        except KeyError:
            self.primary_arxiv_category = None

        # arxiv url
        if self.arxiv_number is not None:
            self.arxiv_url = f'https://arxiv.org/abs/{self.arxiv_number}'
        else:
            self.arxiv_number = None

        self.citation_count = self.ins_citation_count
        self.ins_citation_count_without_self_citations = self.ins_citation_count_without_self_citations
        self.citation_count_no_self = self.ins_citation_count_without_self_citations

    def get_bibtex(self) -> str:
        """get_bibtex get the bibtex entry for a record from the Inspire key

        """
        response = requests.get(f"https://inspirehep.net/api/literature?q=texkeys:{self.texkey}&format=bibtex")
        if response.status_code == 200:
            return (response.content).decode("utf-8")
        else:
            warnings.warn(f"Could not find Inspire entry for texkey={self.key}.")
            return None
            

    def __repr__(self, cap_author_list=5) -> str:
        if self.author_count > cap_author_list:
            authors_shown = self.capped_at_1_authorlist
        else:
            authors_shown = self.capped_at_3_authorlist
        
        if self.arxiv_number is not None:
            if self.primary_arxiv_category is not None:
                arxiv_suffix = f', arXiv:{self.arxiv_number} [{self.primary_arxiv_category[0]}]'
            else:
                arxiv_suffix = f', arXiv:{self.arxiv_number}.'
        else:
            arxiv_suffix = ''

        if self.published:
            _repr = f'{authors_shown}, {self.pub_info}{arxiv_suffix}.'
        elif self.document_type == 'article':
            _repr = f'{authors_shown}, preprint, {self.year}{arxiv_suffix}.'
        elif self.document_type == 'conference paper' or self.document_type == 'proceedings' or self.document_type == 'report':
            _repr = f'{authors_shown}, proceedings, {self.year}{arxiv_suffix}.'
        elif self.document_type == 'thesis':
            _repr = f'{authors_shown}, thesis, {self.year}{arxiv_suffix}.'
        else:
            _repr = f'{authors_shown}, {self.year}{arxiv_suffix}.'
        return _repr.replace("   ", " ").replace("  ", " ").replace(" ,", ",").replace(" .", ".")

    def get_date(self, date: str) -> tuple:
        try:
            y, m, d = date.split(sep='-')
        except ValueError:
            try:
                y, m = date.split(sep='-')
                d = '1'
            except ValueError:
                y = date
                m = '1'
                d = '1'
        return y, m, d

    def get_year_from_texkeys(self, texkey: str) -> int:
        return int(texkey.partition(":")[2][:4])

    def name_force_initials(self, name: str) -> str:
        return name.replace(". ",".").replace(".",". ")

    def get_authorlist(self, cap: int = 2000, first_name: bool = True) -> str:
        
        if cap == 1:
            return f'{self.authors_lastname[0]} {"et al" if self.author_count > 1 else ""}'
        else:
            nauthors = min(self.author_count, cap)
            # string of author lists in different formats 
            _full_author_list = [] 
            for f,l in zip(self.authors_firstname[:nauthors-1],self.authors_lastname[:nauthors-1]):
                if first_name:
                    _full_author_list.append(self.name_force_initials(f'{f} {l}, '))
                else:
                    _full_author_list.append(self.name_force_initials(f'{l}, '))
            if first_name:
                last_entry = self.name_force_initials(f'{self.authors_firstname[-1]} {self.authors_lastname[-1]}')
            else:
                last_entry = self.name_force_initials(f'{self.authors_lastname[-1]}')
            return ''.join(_full_author_list) + last_entry

    def get_authorlist_bibtex_style(self, cap: int = 2000) -> str:
        
        if cap == 1:
            return f'{self.authors_lastname[0]} {"et al" if self.author_count > 1 else ""}'
        else:
            if self.author_count > 2000:
                warnings.warn("Capping at 2000 authors in record {self.texkey}.")
                cap = 2000
            else:
                nauthors = min(self.author_count, cap)
                _full_author_list_bibtex_style = [] 
                for f in self.authors_fullname[:nauthors-1]:
                    _full_author_list_bibtex_style.append(f'{f} and ')
                return ''.join(_full_author_list_bibtex_style) + f'{self.authors_fullname[-1]}'


    def get_record_from_inspire_query(self, texkey: str) -> str:
        """get_record_from_inspire_query get the Inspire record from url

        Parameters
        ----------
        texkey : str
            tex key of the record to be used in the Inspire API query

        Returns
        -------
        str
            full string output from the Inpires query
        """
        # Query Inspire-HEP for author's information
        _inspire_query = 'https://inspirehep.net/api/literature'
        self.record_query = f'{_inspire_query}?q=texkeys:{texkey}'

        # Load the full record of the author
        response = requests.get(self.record_query)
        if response.status_code == 200:
            return (response.content).decode("utf-8")
        else:
            warnings.warn(f"Could not find Inspire entry for author identified = {self.identifier}.")
            return None


            