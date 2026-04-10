import os
import sys
import urllib.request
import json
import time
import hashlib
import hmac
import base64
# import pandas as pd
import requests

API_URL = "https://openapi.naver.com/v1/datalab/search"
BASE_URL = 'https://api.naver.com'
CUSTOMER_ID = 3367408
API_KEY = '0100000000edca9f5031b1b855d4f6a7853f9fe7d5af24c1d22fd26c15f6f3e464b2392895'
SECRET_KEY = 'AQAAAADtyp9QMbG4VdT2p4U/n+fVE82kx6Pen7FcjnE+g7BqdQ=='

class NaverAPI:
    client_id = '5_ogq53CKMoAmfxLWKKR'  # 네이버 API 클라이언트 ID
    client_secret = 'ST60G7PGht'  # 네이버 API 클라이언트 Secret

    @staticmethod
    def generate(timestamp, method, uri):
        message = "{}.{}.{}".format(timestamp, method, uri)
        hash = hmac.new(bytes(SECRET_KEY, "utf-8"), bytes(message, "utf-8"), hashlib.sha256)

        hash.hexdigest()
        return base64.b64encode(hash.digest())

    def get_header(self, method, uri):
        timestamp = str(round(time.time() * 1000))
        signature = self.generate(timestamp, method, uri)
        return {'Content-Type': 'application/json; charset=UTF-8', 'X-Timestamp': timestamp, 'X-API-KEY': API_KEY, 'X-Customer': str(CUSTOMER_ID), 'X-Signature': signature}
    
    def get_search_count(self, keyword):
        print(keyword)
        uri = '/keywordstool'
        method = 'GET'
        r = requests.get(BASE_URL + uri, params={'siteId':None, 'biztpId':None, 'hintKeywords': keyword, 'event':None, 'month':None, 'showDetail':'0'}, headers=self.get_header(method, uri))

        # print(json.dumps(r.json()['keywordList'], indent=4))
        if r.status_code != 200:
            print(r.json())
            return 0
        keyword_list = r.json()['keywordList']

        # convert bytes to string        
        keyword_list = [{'relKeyword': x['relKeyword'], 'monthlyCnt': (x['monthlyPcQcCnt'] + x['monthlyMobileQcCnt']) if (type(x['monthlyPcQcCnt']) == int and type(x['monthlyMobileQcCnt']) == int) else 0} for x in keyword_list]
        
        # remove if 'monthlyCnt' is lower than 10000
        keyword_list = [x for x in keyword_list if x['monthlyCnt'] >= 10000]
        
        # get blog contents count
        keyword_list = [{'relKeyword': x['relKeyword'], 'monthlyCnt': x['monthlyCnt'], 'blogCnt': self.get_blog_contents_count(x['relKeyword'])} for x in keyword_list]
        
        # get ratio of blogCnt / monthlyCnt
        keyword_list = [{'relKeyword': x['relKeyword'], 'monthlyCnt': x['monthlyCnt'], 'blogCnt': x['blogCnt'], 'ratio': x['blogCnt'] / x['monthlyCnt']} for x in keyword_list]
        
        # sort by ratio
        keyword_list = sorted(keyword_list, key=lambda x: x['ratio'], reverse=False)

        # print pretty
        print(json.dumps(keyword_list, indent=4, ensure_ascii=False))
        return json.dumps(keyword_list, indent=4, ensure_ascii=False)
        
        month_pc_count = r.json()['keywordList'][0]['monthlyPcQcCnt']
        month_mobile_count = r.json()['keywordList'][0]['monthlyMobileQcCnt']
        # df_keyword = pd.DataFrame([r.json()['keywordList'][0]]).set_index('relKeyword')

        # df_keyword.rename({'monthlyPcQcCnt':'월간 PC조회수','monthlyMobileQcCnt':'월간 모바일 조회수','monthlyAvePcClkCnt':'월간 평균 PC 클릭수', 'monthlyAveMobileClkCnt':'월간 평균 모바일 클릭수', 'monthlyAvePcCtr':'월간 평균 PC 클릭율', 'monthlyAveMobileCtr':'월간 평균 모바일 클릭율', 'plAvgDepth':'월간 평균 PC 광고수', 'compIdx':'PC 광고 기반 경쟁력'}, axis=1, inplace=True)
        # df_keyword.index.name = '키워드'

        # df_keyword = df_keyword[['월간 PC조회수', '월간 모바일 조회수', '월간 평균 PC 클릭수', '월간 평균 모바일 클릭수', '월간 평균 PC 클릭율', '월간 평균 모바일 클릭율', '월간 평균 PC 광고수', 'PC 광고 기반 경쟁력']]
        return month_pc_count + month_mobile_count

    def get_blog_contents_count(self, q):
        encText = urllib.parse.quote(q)
        url = "https://openapi.naver.com/v1/search/blog?query=" + encText # JSON 결과
        # url = "https://openapi.naver.com/v1/search/blog.xml?query=" + encText # XML 결과
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id",self.client_id)
        request.add_header("X-Naver-Client-Secret",self.client_secret)
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        if(rescode==200):
            response_body = response.read()
            response = response_body.decode('utf-8')
            # print(response)
            blog_contents_count = json.loads(response)["total"]
            return blog_contents_count
        else:
            print("Error Code:" + rescode)
        
    
    def query_and_download_images(self, q, n=3):
        urls = self.query_image(self, q)
        for index, url in enumerate(urls):
            print(f'donwload image {index+1}')
            image_path = f"C:/Utilities/Blog/product_images/{self.item}/{self.item}_{index + 1}.png"
        
    
    def query_image(self, q):
        encText = urllib.parse.quote(q)
        url = "https://openapi.naver.com/v1/search/image?query=" + encText # JSON 결과
        print(url)

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", self.client_id)
        request.add_header("X-Naver-Client-Secret", self.client_secret)
        request.add_header("Content-Type","application/json")
        response = urllib.request.urlopen(request)
        # response = urllib.request.urlopen(request, data=body.encode("utf-8"))
        rescode = response.getcode()
        if(rescode==200):
            response_body = response.read()
            body = json.loads(response_body)
            image_list = [body["items"][i]["link"] for i in range(len(body["items"]))]
            print('\n'.join(image_list))
            return image_list
        else:
            print("Error Code:" + rescode)
            return []
            
if __name__ == "__main__":
    naver = NaverAPI()
    q = "신생아밥통가습기"
    search_count = naver.get_search_count(q)
    print(search_count)
    blog_count = naver.get_blog_contents_count(q)
    print(blog_count)
    # image_list = naver.query_image(q)
    