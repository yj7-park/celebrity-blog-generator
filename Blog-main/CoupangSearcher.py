import os
import json
import logging
from typing import Tuple
from urllib import parse
import hmac
import hashlib
import requests
from time import gmtime, strftime

class CoupangSearcher:
    def __init__(self, item: str, root_dir: str):
        self.item = item
        self.root_dir = root_dir
        self._load_config()
        self._setup_directories()
        self._setup_logging()

    def _load_config(self):
        # Load configuration from a separate file
        with open('config.json', 'r') as f:
            config = json.load(f)
        self._access_key = config['access_key']
        self._secret_key = config['secret_key']
        self._domain = config['domain']

    def _setup_directories(self):
        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(f"{self.root_dir}/raw", exist_ok=True)

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger()

    def _generate_hmac(self, method: str, url: str) -> str:
        path, *query = url.split("?")
        datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
        message = datetime_gmt + method + path + (query[0] if query else "")

        signature = hmac.new(bytes(self._secret_key, "utf-8"),
                             message.encode("utf-8"),
                             hashlib.sha256).hexdigest()

        return f"CEA algorithm=HmacSHA256, access-key={self._access_key}, signed-date={datetime_gmt}, signature={signature}"

    def search_and_save(self, limit: str = '5', size: str = '1024x1024') -> Tuple[str, str, str]:
        pre_name_file_path = f'{self.root_dir}/011-pre-product_names.txt'
        image_file_path = f'{self.root_dir}/02-product_images.txt'
        url_file_path = f'{self.root_dir}/03-product_urls.txt'
        price_file_path = f'{self.root_dir}/011-product_price.txt'

        if all(os.path.isfile(f) for f in [pre_name_file_path, image_file_path, url_file_path, price_file_path]):
            self.logger.info('Files exist, skipping process.')
            return pre_name_file_path, image_file_path, url_file_path, price_file_path

        json_file_path = f'{self.root_dir}/raw/A-api_result.json'
        if os.path.isfile(json_file_path):
            with open(json_file_path, 'r', encoding='utf8') as f:
                jsonbody = json.load(f)
            self.logger.info('File exists, no call for CoupangAPI.')
        else:
            jsonbody = self._call_coupang_api(limit, size)
            self._save_json_response(jsonbody, json_file_path)

        self._process_and_save_results(jsonbody, pre_name_file_path, image_file_path, url_file_path, price_file_path)

        return pre_name_file_path, image_file_path, url_file_path, price_file_path

    def _call_coupang_api(self, limit: str, size: str) -> dict:
        url_keyword = parse.quote(self.item)
        url = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={url_keyword}&limit={limit}&imageSize={size}"
        authorization = self._generate_hmac("GET", url)
        full_url = f"{self._domain}{url}"
        
        try:
            response = requests.get(
                url=full_url,
                headers={
                    "Authorization": authorization,
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"API call failed: {e}")
            raise

    def _save_json_response(self, jsonbody: dict, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(jsonbody, f, indent=4, ensure_ascii=False)
        self.logger.info(file_path)

    def _process_and_save_results(self, jsonbody: dict, pre_name_file_path: str, image_file_path: str, url_file_path: str, price_file_path: str):
        product_data = jsonbody['data']['productData']
        names = [product['productName'] for product in product_data]
        images = [product['productImage'] for product in product_data]
        urls = [product['productUrl'] for product in product_data]
        prices = [product['productPrice'] for product in product_data]

        self._save_list_to_file(names, pre_name_file_path)
        self._save_list_to_file(images, image_file_path)
        self._save_list_to_file(urls, url_file_path)
        self._save_list_to_file(prices, price_file_path)

    def _save_list_to_file(self, items: list, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False).strip('"') + '\n')
        self.logger.info(file_path)

if __name__ == "__main__":
    keyword = '미니 세탁기'
    searcher = CoupangSearcher(keyword, "./output")
    searcher.search_and_save(limit='10', size='400x400')