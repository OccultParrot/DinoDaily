import time

import requests
from bs4 import BeautifulSoup
import dotenv
from rich.progress import Progress, SpinnerColumn, TextColumn, TaskProgressColumn, TimeRemainingColumn, BarColumn
from rich import print as print

from database_utils import get_connection

dotenv.load_dotenv()

headers = {'User-Agent': 'DinoDaily/1.0 (Testing purposes)'}


def get_dinosaur_list():
    url = 'https://en.wikipedia.org/wiki/List_of_dinosaur_genera'
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    dinosaurs = []
    print("Scraping Wikipedia...")

    # --- PARSING LOGIC ---
    tables = soup.find_all("table", {"id": "toc"})
    see_also = soup.find('span', {'id': 'See_also'})
    see_also_heading = see_also.parent if see_also else None

    for item in tables:
        for sibling in item.find_next_siblings():
            if see_also_heading and sibling == see_also_heading:
                break
            if sibling.name == 'table' and sibling.get("id") == 'toc':
                break
            if sibling.name == "ul":
                if sibling.get('class') and any('reflist' in c for c in sibling.get('class', "")):
                    continue
                for child in sibling.find_all("li", recursive=False):
                    dino_link = child.find("a")
                    if dino_link:
                        href = dino_link.get('href')
                        text = dino_link.text.strip()
                        if not ('cite_ref' in href or 'cite_note' in href):
                            skip_terms = ['ISBN', 'portal', 'List', 'Archived', 'Wayback']
                            if not any(term in text for term in skip_terms):
                                full_href = "https://en.wikipedia.org" + href
                                dino_page = BeautifulSoup(requests.get(full_href, headers=headers).text, 'html.parser')
                                page_name = href.split('/')[-1]
                                dinosaurs.append((text, full_href, page_name))

    # --- DATABASE LOGIC ---
    if dinosaurs:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                print("Cleaning slate: Truncating dino_refs...")
                cursor.execute("TRUNCATE TABLE dino_refs RESTART IDENTITY;")

                with Progress(
                        SpinnerColumn(),
                        TextColumn("[bold blue]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task("[cyan]Saving to database...", total=len(dinosaurs))

                    insert_query = """
                    INSERT INTO dino_refs (name, href, page_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                    """

                    # Loop through the list to make the progress bar "tick"
                    batch_size = 5
                    start_time = time.time()
                    for i in range(0, len(dinosaurs), batch_size):
                        batch = dinosaurs[i: i + batch_size]
                        cursor.executemany(insert_query, batch)
                        progress.advance(task, advance=len(batch))  # This makes the bar move per dino

                connection.commit()
                print(f"Scrape complete! {len(dinosaurs)} dinosaurs saved.")

                end_time = time.time()

                # --- SUMMARY ---
                mins, secs = divmod(end_time - start_time, 60)

                print("[green]\n" + "=" * 30)
                print(f"Total dinosaurs scraped: {len(dinosaurs)}")
                print(f"Elapsed time: {int(mins):02}:{int(secs):02}")
                print("[green]=" * 30)


if __name__ == "__main__":
    get_dinosaur_list()
