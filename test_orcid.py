# %%
from bs4 import BeautifulSoup
import json
import requests
import orcid
user_id = '0000-0002-8009-4515'
user_password = '2Heavy!?'
redirect_uri = 'https://orcid.org'
institution_key = 'APP-UHOPZU183KN6U7LM'
institution_secret = '149b79f7-e28b-4e9e-a86e-7e024cfd837e'
# %%

# api = orcid.PublicAPI(institution_key, institution_secret, sandbox=True)
# token = api.get_token(user_id, user_password, redirect_uri)
# summary = api.read_record_public('0000-0002-8009-4515', 'activities', token)
# # summary = api.read_record_public('0000-0001-1111-1111', 'record', token)
# print(summary)

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


# %%
data = []
TITLES, DOIs = [], []

for i, result in enumerate(results['profile']['activities']
                           ['works']['work']):
    title = str(result['work-title']['title']['value'].encode('utf-8'))
    doi = 'None'

    for x in result.get('-external-identifiers', []):
        for eid in result['work-external-identifiers']['work-external-identifier']:
            if eid['work-external-identifier-type'] == 'DOI':
                doi = str(eid['work-external-identifier-id']
                          ['value'].encode('utf-8'))

    # AIP journals tend to have a \n in the DOI, and the doi is the second line. we get
    # that here.
    if len(doi.split('\n')) == 2:
        doi = doi.split('\n')[1]

    pub_date = result.get('publication-date', None)
    if pub_date:
        year = pub_date.get('year', None).get('value').encode('utf-8')
    else:
        year = 'Unknown'

    # Try to minimize duplicate entries that are found
    dup = False
    if title.lower() in TITLES:
        dup = True
    if (doi != 'None'
            and doi.lower() in DOIs):
        dup = True

    if not dup:
        # truncate title to first 50 characters
        print('| {3} | {0}  | {1} | [[doi:{2}]]|'.format(
            title[0:50], year, doi, result['work-type']))

    TITLES.append(title.lower())
    DOIs.append(doi.lower())

# %%
# URL of the Google Scholar page
url = "https://scholar.google.de/citations?user=d-lXKR8AAAAJ&hl=en"

# Send a GET request to the URL
response = requests.get(url)

# Parse the HTML content of the page
soup = BeautifulSoup(response.content, 'html.parser')

# Find all the rows in the table containing the publications
publication_rows = soup.find_all('tr', class_='gsc_a_tr')

# Dictionary to store the details of the papers
papers_dict = {}

# Iterate over each row to extract the paper details
for row in publication_rows:
    # Extract the title of the paper
    title = row.find('a', class_='gsc_a_at').text

    # Extract other metadata like authors, publication venue, and year
    authors_venue = row.find('div', class_='gs_gray').text
    year = row.find('span', class_='gsc_a_h').text if row.find(
        'span', class_='gsc_a_h') else 'N/A'

    # Add the paper details to the dictionary
    papers_dict[title] = {
        'Authors/Venue': authors_venue,
        'Year': year
    }

# Display the papers dictionary
papers_dict

# %%
