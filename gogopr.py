import requests
from bs4 import BeautifulSoup

# URL of the webpage
url = "https://getcomics.org/other-comics/go-go-power-rangers-vol-1-tpb-2018/"

# Send a GET request to the URL
response = requests.get(url)

# Parse the HTML content of the webpage
soup = BeautifulSoup(response.text, "html.parser")

# Find all <a> tags with href containing "https://getcomics.org/dlds"
download_links = soup.find_all("a", {"href": lambda x: x and "https://getcomics.org/dlds" in x})

# Extract and print the download links
for link in download_links:
    print(link['href'])
