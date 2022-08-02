import warnings
import requests
import numpy as np
import json

from inspyhep import InspiresRecord

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

        self.full_record = self.get_full_records_from_query(self.author_query)
        self.full_json_records = json.loads(self.full_record)

        # how many records found?
        self.num_hits = self.full_json_records['hits']['total']

        # Fill in information about author's papers from the website response
        self.get_records_dict(self.full_json_records)

        # total number of citations
        self.citations = self.get_total_number_of_citations(self.inspires_records, )
        self.citations_noself = self.get_total_number_of_citations(self.inspires_records, cite_self=False)


    def get_total_number_of_citations(self, records: dict, cite_self=True) -> int:
        """ get_total_number_of_citations

        Parameters
        ----------
        records : dict
            the dictionary with asll the InspiresRecord instances
        cite_self : bool, optional
            if True, count self citations, otherwise do not. By default True

        Returns
        -------
        int
            total number of citations of the author
        """
        count = 0
        for record in records.values():
            if cite_self:
                count += record.citation_count
            else:
                count += record.ins_citation_count_without_self_citations
        return count

    def get_records_dict(self, json_records) -> dict:
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
        self.inspires_records = {}
        for record in json_records['hits']['hits']:
            r = InspiresRecord(record['metadata'])
            self.inspires_records[f'{r.texkey}'] = r
        return self.inspires_records

    def get_full_records_from_query(self, query) -> str:
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
