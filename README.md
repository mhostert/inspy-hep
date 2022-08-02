## InSPy-HEP
---

##### Inspires-HEP Statistics with Python
A simplified Python interface to your Inspires-HEP data.

Inspired on packages by
* [efranzin](https://github.com/efranzin/python)
* [motloch](https://github.com/motloch/]track_inspire-hep_citations)

---

##### Main classes
`Author(identifier: str ='S.Weinberg.1')`: Main class containing all the records, statistics, and functionality to understand a given author's Inspires-HEP statistics.

`InspiresRecord(record: str)`: Main class containing the information on a specific Inspires-HEP record. The argument `record` is one of the records in a `json`-fomatted string spat out by Inspires when querying it with 
```
# Query Inspire-HEP for author's information
'https://inspirehep.net/api/literature?sort=mostrecent&size=MAX_PAPER&q=a%20AUTHOR_IDENTIFIER
```



--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
