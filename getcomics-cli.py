import requests
from bs4 import BeautifulSoup
import argparse
import re
import os
import subprocess

# Constants
SEARCH_URL_TEMPLATE = "https://getcomics.org/page/{}/?s={}"
YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
SPECIAL_CASES = {
    "spider man": "Spider-Man",
    "ms marvel": "Ms. Marvel",
    "spider gwen": "Spider-Gwen",
}

def normalize_keyword(keyword: str) -> str:
    """Normalize the keyword by applying special cases and converting to lowercase."""
    keyword = keyword.lower()
    for case in SPECIAL_CASES:
        if case in keyword:
            keyword = keyword.replace(case, SPECIAL_CASES[case])
    return keyword

def format_folder_name(name: str) -> str:
    """Format the folder name by capitalizing properly and handling special cases."""
    # Apply special cases first
    name = normalize_keyword(name)
    for case, replacement in SPECIAL_CASES.items():
        if case in name:
            name = name.replace(case, replacement)

    # Capitalize the first letter of each word
    name = ' '.join(word.capitalize() for word in name.split())
    return f"{name} Comics"

def search_getcomics(keyword: str, page_number: int = 1) -> dict:
    """Search GetComics for a keyword and return categorized links."""
    search_url = SEARCH_URL_TEMPLATE.format(page_number, keyword.replace(' ', '+'))
    print(f"Constructed URL: {search_url}")  # Debug print

    response = requests.get(search_url)
    print(f"HTTP Status Code: {response.status_code}")  # Debug print
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    print(f"Page Title: {soup.title.string}")  # Debug print

    links = soup.find_all('a', href=True)
    print(f"Number of Links Found: {len(links)}")  # Debug print

    categorized_links = {}
    for link in links:
        href = link['href']
        text = link.get_text().strip()

        # Check if the link contains the keyword in the text and is from the correct domain
        if 'getcomics.org' in href and keyword.lower() in text.lower():
            match = YEAR_PATTERN.search(href)
            if match:
                year = match.group(0)
                if year not in categorized_links:
                    categorized_links[year] = []
                # Get size information
                size = get_comic_size(href, keyword)
                categorized_links[year].append({'text': text, 'href': href, 'size': size})
            else:
                if 'Unknown' not in categorized_links:
                    categorized_links['Unknown'] = []
                size = get_comic_size(href, keyword)
                categorized_links['Unknown'].append({'text': text, 'href': href, 'size': size})

    return categorized_links

def get_comic_size(link: str, keyword: str) -> str:
    """Get the size of a comic book."""
    response = requests.get(link)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    size_element = soup.find('p', style="text-align: center;")
    if size_element:
        size_text = size_element.get_text()
        size_match = re.search(r'Size\s*:\s*([\d.]+\s*MB)', size_text)
        if size_match:
            return size_match.group(1)
    
    # If size information is not found in <p> element, look for <li> tags
    if 'vol' in keyword.lower():
        download_list_items = soup.find_all("li")
        for li in download_list_items:
            if keyword.lower() in li.get_text().lower():
                size_match = re.search(r'\(([\d.]+\s*MB)\)', li.get_text())
                if size_match:
                    return size_match.group(1)
    
    return 'Unknown'

def get_download_links(link: str, keyword: str) -> list:
    """Get download links from a comic page."""
    response = requests.get(link)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    download_links = []

    # Check all <li> elements for any download links
    download_list_items = soup.find_all("li")
    for li in download_list_items:
        if keyword.lower() in li.get_text().lower():
            links = li.find_all('a', href=True)
            for link in links:
                if 'Main Server' in link.get_text(strip=True):
                    download_links.append(link['href'])

    return download_links

def download_with_aria2c(url: str, output_dir: str = '.') -> None:
    """Download a file using aria2c."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    command = ['aria2c', '-d', output_dir, url]
    subprocess.run(command)

def main() -> None:
    """Main program entry point."""
    parser = argparse.ArgumentParser(description="Search GetComics for a keyword and return all matching links categorized by year.")
    parser.add_argument('keyword', type=str, help="The keyword to search for.")
    parser.add_argument('-p', '--page', type=int, default=1, help="The page number to search on.")
    args = parser.parse_args()

    keyword = normalize_keyword(args.keyword)
    page_number = args.page

    try:
        categorized_links = search_getcomics(keyword, page_number)
    except requests.RequestException as e:
        print(f"Error during search: {e}")
        return

    comics = []
    for year, links in categorized_links.items():
        for item in links:
            comics.append({'year': year, 'text': item['text'], 'href': item['href'], 'size': item['size']})

    if not comics:
        print("No comics found.")
        return

    for idx, comic in enumerate(comics, start=1):
        print(f"{idx}. [{comic['year']}] {comic['text']} - Size: {comic['size']}")

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
            download_links = get_download_links(selected_comic['href'], keyword)
            if download_links:
                formatted_links = [
                    f"{selected_comic['text']} Vol {idx+1}: {link}" for idx, link in enumerate(download_links)
                ]
                print("Download links found:")
                for idx, link in enumerate(formatted_links, start=1):
                    print(f"{idx}. {link}")

                vol_choice = input("\nEnter the number of the volume you want to download or 'all' to download all volumes: ").strip().lower()
                if vol_choice == 'all':
                    vol_indices = range(1, len(download_links) + 1)
                else:
                    vol_indices = [int(vol_choice)]

                comic_name = ' '.join(selected_comic['text'].split()[:2])  # Assume first two words are the series name
                output_dir = os.path.join("Comic Book", format_folder_name(comic_name))

                for vol_index in vol_indices:
                    download_with_aria2c(download_links[vol_index - 1], output_dir)
                print("Download completed.")
            else:
                print("Download links not found.")
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")

if __name__ == "__main__":
    main()
