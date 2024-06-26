import requests
from bs4 import BeautifulSoup
import argparse
import re
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Constants
SEARCH_URL_TEMPLATE = "https://getcomics.org/page/{}/?s={}"
YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
SPECIAL_CASES = {
    "spider man": "Spider-Man",
    "ms marvel": "Ms. Marvel",
    "spider gwen": "Spider-Gwen",
}

def normalize_keyword(keyword: str) -> str:
    keyword = keyword.lower()
    for case in SPECIAL_CASES:
        if case in keyword:
            keyword = keyword.replace(case, SPECIAL_CASES[case])
    return keyword

def format_folder_name(name: str) -> str:
    name = normalize_keyword(name)
    for case, replacement in SPECIAL_CASES.items():
        if case in name:
            name = name.replace(case, replacement)
    name = ' '.join(word.capitalize() for word in name.split())
    return f"{name} Comics"

def fetch_url(url: str) -> str:
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return ''

def search_getcomics(keyword: str, page_number: int = 1) -> dict:
    search_url = SEARCH_URL_TEMPLATE.format(page_number, keyword.replace(' ', '+'))
    html_content = fetch_url(search_url)
    if not html_content:
        return {}

    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find_all('a', href=True)

    categorized_links = {}
    for link in links:
        href = link['href']
        text = link.get_text().strip()

        if 'getcomics.org' in href and any(word in text.lower() for word in keyword.split()):
            match = YEAR_PATTERN.search(href)
            year = match.group(0) if match else 'Unknown'
            size = get_comic_size(href)
            categorized_links.setdefault(year, []).append({'text': text, 'href': href, 'size': size})

    return categorized_links

def get_comic_size(link: str) -> str:
    html_content = fetch_url(link)
    if not html_content:
        return 'Unknown'

    soup = BeautifulSoup(html_content, 'html.parser')
    size_element = soup.find('p', style="text-align: center;")
    if size_element:
        size_match = re.search(r'Size\s*:\s*([\d.]+\s*MB)', size_element.get_text())
        if size_match:
            return size_match.group(1)

    return 'Unknown'

def get_download_links(link: str, keyword: str, comic_name: str) -> list:
    html_content = fetch_url(link)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    download_links = []

    if 'vol' in keyword.lower():
        download_list_items = soup.find_all("li")
        vol_count = 1
        for li in download_list_items:
            if keyword.lower() in li.get_text().lower():
                links = li.find_all('a', href=True)
                for link in links:
                    if 'Main Server' in link.get_text(strip=True):
                        download_links.append({'link': link['href'], 'volume': vol_count})
                        vol_count += 1
    else:
        download_buttons = soup.find_all('a', href=True, title="DOWNLOAD NOW")
        vol_count = 1
        for button in download_buttons:
            if button['href'].startswith('https://getcomics.org/dlds'):
                download_links.append({'link': button['href'], 'volume': vol_count})
                vol_count += 1

    return download_links

def download_with_aria2c(url: str, output_dir: str = '.') -> None:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    command = ['aria2c', '-d', output_dir, url]
    subprocess.run(command)

def download_comics(download_links: list, output_dir: str) -> None:
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download_with_aria2c, link['link'], output_dir) for link in download_links]
        for future in as_completed(futures):
            future.result()

def search_and_download() -> None:
    parser = argparse.ArgumentParser(description="Search GetComics for a keyword and return all matching links categorized by year.")
    parser.add_argument('keyword', type=str, help="The keyword to search for.")
    parser.add_argument('-p', '--page', type=int, default=1, help="The page number to search on.")
    args = parser.parse_args()

    while True:
        keyword = normalize_keyword(args.keyword)
        page_number = args.page

        categorized_links = search_getcomics(keyword, page_number)

        comics = []
        for year, links in categorized_links.items():
            for item in links:
                comics.append({'year': year, 'text': item['text'], 'href': item['href'], 'size': item['size']})

        if not comics:
            print("No comics found.")
            return

        for idx, comic in enumerate(comics, start=1):
            print(f"{idx}. [{comic['year']}] {comic['text']} - Size: {comic['size']}")

        while True:
            choice = input("\nEnter the number of the comic you want to download or 'exit' to quit: ").strip().lower()
            if choice == 'exit':
                print("Exiting without downloading.")
                return

            try:
                choice = int(choice)
                selected_comic = comics[choice - 1]
                print(f"\nYou selected: {selected_comic['text']} ({selected_comic['year']}) - Size: {selected_comic['size']}")

                confirm_download = input("Confirm download (Y/n): ").strip().lower()
                if confirm_download in ['', 'y']:
                    comic_name = ' '.join(selected_comic['text'].split()[:2])
                    download_links = get_download_links(selected_comic['href'], keyword, comic_name)
                    if download_links:
                        output_dir = os.path.join("Comic Book", format_folder_name(comic_name))

                        if len(download_links) == 1:
                            vol_indices = [1]
                        else:
                            print("Download links found:")
                            for idx, link_info in enumerate(download_links, start=1):
                                print(f"{idx}. {comic_name} vol {link_info['volume']}: {link_info['link']}")

                            vol_choice = input("\nEnter the number of the volume you want to download or 'all' to download all volumes: ").strip().lower()
                            if vol_choice == 'all' or vol_choice == '':
                                vol_indices = range(1, len(download_links) + 1)
                            else:
                                vol_indices = [int(vol_choice)]

                        download_comics([download_links[i - 1] for i in vol_indices], output_dir)
                        print("Download completed.")
                    else:
                        print("No download links found.")

                break
            except (ValueError, IndexError):
                print("Invalid selection. Please enter a valid number.")

        another_search = input("\nDo you want to search for another comic book? (Y/n): ").strip().lower()
        if another_search not in ['', 'y']:
            print("Goodbye!")
            break

if __name__ == "__main__":
    search_and_download()
