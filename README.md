## InSPy-HEP

Inspire-HEP Statistics with Python


A simplified Python interface to your Inspire-HEP data.

This is an independent tool made public with the hope it will be helpful to others, but without any guarantee. See also project by [efranzin](https://github.com/efranzin/python) and [motloch](https://github.com/motloch/track_inspire-hep_citations).

For official products, see
[![InspireHEP](https://img.shields.io/badge/Inspire_HEP-.net-dodgerblue.svg)](https://inspirehep.net/) [![InspireGEP](https://img.shields.io/badge/Inspire_HEP-on_GitHub-lightyellow.svg)](https://github.com/inspirehep)


---
### Installation

At this time, you can clone the repository and pip install it locally. From the top folder of the repo,
```sh
python3 -m pip install -e .
```

### Usage

##### Main classes

`Author(identifier: str)`: Main class containing all the records, statistics, and functionality to understand a given author's Inspire-HEP statistics.

`InspireRecord(info: str | dict)`: Main class containing the information on a specific Inspire-HEP record. The argument `record` can be a str with the texkey of the record or a `json`-fomatted dictionary spat out by Inspire.

##### Examples 

For instance, to get "A Model of Leptons" and the author information for Weinberg, simply do
```py
from inspyhep import InspireRecord, Author

SM_paper = InspireRecord('Weinberg:1967tq')

SW = Author('Steven.Weinberg.1')
```
and all the inspire obtained directly from Inspire is accessible through `ins_{attribute}`, but a few additional properties are also implemented. For example
``` py
print(SM_paper) # __repr__ returns 'Weinberg, Phys.Rev.Lett. 19 (1967), 1967.'
SM_paper.ins_citation_count
SM_paper.authorlist_bibtex_style # = 'Weinberg, Steven'
SM_paper.get_bibtex() # = '@article{Weinberg:1967tq, [...]}
```

The Author class also has a few useful features. If you tired of copy and pasting your publications, you can do:
``` py
SW.nice_publication_list(latex_itemize=True, split_peer_review=True)
```
to get a latex-formatted string:
```latex
\textbf{Peer-reviewed publications}
\begin{enumerate}
\item On the Development of Effective Field Theory, Weinberg, Eur.Phys.J.H 46 (2021) 1 6, 2021, arXiv:2101.04241 [hep-th], [citations: 10].
\item Massless particles in higher dimensions, Weinberg, Phys.Rev.D 102 (2020) 9 095022, 2020, arXiv:2010.05823 [hep-th], [citations: 10].
\item Models of Lepton and Quark Masses, Weinberg, Phys.Rev.D 101 (2020) 3 035020, 2020, arXiv:2001.06582 [hep-th], [citations: 
[...]
\item Current algebra, Weinberg, proceedings, 1968.
\item ON THE DERIVATION OF INTRINSIC SYMMETRIES, Weinberg, preprint, 1963.
\item The non-field theory of non-elementary particles, Weinberg, proceedings, 1962.
\end{enumerate}
```

---
##### How information is retrieved

To obtain all the author information, we query Inspire as
```sh
https://inspirehep.net/api/literature?sort=mostrecent&size=MAX_PAPER&q=a%20AUTHOR_IDENTIFIER
```
where AUTHOR_IDENTIFIER is the identifier of the author (e.g., Steven.Weinberg.1).
To obtain all the information of a given Inspire record, we use:
```sh
https://inspirehep.net/api/literature?q=texkeys:TEXKEY
```
where TEXKEY is the record.texkey (e.g., 'Weinberg:1967tq').

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
