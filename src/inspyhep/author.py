import warnings
import requests
import numpy as np
import json
import datetime

from inspyhep.inspire_tools import InspireRecord

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
        self.snapshot_date = datetime.datetime.now()

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
        self.inspire_records = self.get_records_dict(self.full_json_records)

        # total number of citations
        self.citations = self.get_total_number_of_citations(self.inspire_records, )
        self.citations_noself = self.get_total_number_of_citations(self.inspire_records, self_cite=False)


    def get_total_number_of_citations(self, 
                                        records: dict,
                                        self_cite: bool =True,
                                        only_citeable: bool =False,
                                        only_published: bool =False,
                                        before_date: datetime.date =datetime.date.today(),
                                        after_date: datetime.date =datetime.date.min,
                                        in_year: int =None,
                                        max_nauthors: int =None) -> int:
        """ get_total_number_of_citations

        Parameters
        ----------
        records : dict
            the dictionary with asll the InspireRecord instances
        self_cite : bool, optional
            if True, count self citations, otherwise do not. By default True
        only_citeable : bool, optional
            if True, count only records that are citeable according to Inspire standard (i.e., can reliably be tracked). By default False
        only_published : bool, optional
            if True, count records that are not published. By default True
        before_date:
            only count records before a ceratain date (e.g datetime.date(2020, 3, 20))
        after_date:
            only count records after a ceratain date (e.g datetime.date(2020, 3, 20))
        max_nauthors:
            only count records with an author count less than of max_nauthors

        Returns
        -------
        int
            total number of citations of the author
        """
        count = 0
        for record in records.values():
            skip = (only_citeable and not record.citeable)\
                    or (only_published and not record.published)\
                    or (max_nauthors is not None and record.author_count > max_nauthors)\
                    or record.date > before_date\
                    or record.date < after_date\
                    or (in_year is not None and record.date.year != in_year)

            if skip:
                continue
            else:
                if self_cite:
                    count += record.citation_count
                else:
                    count += record.ins_citation_count_without_self_citations
        return count

    def get_records_dict(self, json_records) -> dict:
        """get_record_json get a dictionary of all inspire records for this author

        Parameters
        ----------
        json_record : str
            str with json output of inspire query

        Returns
        -------
        dict
            a dictionary with keys containing instances of the InspireRecord class,
            accessible with inspire texkeys (e.g., dic['weinberd:2002abc'])
        """
        inspire_records = {}
        for record in json_records['hits']['hits']:
            r = InspireRecord(record['metadata'])
            inspire_records[f'{r.texkey}'] = r
        return inspire_records

    def get_full_records_from_query(self, query) -> str:
        """get_full_record_from_query get the full result of the author query to Inspire

        Parameters
        ----------
        query : str
            url string with the author query following Inspire API

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
            warnings.warn(f"Could not find Inspire entry for author identified = {self.identifier}.")
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
        for record in self.inspire_records.values():
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
            pub_list += '\\textbf{Peer-reviewed publications}\n\\begin{enumerate}\n'\
                        + list_peer_reviewed\
                        + '\\end{enumerate}\n\\textbf{Under review or non-peer reviewed publications}\n\\begin{enumerate} \n'\
                        + list_nonpeerreviewed\
                        + '\\end{enumerate}'
        else:
            if latex_itemize:
                pub_list = '\\begin{enumerate}\n' + pub_list + '\\end{enumerate}'

        return pub_list.replace("  "," ")
