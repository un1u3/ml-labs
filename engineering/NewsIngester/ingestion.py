from bs4 import BeautifulSoup
import requests
import re 

class Article:
    def __init__(self, url: str, content: str):
        self.url = url
        self.content = content


class NewsIngester:
    def fetch_from_source(self, url : str):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraph = soup.find_all('p')
            text = " ".join(
                            p.get_text(strip=True)
                            for p in paragraph
                            if p.get_text(strip=True)
)
            return Article(url=url, content=text)
        except:
            raise ValueError(f"No data found at {url}")

    def clean_data(self, article: Article):
        text = article.content

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\x00-\x7F\u0900-\u097F]", "", text)
        text = text.strip()

        return Article(url=article.url, content=text)

    def fetch_extract(self, url:str):
        article = self.fetch_from_source(url)
        cleaned = self.clean_data(article)
        return cleaned




news = NewsIngester()

article = news.fetch_extract("https://www.ronbpost.com/2026/05/15240/")

print(article.content[:500])


