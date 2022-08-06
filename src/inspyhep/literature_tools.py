import warnings
from inspect import signature
from typing import Union
import json
import requests
from pylatexenc.latexencode import unicode_to_latex
import datetime
import time

from inspyhep import metadata

class InspireRecord:
    """Class for storing Inspire record information."""

    def __init__(self, input: Union[dict,str], cap_authors: int =100):

        self.input = input
        # if texkey was passed, then request json info from Inspire API
        if type(self.input) is str:
            _content = self.get_record_from_inspire_query(texkey=self.input)
            _records_found = json_load_hits(_content)
            if len(_records_found)>1:
                warnings.warn(f'More than one record found with key = {self.input}. Reading the first one.')
                _records_found = [_records_found[0]]
            elif len(_records_found)==0:
                raise ValueError(f"No record found with requests.get({self.record_query}) for input texkey '{self.input}'")
            else:
                self.json_record = _records_found[0]['metadata']
        # else, assume we have the json data already
        else:
            self.json_record = self.input

        self._cap_authors = cap_authors

        # Load all inspire record attributes as "ins_{key}"
        for key in self.json_record.keys():
            setattr(self, f'ins_{key}', self.json_record[key])

        # main key that identifies a record (used by latex)
        try:
            self.texkey = self.ins_texkeys[0]
        except AttributeError:
            raise ValueError(f"No texkey found for record {self.json_record}.")

        # title
        self.title = self.ins_titles[0]['title'] if hasattr(self, 'ins_titles') else None

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


        # main key that identifies a record (used by latex)
        self.document_type = self.ins_document_type[0]

        # first author
        self.first_author = unicode_to_latex(self.ins_first_author['full_name'])
        
        # number of authors
        self.author_count = self.ins_author_count
        
        # create a dictionary of author dataclasses
        self.authors = {}
        for a in self.ins_authors:
            meta = metadata.author(**a)
            self.authors[meta.bai] = meta
            self.authors[meta.bai].last_update = self.date

        # This loops over all possible author properties and creates lists of these for all authors of this record
        # called authors_{prop} (e.g., authors_first_name = ['Alice', 'Bob'])
        for prop in signature(metadata.author).parameters.keys():
            if prop == 'affiliations':
                setattr(self, f'authors_{prop}', [ a[prop][0]["value"] if prop in a.keys() else '' for a in self.ins_authors])
            else:
                setattr(self, f'authors_{prop}', [ a[prop] if prop in a.keys() else '' for a in self.ins_authors])

        # 'Salam, G. and Weinber, S.'
        self.authorlist = self.get_authorlist()
        # 'G. Salam, S. Weinberg'
        self.authorlist_bibtex_style = self.get_authorlist_bibtex_style()
        
        self.capped_at_1_authorlist = f'{self.authors_last_name[0]} et al'
        self.capped_at_3_authorlist = self.get_authorlist(cap=3, first_name=False)

        self.capped_at_1_authorlist_full_name = self.get_authorlist(cap=1)
        self.capped_at_3_authorlist_full_name = self.get_authorlist(cap=3)


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
            self.arxiv_url = None

        self.citation_count = self.ins_citation_count
        self.ins_citation_count_without_self_citations = self.ins_citation_count_without_self_citations
        self.citation_count_no_self = self.ins_citation_count_without_self_citations

    def get_bibtex(self) -> str:
        """get_bibtex get the bibtex entry for a record from the Inspire key"""
        return make_request(f"https://inspirehep.net/api/literature?q=texkeys:{self.texkey}&format=bibtex")
    
    def arxiv_url_builder(self, name: str, format: str = 'latex') -> str:
        
        if self.arxiv_url is not None:
            rb = '}'
            lb = '{'
            bs = '\\'
            ARXIV_URLS = {
                            'latex': f'{bs}href{lb}{name}{rb}{lb}self.arxiv_url{rb}',
                            'latex_url': f'{bs}url{lb}self.arxiv_url{rb}',
                            #
                            'markdown': f'[{name}]({self.arxiv_url})',
                            'markdown_url': f'{self.arxiv_url}',
                            #
                            'html': f'<a href="{self.arxiv_url}">{name}</a>',
                            'html_url': f'<a href="{self.arxiv_url}">{self.arxiv_url}</a>',
                        }

            try:
                return ARXIV_URLS[format]
            except KeyError:
                warnings.warn("arXiv URL in format '{format}' not implemented.")
                return None
        else:
            return ''

        

    def __repr__(self, cap_author_list=5, 
                        arxiv_category: bool = True,
                        arxiv_url=None,
                        ) -> str:

        if self.author_count > cap_author_list:
            authors_shown = self.capped_at_1_authorlist
        else:
            authors_shown = self.capped_at_3_authorlist
        
        if self.arxiv_number is not None:
            if self.primary_arxiv_category is not None and arxiv_category:
                arxiv_suffix = f', arXiv:{self.arxiv_number} [{self.primary_arxiv_category[0]}]'
            else:
                arxiv_suffix = f', arXiv:{self.arxiv_number}'
            if arxiv_url is not None:
                arxiv_suffix = f', {self.arxiv_url_builder(arxiv_suffix[2:], format=arxiv_url)}'

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
            return f'{self.authors_last_name[0]} {"et al" if self.author_count > 1 else ""}'
        else:
            nauthors = min(self.author_count, cap)
            # string of author lists in different formats 
            _full_author_list = [] 
            for f,l in zip(self.authors_first_name[:nauthors-1],self.authors_last_name[:nauthors-1]):
                if first_name:
                    _full_author_list.append(self.name_force_initials(f'{f} {l}, '))
                else:
                    _full_author_list.append(self.name_force_initials(f'{l}, '))
            if first_name:
                last_entry = self.name_force_initials(f'{self.authors_first_name[-1]} {self.authors_last_name[-1]}')
            else:
                last_entry = self.name_force_initials(f'{self.authors_last_name[-1]}')
            return ''.join(_full_author_list) + last_entry

    def get_authorlist_bibtex_style(self, cap: int = 2000) -> str:
        
        if cap == 1:
            return f'{self.authors_last_name[0]} {"et al" if self.author_count > 1 else ""}'
        else:
            if self.author_count > 2000:
                warnings.warn("Capping at 2000 authors in record {self.texkey}.")
                cap = 2000
            else:
                nauthors = min(self.author_count, cap)
                _full_author_list_bibtex_style = [] 
                for f in self.authors_full_name[:nauthors-1]:
                    _full_author_list_bibtex_style.append(f'{f} and ')
                return ''.join(_full_author_list_bibtex_style) + f'{self.authors_full_name[-1]}'


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

        return make_request(self.record_query)


def make_request(query: str) -> str:
    """make_request make request to website

    Parameters
    ----------
    query : str
        url with query to be used by requests.get().

    Returns
    -------
    str
        response of the request in utf-8 format string
    """

    # Attempting to request data
    for attempt in range(10):
        # Try
        try:
            response = requests.get(query)
            response.raise_for_status()
            try:
                return (response.content).decode("utf-8").replace("$", "")
            except AttributeError:
                warnings.warn('Could not decode website response.content = {response.content}. Skipping decoding.')
                return response.content

        # Too many requests
        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:
                warnings.warn("You have exceeded the number of requests in 5s set by Inspire. Waiting 5s to try again.")
                time.sleep(5 + 0.01)
            else:
                warnings.warn(f"Could not access Inspire data (request status_code = {response.status_code}).")
                warnings.warn(err)
                warnings.warn("Trying again...")
                return None
    else:
        warnings.warn(f"Could not access Inspire data using query = {response.url} (request status_code = {response.status_code})")
        return None


def json_load_hits(content: str) -> list:
    """json_load_hits Loads the content of the inspire response into a json format

        Note: I do not believe there is any useful information in the top dictionary, 
        so we always take the value of ['hits']['hits'].

    Parameters
    ----------
    content : str
        content in utf-8 formatted string from requests.get

    Returns
    -------
    list
        the list of hits found.
    """
    try:
        loaded = json.loads(content)
    except AttributeError:
        warnings.warn(f"Not able to load the content of the Inspire request with json. Content = {content}")
        return None
    
    try:
        return loaded['hits']['hits']
    except KeyError:
        return loaded
