# %%
from bs4 import BeautifulSoup
import json
import requests
import orcid

# %%

resp = requests.get("http://pub.orcid.org/0000-0002-8009-4515/works",
                    headers={'Accept': 'application/orcid+json'})
results = resp.json()

# %%
g = results['group']
g
# %%
titles = []
dois = []
doi_urls = []

for i, gi in enumerate(g):
    # print(i, gi)
    ws = gi['work-summary']
    for wsi in ws:
        # print(wsi)
        title = str(wsi['title']['title']['value'])

        doi = None
        doi_url = None
        v = wsi['external-ids']['external-id']
        # print(v)
        for eid in v:
            if eid['external-id-type'] == 'doi':
                doi = str(eid['external-id-value'])
                doi_url = str(eid['external-id-url'])

        if doi is not None and (title not in titles) and ('arXiv' not in doi):
            titles.append(title)
            dois.append(doi)
            doi_urls.append(doi_urls)
# %%
for li in zip(dois, titles):
    print(li)
print(len(titles))
# %%
