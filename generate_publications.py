# %%
from bs4 import BeautifulSoup
import json
import requests
import orcid
import time
import os
import re
from datetime import datetime
import html
import csv

# %%

def get_publication_info_from_crossref(doi):
    """Fetch complete publication information from Crossref API using DOI"""
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
            
            # Extract abstract
            abstract = ""
            if 'abstract' in work:
                abstract = work['abstract']
            
            # Extract volume and page information
            volume = work.get('volume', '')
            page = work.get('page', '')
            
            # Extract container title (journal name)
            container_title = ""
            if 'container-title' in work and work['container-title']:
                container_title = work['container-title'][0]
            
            # Extract keywords/subjects
            keywords = []
            if 'subject' in work:
                keywords.extend(work['subject'])
            if 'link' in work:
                for link in work['link']:
                    if link.get('content-type') == 'application/pdf':
                        # Sometimes keywords are in link descriptions
                        if 'title' in link and link['title']:
                            keywords.append(link['title'])
            
            return {
                'authors': authors,
                'abstract': abstract,
                'volume': volume,
                'page': page,
                'container_title': container_title,
                'keywords': keywords
            }
        else:
            print(f"Crossref API error for DOI {doi}: {response.status_code}")
            return {'authors': [], 'abstract': '', 'volume': '', 'page': '', 'container_title': '', 'keywords': []}
    except Exception as e:
        print(f"Error fetching publication info for DOI {doi}: {e}")
        return {'authors': [], 'abstract': '', 'volume': '', 'page': '', 'container_title': '', 'keywords': []}

def get_abstract_from_semantic_scholar(doi):
    """Fetch abstract from Semantic Scholar API as fallback"""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}?fields=abstract"
    try:
        response = requests.get(url, headers={'User-Agent': 'ECLIPSE-Lab/1.0 (mailto:philipp.pelz@fau.de)'})
        if response.status_code == 200:
            data = response.json()
            return data.get('abstract', '')
        else:
            return ''
    except Exception as e:
        print(f"Semantic Scholar API error for DOI {doi}: {e}")
        return ''

def get_keywords_from_semantic_scholar(doi):
    """Fetch keywords from Semantic Scholar API"""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}?fields=topics"
    try:
        response = requests.get(url, headers={'User-Agent': 'ECLIPSE-Lab/1.0 (mailto:philipp.pelz@fau.de)'})
        if response.status_code == 200:
            data = response.json()
            topics = data.get('topics', [])
            keywords = []
            for topic in topics:
                if 'topic' in topic:
                    keywords.append(topic['topic'])
            return keywords
        else:
            return []
    except Exception as e:
        print(f"Semantic Scholar keywords API error for DOI {doi}: {e}")
        return []

def get_publication_info_with_fallback(doi):
    """Fetch publication info from Crossref, with Semantic Scholar as fallback for abstract and keywords"""
    crossref_info = get_publication_info_from_crossref(doi)
    
    # If no abstract from Crossref, try Semantic Scholar
    if not crossref_info['abstract']:
        print(f"  No abstract in Crossref, trying Semantic Scholar...")
        semantic_abstract = get_abstract_from_semantic_scholar(doi)
        if semantic_abstract:
            crossref_info['abstract'] = semantic_abstract
            print(f"  Found abstract in Semantic Scholar!")
        else:
            print(f"  No abstract found in Semantic Scholar either")
    
    # If no keywords from Crossref, try Semantic Scholar
    if not crossref_info['keywords']:
        print(f"  No keywords in Crossref, trying Semantic Scholar...")
        semantic_keywords = get_keywords_from_semantic_scholar(doi)
        if semantic_keywords:
            crossref_info['keywords'].extend(semantic_keywords)
            print(f"  Found {len(semantic_keywords)} keywords in Semantic Scholar!")
        else:
            print(f"  No keywords found in Semantic Scholar either")
    
    return crossref_info

def clean_filename(title):
    """Convert title to a clean filename"""
    # Remove special characters and replace spaces with underscores
    clean = re.sub(r'[^\w\s-]', '', title)
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean.lower()[:50]  # Limit length

def format_authors_for_bibtex(authors):
    """Format authors list for bibtex-style author field"""
    if not authors:
        return ""
    
    # Convert full names to initials + last name format
    formatted_authors = []
    for author in authors:
        parts = author.split()
        if len(parts) >= 2:
            # Take first letter of each part except the last
            initials = " ".join([part[0] + "." for part in parts[:-1]])
            last_name = parts[-1]
            formatted_authors.append(f"{initials} {last_name}")
        else:
            formatted_authors.append(author)
    
    return ", ".join(formatted_authors)

def jats_to_markdown(jats_text):
    """Convert JATS XML tags in abstract to Markdown/HTML-compatible formatting."""
    if not jats_text:
        return ''
    # Remove <jats:title> tags entirely (including "Abstract" titles)
    jats_text = re.sub(r'<jats:title>.*?</jats:title>', '', jats_text, flags=re.DOTALL)
    # Remove <jats:p> tags, keep their content
    jats_text = re.sub(r'<jats:p>(.*?)</jats:p>', r'\1\n\n', jats_text, flags=re.DOTALL)
    # Convert <jats:sub>...</jats:sub> to <sub>...</sub>
    jats_text = re.sub(r'<jats:sub>(.*?)</jats:sub>', r'<sub>\1</sub>', jats_text)
    # Remove any other JATS tags (e.g., <jats:sup>, <jats:bold>, etc.) but keep their content
    jats_text = re.sub(r'<jats:[^>]+>(.*?)</jats:[^>]+>', r'\1', jats_text)
    # Unescape HTML entities
    jats_text = html.unescape(jats_text)
    # Remove leading/trailing whitespace and extra newlines
    jats_text = re.sub(r'\n\s*\n\s*\n', '\n\n', jats_text)  # Remove excessive newlines
    # Remove excessive tabs and normalize whitespace
    jats_text = re.sub(r'\t+', ' ', jats_text)  # Replace tabs with single spaces
    jats_text = re.sub(r' +', ' ', jats_text)   # Replace multiple spaces with single space
    return jats_text.strip()

def load_publication_links(csv_file="publication_links.csv"):
    """Load publication links from CSV file"""
    links = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                doi = row['doi'].strip()
                links[doi] = {
                    'code_url': row['code_url'].strip() if row['code_url'].strip() else '',
                    'project_page_url': row['project_page_url'].strip() if row['project_page_url'].strip() else ''
                }
        print(f"Loaded {len(links)} publication links from {csv_file}")
    except FileNotFoundError:
        print(f"Warning: {csv_file} not found. No additional links will be added.")
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
    return links

def detect_categories(title, keywords, work_type):
    """Detect categories based on title, keywords, and work type"""
    categories = []
    
    # Combine title and keywords for analysis
    text_to_analyze = title.lower()
    if keywords:
        text_to_analyze += " " + " ".join(keywords).lower()
    
    # Category detection based on keywords and title
    category_keywords = {
        "ptychography": ["ptychography", "ptychographic", "ptychogram"],
        "electron microscopy": ["electron microscopy", "stem", "tem", "scanning transmission", "transmission electron", "4d-stem", "4d stem"],
        "X-ray microscopy": ["x-ray", "xray", "synchrotron", "x-ray microscopy"],
        "tomography": ["tomography", "tomographic", "3d reconstruction", "tilt series"],
        "software": ["software", "algorithm", "py4dstem", "prismatic", "code", "implementation", "package"],
        "cryo-EM": ["cryo", "cryogenic", "cryo-em", "cryo em"],
        "atomic resolution": ["atomic", "ångstrom", "angstrom", "sub-angstrom", "atomic resolution"],
        "nanoparticles": ["nanoparticle", "nanoparticles", "nano", "quantum dot"],
        "materials science": ["materials", "crystal", "crystalline", "lattice", "defect"],
        "imaging": ["imaging", "microscopy", "microscope", "image reconstruction"],
        "computational": ["computational", "simulation", "modeling", "numerical", "algorithm"],
        "machine learning": ["machine learning", "deep learning", "neural network", "ai", "artificial intelligence"],
        "physics": ["physics", "physical", "scattering", "diffraction", "interference"],
        "chemistry": ["chemistry", "chemical", "molecular", "organic", "inorganic"],
        "biology": ["biology", "biological", "biomolecule", "protein", "cell"]
    }
    
    # Check each category
    for category, keywords_list in category_keywords.items():
        for keyword in keywords_list:
            if keyword in text_to_analyze:
                if category not in categories:
                    categories.append(category)
                break
    
    # Add work type category
    if work_type == "journal-article":
        if "journal article" not in categories:
            categories.append("journal article")
    elif work_type == "conference-paper":
        if "conference paper" not in categories:
            categories.append("conference paper")
    elif work_type == "book-chapter":
        if "book chapter" not in categories:
            categories.append("book chapter")
    
    # Ensure we have at least one category
    if not categories:
        categories.append("research")
    
    return categories

def generate_qmd_content(title, authors, year, journal_title, doi, work_type, publication_date, crossref_info, publication_links):
    """Generate the content for a qmd file"""
    
    # Use Crossref journal title if available, otherwise use ORCID data
    final_journal_title = crossref_info.get('container_title', journal_title) or journal_title
    
    # Get keywords from Crossref
    keywords = crossref_info.get('keywords', [])
    
    # Detect categories using improved algorithm
    categories = detect_categories(title, keywords, work_type)
    
    # Format publication string with volume and page info
    publication = final_journal_title
    volume = crossref_info.get('volume', '')
    page = crossref_info.get('page', '')
    
    if volume and page:
        publication += f" {volume}, {page}"
    elif volume:
        publication += f" {volume}"
    
    # Format authors for bibtex
    bibtex_authors = format_authors_for_bibtex(authors)
    
    # Generate filename
    filename = clean_filename(title)
    
    # Get abstract
    abstract = crossref_info.get('abstract', '')
    if abstract:
        abstract = jats_to_markdown(abstract)
    else:
        abstract = "[Abstract will be added manually]"
    
    # Get additional links from CSV
    links = publication_links.get(doi, {})
    code_url = links.get('code_url', '')
    project_page_url = links.get('project_page_url', '')
    
    # Create qmd content
    categories_str = "\n  - ".join(categories)
    qmd_content = f"""---
title: "{title}"
type: "article"
author: "{bibtex_authors}"
year: "{year}"
publication: "{publication}"
preprint: ""
doi: "{doi}"
materials: ""
code_url: "{code_url}"
project_page_url: "{project_page_url}"
toc: false
categories:
  - {categories_str}
---

## Citation (APA 7)

> {title}
{bibtex_authors}
{publication}


## Abstract

{abstract}


"""
    
    return filename, qmd_content

def main(output_dir="publications/articles"):
    """Main function to fetch ORCID data and generate qmd files"""
    
    # Load publication links from CSV
    publication_links = load_publication_links()
    
    print("Fetching ORCID data...")
    resp = requests.get("http://pub.orcid.org/0000-0002-8009-4515/works",
                        headers={'Accept': 'application/orcid+json'})
    results = resp.json()
    
    g = results['group']
    
    # Initialize lists
    publications = []
    
    print("Processing publications...")
    for i, gi in enumerate(g):
        ws = gi['work-summary']
        for wsi in ws:
            # Extract title
            title = str(wsi['title']['title']['value'])
            
            # Extract DOI
            doi = None
            v = wsi['external-ids']['external-id']
            for eid in v:
                if eid['external-id-type'] == 'doi':
                    doi = str(eid['external-id-value'])
                    break
            
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
            
            # Filter out arXiv entries and duplicates
            if doi is not None and ('arXiv' not in doi):
                # Check if we already have this title
                if not any(pub['title'] == title for pub in publications):
                    print(f"\nProcessing: {title}")
                    
                    # Fetch complete publication info from Crossref with Semantic Scholar fallback
                    crossref_info = get_publication_info_with_fallback(doi)
                    
                    # Debug: Show keywords if found
                    keywords = crossref_info.get('keywords', [])
                    if keywords:
                        print(f"  Keywords found: {', '.join(keywords[:5])}")  # Show first 5 keywords
                    
                    publication_data = {
                        'title': title,
                        'authors': crossref_info['authors'],
                        'year': pub_year,
                        'journal_title': journal_title,
                        'doi': doi,
                        'work_type': work_type,
                        'publication_date': {
                            'year': pub_year,
                            'month': pub_month,
                            'day': pub_day
                        },
                        'crossref_info': crossref_info
                    }
                    
                    publications.append(publication_data)
                    
                    # Be nice to the API
                    time.sleep(0.2)
    
    print(f"\nFound {len(publications)} publications to process")
    
    # Sort publications from oldest to newest
    def pub_sort_key(pub):
        y = pub['year']
        m = pub['publication_date'].get('month')
        d = pub['publication_date'].get('day')
        # Use 0 for missing month/day so missing values sort as earliest
        return (
            int(y) if y and y.isdigit() else 0,
            int(m) if m and m.isdigit() else 0,
            int(d) if d and d.isdigit() else 0
        )
    publications.sort(key=pub_sort_key)
    
    # Generate qmd files
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nGenerating qmd files in {output_dir}...")
    for i, pub in enumerate(publications):
        filename, content = generate_qmd_content(
            pub['title'],
            pub['authors'],
            pub['year'],
            pub['journal_title'],
            pub['doi'],
            pub['work_type'],
            pub['publication_date'],
            pub['crossref_info'],
            publication_links
        )
        
        # Add index number to filename to ensure uniqueness
        qmd_filename = f"{i+1:02d}_{filename}.qmd"
        filepath = os.path.join(output_dir, qmd_filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Created: {qmd_filename}")
    
    print(f"\nSuccessfully generated {len(publications)} qmd files in {output_dir}")

if __name__ == "__main__":
    # For testing, use the test directory
    main("publications/articles")
    
    # Uncomment the line below to generate files in the actual publications folder
    # main("publications/articles") 