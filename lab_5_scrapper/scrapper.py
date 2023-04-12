"""
Crawler implementation
"""
import datetime
import json
import re
import shutil
from pathlib import Path
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_raw, to_meta
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH, TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT,
                                  NUM_ARTICLES_UPPER_LIMIT)




class IncorrectSeedURLError(Exception):
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    pass


class IncorrectNumberOfArticlesError(Exception):
    pass


class IncorrectHeadersError(Exception):
    pass


class IncorrectEncodingError(Exception):
    pass


class IncorrectTimeoutError(Exception):
    pass


class IncorrectVerifyError(Exception):
    pass


class Config:
    """
    Unpacks and validates configurations
    """

    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        self.path_to_config = path_to_config
        self._validate_config_content()
        self._config_dto = self._extract_config_content()
        self._seed_urls = self._config_dto.seed_urls
        self._num_articles = self._config_dto.total_articles
        self._headers = self._config_dto.headers
        self._encoding = self._config_dto.encoding
        self._timeout = self._config_dto.timeout
        self._should_verify_certificate = self._config_dto.should_verify_certificate
        self._headless_mode = self._config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            configuration = json.load(file)
        return ConfigDTO(**configuration)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()

        if not isinstance(config_dto.seed_urls,list):
            raise IncorrectSeedURLError

        for i in config_dto.seed_urls:
            if not isinstance(i, str):
                raise IncorrectSeedURLError

        if not config_dto.seed_url or not re.match(r'^https?://w?w?w?.', config_dto.seed_url):
            raise IncorrectSeedURLError

        if not isinstance(config_dto.num_articles, int):
            raise IncorrectNumberOfArticlesError

        if config_dto.num_articles < 1 or config_dto.num_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        headers = config_dto.get('headers')
        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        encoding = config_dto.get('encoding')
        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        timeout = config_dto.get('timeout')
        if not isinstance(timeout, int) or timeout <= TIMEOUT_LOWER_LIMIT or timeout >= TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        should_verify_certificate = config_dto.get('should_verify_certificate')
        if not isinstance(should_verify_certificate, bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self._config_dto.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self._total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self._config_dto.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self._config_dto.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self._config_dto.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self._config_dto.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self._config_dto.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """

    response = requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
    response.encoding == 'utf-8'
    return response


class Crawler:
    """
    Crawler implementation
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Crawler class
        """
        self.urls = []
        self._config = config
        self._seed_urls = config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs['href']
        if (isinstance(url, str)) and (url.count('/') > 3) and (url.startswith('/news/')):
            return url

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url1 in self._seed_urls:
            response = make_request(url1, self._config)
            if response.status_code == 200:
                main_bs = BeautifulSoup(response.text, 'lxml')
                for url2 in main_bs.find_all('a'):
                    url3 = self._extract_url(url2)
                    self.urls.append(url3)
                    if len(self.urls) >= self._config.get_num_articles():
                        return

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._config.get_seed_urls()


class HTMLParser:
    """
    ArticleParser implementation
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initializes an instance of the HTMLParser class
        """
        self._full_url = full_url
        self._article_id = article_id
        self._config = config
        self.article = Article(self._full_url)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text = article_soup.find('p')
        paragraphs_text = [paragraph.text for paragraph in text]
        self.article.text = '\n'.join(paragraphs_text)


    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """


    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self._full_url, self._config)
        article_bs = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article_bs)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if isinstance(base_path, str):
        base_path = Path(base_path)

    if base_path.exists():
        shutil.rmtree(base_path)

    else:
        base_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(full_url=url, article_id=i, config=configuration)
        text = parser.parse()
        to_raw(text)
        to_meta(text)


if __name__ == "__main__":
    main()
