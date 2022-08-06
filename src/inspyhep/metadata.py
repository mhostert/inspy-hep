import warnings
import datetime
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class author:
    #
    # simplified
    full_name_unicode_normalized: str = ''
    affiliations_identifiers: List = field(default_factory=lambda: [])
    inspire_roles: List = field(default_factory=lambda: [])
    last_name: str = ''
    signature_block: str = ''
    uuid: str = ''
    id: str = ''
    ids: List = field(default_factory=lambda: [])
    record: Dict = field(default_factory=lambda: {})
    recid: int = ''
    curated_relation: bool = False
    bai: str = ''
    raw_affiliations: List = field(default_factory=lambda: [])
    source: str = ''
    first_name: str = ''
    affiliations: List = field(default_factory=lambda: [])
    record: Dict = field(default_factory=lambda: {})
    full_name: str = ''
    #
    # complete
    advisors: List = field(default_factory=lambda: [])
    positions: List = field(default_factory=lambda: [])
    project_membership: List = field(default_factory=lambda: [])
    schema: str = ''
    arxiv_categories: List = field(default_factory=lambda: [])
    control_number: int = 0
    deleted: bool = False
    legacy_creation_date: str = ''
    legacy_version: str = ''
    name: Dict = field(default_factory=lambda: {})
    status: str = ''
    stub: bool = False
    urls: List = field(default_factory=lambda: [])
    awards: List = field(default_factory=lambda: [])
    email_addresses: List = field(default_factory=lambda: [])
    

    def __post_init__(self):

        self.last_update = datetime.date(1,1,1)

        # get affiliation
        if len(self.affiliations)>0:
            self.affiliation = self.affiliations[0]["value"]
        elif len(self.raw_affiliations)>0:
            self.affiliation = self.raw_affiliations[0]["value"]
        else:
            self.affiliation = "Unknown"

        # Get ids 
        for id in self.ids:
            if id['schema'] == 'INSPIRE BAI' and self.bai == '':
                self.bai = id['value']
            elif id['schema'] == 'INSPIRE ID':
                self.id = id['value'].replace('INSPIRE-','')
        if self.id == '':
            self.id = self.recid
        
        self.primary_email_address = self.email_addresses[0] if len(self.email_addresses)>0 else ''
            

@dataclass
class literature:
    full_name_unicode_normalized: str = ''
    affiliations_identifiers: List = field(default_factory=lambda: [])
    record: Dict = field(default_factory=lambda: {})

    def __post_init__(self):
        self.last_update = datetime.date(1,1,1)


@dataclass
class institution:
    full_name_unicode_normalized: str = ''
    affiliations_identifiers: List = field(default_factory=lambda: [])
    record: Dict = field(default_factory=lambda: {})

    def __post_init__(self):
        self.last_update = datetime.date(1,1,1)