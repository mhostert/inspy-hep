import warnings
import datetime
import os
import re
from bs4 import BeautifulSoup

from inspyhep import metadata
from inspyhep.literature_tools import InspireRecord, make_request, json_load_hits
import numpy as np


def strip_string(string):
    soup = BeautifulSoup(string)
    text_parts = soup.findAll(text=True)
    text = "".join(text_parts)

    return text.replace("^", "").replace("\\prime", "'").replace("{", "").replace("}", "").replace("'", "")


class Author:
    def __init__(self, identifier, max_papers=1000):
        """Author()

        Parameters
        ----------
        identifier : str
            the author's BAI string (e.g. 'Steven.Weinberg.1') or ORCID number (e.g., '0000-0002-9584-8877') or Inspires record ID (e.g., 00058003)
        max_papers : int, optional
            Number of papers requested from INSPIRE-HEP, by default 1000


        Modified from
            * https://github.com/efranzin/python
            * https://github.com/motloch/track_inspire-hep_citations

        """

        self.identifier = identifier
        self.max_papers = max_papers
        self.max_title_length = 100
        self.snapshot_date = datetime.datetime.now()

        # ORCID number (e.g., '0000-0002-9584-8877')
        if self.identifier.count("-") == 3 and len(self.identifier) == 19:
            self.orcid = self.identifier
            self.author_metadata_query = f"https://inspirehep.net/api/orcid/{self.orcid}"
            self.json_metadata = json_load_hits(make_request(self.author_metadata_query))["metadata"]

        # Inspire record ID (e.g., 1621061)
        elif self.identifier.isnumeric() or type(self.identifier) == int:
            self.recid = self.identifier
            self.author_metadata_query = f"https://inspirehep.net/api/authors/{self.recid}"
            self.json_metadata = json_load_hits(make_request(self.author_metadata_query))["metadata"]

        # Inspire BAI
        else:
            self.bai = self.identifier  # same thing
            self.author_metadata_query = f"https://inspirehep.net/api/authors?q=ids.value:{self.bai}"
            self.json_metadata = json_load_hits(make_request(self.author_metadata_query))[0]["metadata"]

        # We start by loading the overview of the author
        self.metadata = metadata.author(**self.json_metadata)
        self.bai = self.metadata.bai

        # Then we load all the author's literature records
        self.author_record_query = f"https://inspirehep.net/api/literature?sort=mostrecent&size={self.max_papers}&q=a%20{self.bai}"
        self.full_json_records = json_load_hits(make_request(self.author_record_query))
        # Fill in information about author's papers from the website response
        self.inspire_records = self.get_records_dict(self.full_json_records)
        # how many records found?
        self.num_hits = len(self.inspire_records)

        # And finally, we use the latest inspire_record to draw even more information on the author
        for author in self.full_json_records[0]["metadata"]["authors"]:
            if "recid" in author.keys() and author["recid"] == self.metadata.recid:
                self.json_metadata.update(author)
            elif "bai" in author.keys() and author["bai"] == self.metadata.bai:
                self.json_metadata.update(author)
        self.metadata = metadata.author(**self.json_metadata)

        # total number of citations
        self.citations = self.get_total_number_of_citations()
        self.citations_noself = self.get_total_number_of_citations(self_cite=False)

        self.coauthors = self.get_coauthors()
        self.coauthors_cap10 = self.get_coauthors(max_nauthors=10)

        self.coauthor_records_cap10 = self.get_coauthor_records(max_nauthors=10)

    def get_total_number_of_citations(self, self_cite: bool = True, **kwargs) -> int:
        """get_total_number_of_citations

        Parameters
        ----------
        self_cite : bool, optional
            if True, count self citations, otherwise do not. By default True

        Returns
        -------
        int
            total number of citations of the author
        """
        count = 0
        for record in self.inspire_records.values():
            if not self.valid_record(record, **kwargs):
                continue
            else:
                if self_cite:
                    count += record.citation_count
                else:
                    count += record.ins_citation_count_without_self_citations
        return count

    def get_records_dict(self, json_records=None, **kwargs) -> dict:
        """get_record_json get a dictionary of all inspire records for this author

        Parameters
        ----------
        json_record : str
            str with json output of inspire query

        Returns
        -------
        dict
            A dictionary containing instances of the InspireRecord class keys corresponding to the inspire texkeys
            (e.g., dic['weinberd:2002abc'])
        """
        if json_records is None:
            json_records = self.full_json_records

        inspire_records = {}
        for record in json_records:
            try:
                r = InspireRecord(record["metadata"])
            except ValueError:
                warnings.warn(f"Skipping record {record}. Could not parse it.")
                continue
            if self.valid_record(r, **kwargs):
                # if the record is valid, add it to the dictionary
                if r.texkey not in inspire_records.keys():
                    # if the texkey is not already in the dictionary, add it
                    inspire_records[f"{r.texkey}"] = r
                else:
                    # if the texkey is already in the dictionary, update it
                    inspire_records[f"{r.texkey}"].update(r)
            else:
                continue
        return inspire_records

    def get_number_of_records(self, json_records=None, **kwargs) -> int:
        """get_number_of_records get the number of inspire records for this author

        Parameters
        ----------
        json_record : str
            str with json output of inspire query

        Returns
        -------
        dict
            A dictionary containing instances of the InspireRecord class keys corresponding to the inspire texkeys
            (e.g., dic['weinberd:2002abc'])
        """
        count = 0
        for record in self.inspire_records.values():
            if not self.valid_record(record, **kwargs):
                continue
            else:
                count += 1
        return count

    def nice_publication_list(
        self,
        include_title: bool = True,
        author_count_to_exclude: int = 10,
        include_citation: bool = True,
        def_well_cited: int = 10,
        arxiv: bool = True,
        split_peer_review: bool = False,
        latex_itemize: str = False,
        newline: str = "\n",
        **kwargs,
    ) -> str:
        pub_list = ""
        list_peer_reviewed = ""
        if split_peer_review:
            list_nonpeerreviewed = ""
        item = "\\item "
        for record in self.inspire_records.values():
            entry = ""
            if record.author_count < author_count_to_exclude:
                cited = record.citation_count > 0
                well_cited = record.citation_count > def_well_cited
                backslash_char = "\\textbf{"
                citation = f', citations: { f"{backslash_char}" if well_cited else ""}{record.citation_count}{"}" if well_cited else ""}'

                if latex_itemize:
                    entry += item
                if include_title:
                    entry += f'{record.ins_titles[0]["title"]}, '
                if arxiv:
                    entry += record.__repr__(**kwargs)[:-1]
                if include_citation and cited:
                    entry += citation

                entry += f".{newline}"

            if split_peer_review:
                if record.published:
                    list_peer_reviewed += entry
                else:
                    list_nonpeerreviewed += entry
            else:
                pub_list += entry

        if split_peer_review and latex_itemize:
            pub_list += (
                "\\textbf{Peer-reviewed publications}\n\\begin{enumerate}\n"
                + list_peer_reviewed
                + "\\end{enumerate}\n\\textbf{Under review or non-peer reviewed publications}\n\\begin{enumerate} \n"
                + list_nonpeerreviewed
                + "\\end{enumerate}"
            )
        else:
            if latex_itemize:
                pub_list = "\\begin{enumerate}\n" + pub_list + "\\end{enumerate}"
        return re.sub("[<].*?[>]", "", pub_list).replace("  ", " ")

    def get_coauthors(self, **kwargs) -> str:
        """
        Given an author generates a list of all coauthors since a given year.
        Data is imported from the INSPIRE-HEP database.

        Known limitations.
        * Will only parse the most recent 1,000 publications

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <https://www.gnu.org/licenses/>.

        __author__  = 'David Radice'
        __version__ = '1.1'
        __license__ = 'GPL'
        __email__   = 'dur566@psu.edu'
        """

        # dictionary of metadata author dataclasses
        coauthors = {}
        for record in self.inspire_records.values():
            # determine if record is to be included given certain requirements
            if not self.valid_record(record, **kwargs):
                continue
            for author in record.authors.values():
                # Exclude yourself from coauthor lists
                if author.bai == self.bai:
                    continue
                # Check if this is a new author
                if author.bai not in coauthors.keys():
                    coauthors[author.bai] = author
                # Coauthor is known, but might be updated
                else:
                    # Update the last active year and keep longer version of name
                    if (record.date > author.last_update) or (author.full_name > coauthors[author.bai].full_name):
                        coauthors[author.bai] = author
        return coauthors

    def get_coauthor_records(self, **kwargs) -> str:
        """
        Generates a list of all records for each coauthor
        """

        # dictionary of metadata author dataclasses
        coauthors_joint_records = {}
        for record in self.inspire_records.values():
            # determine if record is to be included given certain requirements
            if not self.valid_record(record, **kwargs):
                continue
            for author in record.authors.values():
                # Exclude yourself from coauthor lists
                if author.bai == self.bai:
                    continue
                # Check if this is a new author
                if not author.bai in coauthors_joint_records.keys():
                    coauthors_joint_records[author.bai] = [record]
                # Coauthor is known, but new entry
                else:
                    coauthors_joint_records[author.bai].append(record)
        return coauthors_joint_records

    def get_coauthors_formatted(self, output_file: str = None, format: str = "nsf", **kwargs) -> str:
        coauthors = self.coauthors if hasattr(self, "coauthors") else self.get_coauthors(**kwargs)[0]
        if format.lower() == "nsf":
            coauthor_csv = '"Author","Affiliation","Last Active"\n'
        elif format.lower() == "doe":
            coauthor_csv = '"Last Name","First Name","Affiliation","Last Active"\n'

        for author in coauthors.values():
            coauthor_csv += f"{self.format_author(author, format=format)}\n"

        if output_file is not None:
            outfile = open(output_file, "w")
            outfile.write(coauthor_csv)
            outfile.close()

        return coauthor_csv

    def format_author(self, author, format="NSF") -> str:
        if format.lower() == "nsf":
            return f'"{author.full_name}","{author.affiliation}","{author.last_update.year}"'
        elif format.lower() == "doe":
            return f'"{author.last_name}","{author.first_name}","{author.affiliation}","{author.last_update.year}"'

    def valid_record(
        self,
        record,
        only_citeable: bool = False,
        only_published: bool = False,
        before_date: datetime.date = datetime.date.today(),
        after_date: datetime.date = datetime.date.min,
        min_citations: int = 0,
        in_year: int = None,
        max_nauthors: int = 10,
        from_keys: list = None,
        exclude_keys: list = None,
    ) -> bool:
        """skip_record check that record satisfies a list of useful conditions

        Parameters
        ----------
        only_citeable : bool, optional
            if True, count only records that are citeable according to Inspire standard (i.e., can reliably be tracked). By default False
        only_published : bool, optional
            if True, count records that are not published. By default True
        min_citations : int, optional
            only count records with a minimum number of citations, by default 0
        in_year : int, optional
            only count records from a given year, by default None
        from_keys : list, optional
            only count records from a given list of texkeys, by default None
        exclude_keys : list, optional
            only count records that are not in a given list of texkeys, by default None
        before_date:
            only count records before a ceratain date (e.g datetime.date(2020, 3, 20))
        after_date:
            only count records after a ceratain date (e.g datetime.date(2020, 3, 20))
        max_nauthors:
            only count records with an author count less than of max_nauthors


        Returns
        -------
        bool
            whether record is valid or not given conditions
        """
        invalid = (
            (only_citeable and not record.citeable)
            or (only_published and not record.published)
            or (max_nauthors is not None and record.author_count > max_nauthors)
            or (record.citation_count < min_citations)
            or (record.date > before_date)
            or (record.date < after_date)
            or (in_year is not None and record.date.year != in_year)
            or (from_keys is not None and record.texkey not in from_keys)
            or (exclude_keys is not None and record.texkey in exclude_keys)
        )

        return not invalid

    def get_publications_per_year(self, year_range: tuple = (2000, datetime.date.today().year), cumulative: bool = False, **kwargs) -> list:
        years = range(year_range[0], year_range[1] + 1)
        publications = []
        for y in years:
            publications.append(self.get_number_of_records(in_year=y, max_nauthors=10, **kwargs))
        if cumulative:
            publications = np.cumsum(publications)
        return publications

    def get_citations_per_year(
        self, year_range: tuple = (2000, datetime.date.today().year), cumulative: bool = False, self_cite: bool = True, **kwargs
    ) -> list:
        years = range(year_range[0], year_range[1] + 1)
        citations = []
        for y in years:
            citations.append(self.get_total_number_of_citations(in_year=y, self_cite=self_cite, max_nauthors=10))
        if cumulative:
            citations = np.cumsum(citations)
        return citations

    def get_markdown_descriptor(self, path=".", **kwargs) -> str:
        """get_markdown_descriptor this function generates a series of markdown files that can be used to generate a website

        Parameters
        ----------
        path : str, optional
            path where to put all markdown files, by default '.'

        Returns
        -------
        None

        """
        md = ""
        pub_number = 1
        # dictionary of metadata author dataclasses
        for record in self.inspire_records.values():
            # determine if record is to be included given certain requirements
            if not self.valid_record(record, **kwargs):
                continue

            # loop through the individual references in a given bibtex file
            # reset default date
            pub_year = record.date.year
            pub_month = record.date.month
            pub_day = record.date.day

            pub_date = f"{pub_year}-{pub_month}-{pub_day}"

            clean_title = strip_string(record.title)

            url_slug = re.sub("\\[.*\\]|[^a-zA-Z0-9_-]", "", clean_title).replace("--", "-")

            md_filename = f"{pub_date}-{url_slug}.md"
            html_filename = f"{pub_date}-{url_slug}"

            #########################################
            # citation authors
            author_citation = ""
            for author in record.authors.values():
                author_citation += strip_string(f" {author.first_name} {author.last_name}, ")

            ##########################################
            # Build Citation from text
            citation = strip_string(f"{record.__repr__(include_title=True, cap_author_list = 10, include_arxiv=False)[:-1]}")
            citation = strip_string(citation)

            citation_notitle = strip_string(f"{record.__repr__(include_title=False, cap_author_list = 10, include_arxiv=False)[:-1]}")
            citation_notitle = strip_string(citation_notitle)
            ##########################################
            ## YAML variables
            md = f"---\ntitle: '{clean_title}'\n"
            md += f"pub_number: {pub_number}\n"
            md += f"authors: {author_citation[:-2]}\n"
            md += "collection: publication"
            md += f"\npermalink: /publication/{html_filename}"
            md += f"\ndate: {pub_date}"
            md += f"\nvenue: {strip_string(record.pub_title)} "
            if record.arxiv_number is not None:
                md += f"\npaperurl: '{record.arxiv_url}'"
            md += f"\ncitation_notitle: '{citation_notitle}'"
            md += f"\ncitation: '{citation}'"
            if record.arxiv_number is not None:
                md += f"\neprint: '{record.arxiv_number}'\n"
            md += "\n---"
            md_filename = os.path.basename(md_filename)

            with open(f"{path}/{md_filename}", "w") as f:
                f.write(md)
            print(f"SUCESSFULLY PARSED {citation}")
            pub_number += 1
