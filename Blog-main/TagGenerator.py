from abc import ABC, abstractmethod
import os

class TagGenerator(ABC):
    item = ''
    items = []
    generated_texts = []
    
    def __init__(self, item, root_dir, items):
        self.root_dir = root_dir
        self.item = item
        import os
        os.makedirs(root_dir, exist_ok=True)
        self.items = items

    def generate_tag(self, overwrite=False):
        file_path = f'{self.root_dir}/06-product_tags.txt'
        # check if file exists
        if not overwrite:
            if os.path.isfile(file_path):
                print('File exists, skipping process.')
                return file_path
        tag = self._generate_tag()
        # print(tag)
        # '#.\w*' with regex
        import re
        tag = re.findall(r'#.\w*', tag)
        tag = ' '.join(tag[:30]) + ' '
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(tag)
        return file_path
    @abstractmethod
    def _generate_tag():
        pass