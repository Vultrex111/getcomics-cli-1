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
    "spider man": "spider-man",
    "ms marvel": "ms. marvel"
}

def normalize_keyword(keyword: str) -> str:
    """Normalize the keyword by applying special cases and converting to lowercase."""
    keyword = keyword.lower()
    for case in SPECIAL_CASES:
        if case in keyword:
            keyword = keyword.replace(case, SPECIAL_CASES[case])
    return keyword

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
                categorized_links[year].append({'text': text, 'href': href})
            else:
                if 'Unknown' not in categorized_links:
                    categorized_links['Unknown'] = []
                categorized_links['Unknown'].append({'text': text, 'href': href})

    return categorized_links

def get_download_links(link: str) -> list:
    """Get download links from a comic page."""
    response = requests.get(link)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    download_links = []

    download_elements = soup.find_all('a', class_='aio-red', href=True)
    for element in download_elements:
        download_link = element['href']
        if 'readcomicsonline.ru' not in download_link:
            download_links.append(download_link)

    return download_links

def download_with_aria2c(url: str, output_dir: str = '.') -> None:
    """Download a file using aria2c."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    command = ['aria2c', '-d', output_dir, url]
    subprocess.run(command)

def create_comic_folder(name: str) -> str:
    """Create a comic folder with proper naming convention."""
    # Special cases handling
    for case, replacement in SPECIAL_CASES.items():
        name = name.lower().replace(case, replacement)
    
    # Capitalize the first letter of each word
    name = ' '.join(word.capitalize() for word in name.split())
    
    # Create the folder path
    folder_path = os.path.join("Comic Book", f"{name} Comics")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def main() -> None:
    """Main program entry point."""
    parser = argparse.ArgumentParser(description="Search GetComics for a keyword and return all matching links categorized by year.")
    parser.add_argument('keyword', type=str, help="The keyword to search for.")
    parser.add_argument('-p', '--page', type=int, default=1, help="The page number to search on.")
    args = parser.parse_args()

    keyword = normalize_keyword(args.keyword)
    page_number = args.page

    categorized_links = search_getcomics(keyword, page_number)

    comics = []
    for year, links in categorized_links.items():
        for item in links:
            comics.append({'year': year, 'text': item['text'], 'href': item['href']})

    if not comics:
        print("No comics found.")
        return

    for idx, comic in enumerate(comics, start=1):
        print(f"{idx}. [{comic['year']}] {comic['text']}")

    choice = input("\nEnter the number of the comic you want to download or 'exit' to quit: ").strip().lower()
    if choice == 'exit':
        print("Exiting without downloading.")
        return

    try:
        choice = int(choice)
        selected_comic = comics[choice - 1]
        print(f"\nYou selected: {selected_comic['text']} ({selected_comic['year']})")

        confirm_download = input("Confirm download (y/N): ").strip().lower()
        if confirm_download == 'y':
            download_links = get_download_links(selected_comic['href'])
            if download_links:
                print("Download link found:")
                print(download_links[0])
                input("\nPress Enter to start the download...")
                
                # Extract the comic name for folder creation
                comic_name = selected_comic['text'].split(' ')[0]
                output_dir = create_comic_folder(comic_name)
                
                download_with_aria2c(download_links[0], output_dir)
                print("Download completed.")
            else:
                print("No download links found for the selected comic.")
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")

if __name__ == "__main__":
    main()
