import requests
from bs4 import BeautifulSoup

# URL of the webpage
url = "https://getcomics.org/other-comics/go-go-power-rangers-vol-1-tpb-2018/"

# Send a GET request to the URL
response = requests.get(url)

# Parse the HTML content of the webpage
soup = BeautifulSoup(response.text, "html.parser")

# Find all <li> tags
download_list_items = soup.find_all("li")

# Iterate through each <li> tag
for li in download_list_items:
    # Check if the <li> tag contains the desired text
    if "Saban’s Go Go Power Rangers" in li.get_text():
        # Extract the title
        title = li.get_text(strip=True).split(' :')[0]
        print(f"Title: {title}")
        # Extract download links from <a> tags within this <li> tag
        download_links = li.find_all("a", {"href": True})
        for link in download_links:
            link_text = link.get_text(strip=True)
            if "Main Server" in link_text:
                link_href = link['href']
                print(f"Main Server: {link_href}")

        # Print a newline for better readability between items
        print("\n")
