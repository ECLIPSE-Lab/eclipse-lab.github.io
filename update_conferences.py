import os
import glob
import re
from datetime import datetime

def update_conferences():
    posts_dir = "posts"
    post_files = glob.glob(os.path.join(posts_dir, "**/index.qmd"), recursive=True)
    
    conferences = []
    
    for pf in post_files:
        with open(pf, "r") as f:
            content = f.read()
        
        # Extract YAML frontmatter
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            continue
        frontmatter = match.group(1)
        
        # Check if category is conference
        # We look for a line with "- conference"
        if not re.search(r"^\s*-\s*conference\s*$", frontmatter, re.MULTILINE):
            continue
            
        # Extract title
        title_match = re.search(r'^title:\s*"(.*?)"', frontmatter, re.MULTILINE)
        if not title_match:
            title_match = re.search(r"^title:\s*(.*?)$", frontmatter, re.MULTILINE)
        if not title_match:
            continue
        title = title_match.group(1).strip('"\'')
        
        # Extract date
        date_match = re.search(r'^date:\s*"(.*?)"', frontmatter, re.MULTILINE)
        if not date_match:
            date_match = re.search(r"^date:\s*(.*?)$", frontmatter, re.MULTILINE)
        if not date_match:
            continue
        date_str = date_match.group(1).strip('"\'')
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
            
        conferences.append({
            "title": title,
            "date": date_obj,
            "path": pf
        })
    
    # Sort by date
    conferences.sort(key=lambda x: x["date"], reverse=True)
    top_3 = conferences[:3]
    
    # Generate new markdown for the talks section
    talks_md = "### Talks & conferences\n"
    for conf in top_3:
        talks_md += f"- [{conf['title']}]({conf['path']})\n"
    
    # Replace in news.qmd
    news_path = "news.qmd"
    with open(news_path, "r") as f:
        news_content = f.read()
    
    # Use regex to find the ### Talks & conferences block and replace it
    # It stops at the next :::
    pattern = re.compile(r"### Talks & conferences\n.*?(?=\n:::)", re.DOTALL)
    
    if pattern.search(news_content):
        new_news_content = pattern.sub(talks_md.strip(), news_content)
        with open(news_path, "w") as f:
            f.write(new_news_content)
        print("Successfully updated news.qmd with the latest 3 conferences:")
        for c in top_3:
            print(f" - {c['title']} ({c['date'].strftime('%Y-%m-%d')})")
    else:
        print("Could not find the '### Talks & conferences' block in news.qmd")

if __name__ == "__main__":
    update_conferences()
