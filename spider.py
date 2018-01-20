# -*- coding: utf-8 -*-
'''
    text file in web spider
'''

import sys
import logging
from http import HTTPStatus
import requests
from MagicGoogle import MagicGoogle
import pymongo

LOGGER = logging.getLogger('txt_spider')

PROXIES = [{
    'http': 'http://127.0.0.1:1080',
    'https': 'http://127.0.0.1:1080'
}]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1664.3 Safari/537.36"


class TxtSpider:
    '''spider class

    Attributes:
        page: the last page number for search by google
    '''

    def __init__(self, page, mongo_uri):
        '''init'''
        self.page = page
        self.mongo = pymongo.MongoClient(mongo_uri)
        self.mg = MagicGoogle(PROXIES)

    def search(self):
        '''search by goole with "pass filetype:txt site:github.com"

        Yields:
            item: search results such as: {"url": "https://github.com/xx"}
        '''
        for page in range(0, self.page):
            for item in self.mg.search(query='intitle:passwd -Exploits filetype:txt site:github.com', num=10, start=page*10, language='en'):
                LOGGER.debug(item)
                if "url" not in item:
                    continue
                yield item

    def run(self):
        '''run spider, data store to mongodb'''

        for item in self.search():
            url = self._convert_url(item["url"])
            LOGGER.info(url)
            try:
                resp = requests.get(
                    url, headers={"User-Agent": USER_AGENT}, proxies=PROXIES[0])
                if resp.status_code == HTTPStatus.OK:
                    self._save_text(str(resp.text))
                else:
                    LOGGER.error("get %s response fail with code %s",
                                 url, resp.status_code)
            except requests.RequestException as err:
                LOGGER.fatal("get %s except exception %s", url, err)

        LOGGER.debug("run finish !!")

    def _convert_url(self, url):
        url = str.replace(url, "github.com", "raw.githubusercontent.com", 1)
        url = str.replace(url, "/blob", "", 1)
        return url

    def _save_text(self, raw):
        for raw_line in raw.splitlines():
            line = self._trim_line(raw_line)
            if line is not None:
                try:
                    collection = self.mongo.get_database().get_collection("raw_pwd")
                    collection.update_one(
                        {"_id": line}, {"$setOnInsert": {"_id": line}}, upsert=True)
                except pymongo.errors.PyMongoError as err:
                    LOGGER.fatal("connect mongodb have exception %s", err)

    def _trim_line(self, line):
        line = str.split(line, "\t").pop()
        line = line.strip()
        line = str.split(line, " ").pop()
        line = str.split(line, ":").pop()
        line = line.strip()
        if len(line) > 2 and len(line) < 30:
            return line


if __name__ == "__main__":
    if len(sys.argv) < 2:
        LOGGER.fail("mongo url such as 'mongodb://username:password@localhost:27017/db_name' must be need")
        sys.exit(1)

    mongo_uri = sys.argv[1]
    TxtSpider(3, mongo_uri).run()
