# %%
from bs4 import BeautifulSoup
import json
import requests
import orcid
import time

# %%

def get_authors_from_crossref(doi):
    """Fetch author information from Crossref API using DOI"""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, headers={'User-Agent': 'ECLIPSE-Lab/1.0 (mailto:philipp.pelz@fau.de)'})
        if response.status_code == 200:
            data = response.json()
            work = data.get('message', {})
            
            # Extract authors
            authors = []
            if 'author' in work:
                for author in work['author']:
                    if 'given' in author and 'family' in author:
                        authors.append(f"{author['given']} {author['family']}")
                    elif 'family' in author:
                        authors.append(author['family'])
                    elif 'name' in author:
                        authors.append(author['name'])
            
            return authors
        else:
            print(f"Crossref API error for DOI {doi}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching authors for DOI {doi}: {e}")
        return []

# %%

resp = requests.get("http://pub.orcid.org/0000-0002-8009-4515/works",
                    headers={'Accept': 'application/orcid+json'})
results = resp.json()

# %%
g = results['group']
g
# %%
# Initialize lists for bibtex-relevant information
titles = []
dois = []
doi_urls = []
journal_titles = []
publication_years = []
publication_months = []
publication_days = []
work_types = []
put_codes = []
urls = []
authors_list = []  # New list for authors

for i, gi in enumerate(g):
    # print(i, gi)
    ws = gi['work-summary']
    for wsi in ws:
        # print(json.dumps(wsi, indent=2))
        
        # Extract title
        title = str(wsi['title']['title']['value'])
        
        # Extract DOI and DOI URL
        doi = None
        doi_url = None
        v = wsi['external-ids']['external-id']
        for eid in v:
            if eid['external-id-type'] == 'doi':
                doi = str(eid['external-id-value'])
                if eid.get('external-id-url'):
                    doi_url = str(eid['external-id-url']['value'])
        
        # Extract journal title
        journal_title = None
        if 'journal-title' in wsi and wsi['journal-title']:
            journal_title = str(wsi['journal-title']['value'])
        
        # Extract publication date
        pub_year = None
        pub_month = None
        pub_day = None
        if 'publication-date' in wsi:
            pub_date = wsi['publication-date']
            if 'year' in pub_date and pub_date['year']:
                pub_year = str(pub_date['year']['value'])
            if 'month' in pub_date and pub_date['month']:
                pub_month = str(pub_date['month']['value'])
            if 'day' in pub_date and pub_date['day']:
                pub_day = str(pub_date['day']['value'])
        
        # Extract work type
        work_type = None
        if 'type' in wsi:
            work_type = str(wsi['type'])
        
        # Extract put-code
        put_code = None
        if 'put-code' in wsi:
            put_code = str(wsi['put-code'])
        
        # Extract URL
        url = None
        if 'url' in wsi and wsi['url']:
            url = str(wsi['url']['value'])
        
        # Filter out arXiv entries and duplicates
        if doi is not None and (title not in titles) and ('arXiv' not in doi):
            titles.append(title)
            dois.append(doi)
            doi_urls.append(doi_url)
            journal_titles.append(journal_title)
            publication_years.append(pub_year)
            publication_months.append(pub_month)
            publication_days.append(pub_day)
            work_types.append(work_type)
            put_codes.append(put_code)
            urls.append(url)
            
            # Fetch authors from Crossref
            print(f"\nFetching authors for: {title}")
            authors = get_authors_from_crossref(doi)
            authors_list.append(authors)
            
            # Be nice to the API - add a small delay
            time.sleep(0.2)

# %%
# Display all extracted information
print("\n=== EXTRACTED BIBTEX INFORMATION ===")
print(f"Total publications: {len(titles)}")
print("\nPublications:")
for i in range(len(titles)):
    print(f"\n{i+1}. {titles[i]}")
    print(f"   DOI: {dois[i]}")
    print(f"   Authors: {', '.join(authors_list[i]) if authors_list[i] else 'Not available'}")
    print(f"   Journal: {journal_titles[i]}")
    print(f"   Year: {publication_years[i]}")
    print(f"   Month: {publication_months[i]}")
    print(f"   Day: {publication_days[i]}")
    print(f"   Type: {work_types[i]}")
    print(f"   Put-code: {put_codes[i]}")
    print(f"   URL: {urls[i]}")
    print(f"   DOI URL: {doi_urls[i]}")

# Print summary statistics
print(f"\n=== SUMMARY ===")
print(f"Total publications: {len(titles)}")
print(f"Publications with authors: {sum(1 for a in authors_list if a)}")
print(f"Publications with journal titles: {sum(1 for j in journal_titles if j is not None)}")
print(f"Publications with years: {sum(1 for y in publication_years if y is not None)}")
print(f"Publications with months: {sum(1 for m in publication_months if m is not None)}")
print(f"Publications with days: {sum(1 for d in publication_days if d is not None)}")
print(f"Publications with URLs: {sum(1 for u in urls if u is not None)}")
print(f"Publications with DOI URLs: {sum(1 for du in doi_urls if du is not None)}")
# %%
