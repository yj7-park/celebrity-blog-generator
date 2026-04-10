from abc import ABC, abstractmethod
import os

class DescGenerator(ABC):
    item = ''
    items = []
    
    def __init__(self, item, root_dir, items):
        self.root_dir = root_dir
        self.item = item
        import os
        os.makedirs(root_dir, exist_ok=True)
        self.items = items

    def generate_desc(self, overwrite=False):
        file_path = f'{self.root_dir}/04-product_descriptions.txt'
        # check if file exists
        if not overwrite:
            if os.path.isfile(file_path):
                print('File exists, skipping process.')
                return file_path
        descs = []
        for item in self.items:
            print(item)
            info = self._generate_info(item)
            desc = self._generate_desc(item, info)
            descs.append(desc)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(descs))
        return file_path
    @abstractmethod
    def _generate_desc():
        pass
    
    def _generate_info(self, item):
        import requests

        url = "https://api.perplexity.ai/chat/completions"

        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "요청된 제품에 대해 인터넷 검색을 통해 특징과 장단점을 찾아줘. 가격이나 색상, AS 정보는 제외하도록 하고, 제품의 카테고리에 맞는 주요 판단 기준을 5가지 선정한 이후에 각 기준의 관점에서 해당 제품의 특징을 상세하게 작성하도록 해. 특히 수치나 특수한 기술 같은 내용들은 명확하게 작성하도록 해."
                },
                {
                    "role": "user",
                    "content": item
                }
            ]
        }
        headers = {
            "Authorization": "Bearer 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",
            "Content-Type": "application/json"
        }

        response = requests.request("POST", url, json=payload, headers=headers)
        # print(response.json()['choices'][0]['message']['content'])
        return response.json()['choices'][0]['message']['content']