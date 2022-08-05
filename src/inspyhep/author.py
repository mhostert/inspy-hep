import warnings
import requests
import numpy as np
import json

from inspyhep.inspires_tools import InspiresRecord
import requests

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
        self.inspires_records = self.get_records_dict(self.full_json_records)

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
        inspires_records = {}
        for record in json_records['hits']['hits']:
            r = InspiresRecord(record['metadata'])
            inspires_records[f'{r.texkey}'] = r
        return inspires_records

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

    def nice_publication_list(self, include_title: bool = True,
                                    author_count_to_exclude: int = 10,
                                    include_citation: bool =True,
                                    def_well_cited: int =10,
                                    arxiv: bool =True,
                                    split_peer_review: bool = False,
                                    latex_itemize: str = False) -> str:

        pub_list = ''
        list_peer_reviewed = ''
        if split_peer_review:
            list_nonpeerreviewed = ''
        newline = '\n'
        item = '\\item '
        for record in self.inspires_records.values():
            entry = ''
            if record.author_count < author_count_to_exclude:
                cited = (record.citation_count > 0)
                well_cited = (record.citation_count > def_well_cited)
                backslash_char = "\\textbf{"
                citation = f', [citations: { f"{backslash_char}" if well_cited else ""}{record.citation_count}{"}" if well_cited else ""}]'

                if latex_itemize:
                    entry += item
                if include_title:
                    entry += f'{record.ins_titles[0]["title"]}, '
                if arxiv:
                    entry += record.__repr__(cap_author_list=author_count_to_exclude)[:-1]
                if include_citation and cited:
                    entry += citation

                entry += f'.{newline}'

            if split_peer_review:
                if record.published:
                    list_peer_reviewed += entry
                else:
                    list_nonpeerreviewed += entry
            else:
                pub_list += entry

        if split_peer_review and latex_itemize:
            pub_list += '\\textbf{Peer-reviewed publications}\n\\begin{enumerate}\n' + list_peer_reviewed + '\\end{enumerate}\n \\textbf{Under review or non-peer review}\n \\begin{enumerate} \n' + list_nonpeerreviewed + '\\end{enumerate} '
        else:
            if latex_itemize:
                pub_list = '\\begin{enumerate}\n' + pub_list + '\\end{enumerate}'

        return pub_list.replace("  "," ")
