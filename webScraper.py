import requests
from bs4 import BeautifulSoup
import time

headers = {
    'User-Agent': 'DinoDaily/1.0 (Testing purposes)'
}

def get_dinosaur_list():
    url = 'https://en.wikipedia.org/wiki/List_of_dinosaur_genera'
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    heading = soup.find_all('h1')[0].text

    print(f"Found page '{heading}'")

    tables = soup.find_all("table", {"id": "toc"})

    see_also = soup.find('span', {'id': 'See_also'})
    if see_also:
        see_also_heading = see_also.parent
    else:
        see_also_heading = None

    for item in tables:
        for sibling in item.find_next_siblings():
            if see_also_heading and sibling == see_also_heading:
                break

            if sibling.name == 'table' and sibling.get("id") == 'toc':
                break

            if sibling.name == "ul":
                # Skip reference lists
                if sibling.get('class') and any('reflist' in c or 'refbegin' in c for c in sibling.get('class', [])):
                    continue

                for child in sibling.find_all(recursive=False):
                    if child.name == "li":
                        dino_link = child.find("a")
                        if dino_link:
                            href = dino_link.get('href')
                            text = dino_link.text.strip()
                            if not ('cite_ref' in href or 'cite_note' in href):
                                skip_terms = ['ISBN', 'portal', 'List', 'Archived', 'Wayback']
                                if any(term in text for term in skip_terms):\
                                    continue
                                print(f"Dinosaur: {dino_link.text}")
                                print(f"Link: {href}")
                                print()



get_dinosaur_list()