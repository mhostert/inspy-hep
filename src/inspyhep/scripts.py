#!/usr/bin/env python3

import warnings
import requests
import numpy as np
import argparse

from inspyhep import InspiresRecord
from inspyhep import Author

def inspyhep():
    # --------------
    # use argument_default=argparse.SUPPRESS so no defaults attributes are instantiated in the final Namespace
    parser = argparse.ArgumentParser(
        description="Summary of author", formatter_class=argparse.ArgumentDefaultsHelpFormatter, argument_default=argparse.SUPPRESS
    )    
    
    parser.add_argument("--identifier", type=str, help="Author identifier")
    kwargs = vars(parser.parse_args())
    author_identifier = kwargs['identifier']
    
    # create Author class
    author = Author(author_identifier)
    print("Author identifier:", author_identifier)
    # print("Latest work:", author.records)
    # print(f"Most cited work: {author.most_cited_record} citations = {author.most_cited_record.citations}")
    print(f"Total number of citations: {author.citations}")

if __name__ == "__main__":
    inspyhep()
