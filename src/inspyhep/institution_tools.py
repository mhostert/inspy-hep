import warnings
import requests
import numpy as np
import json
import datetime

from inspyhep.literature_tools import InspireRecord, make_request, json_load_hits

class Institution():
    def __init__(self, identifier, max_hits: int =1000):
        """ Institution()

            Parameters
            ----------
            identifier : str
                the institutions's identifier number (e.g. '1119124' for ICTP-SAIFR Sao Paulo`)
             max_hits: str
                the maximum number of hits in query

        """

        self.identifier    = identifier
        self.snapshot_date = datetime.datetime.now()

        # Query Inspire-HEP for author's information
        self.author_query = f'https://inspirehep.net/api/institutions?size={self.max_papers}&q={self.identifier}'

        self.full_record = self.get_full_records_from_query()
        self.full_json_records = json_load_hits(self.full_record)

        # how many records found?
        self.num_hits = len(self.full_json_records)

        # Fill in information about author's papers from the website response
        self.inspire_records = self.get_records_dict(self.full_json_records)

        # total number of citations
        self.citations = self.get_total_number_of_citations(self.inspire_records, )
        self.citations_noself = self.get_total_number_of_citations(self.inspire_records, self_cite=False)

