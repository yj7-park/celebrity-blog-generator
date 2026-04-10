# Option 1: use with transformers

from PIL import Image
import torch
from torchvision import transforms
import os


class ImageGenerator:
    item = ""
    urls = []
    images = []
    images_org = []
    birefnet = None

    # initializer
    def __init__(self, item, root_dir, urls):
        # if not no_process:
        #     self.birefnet = ObjectExtractor.init()
        self.item = item
        self.urls = urls
        # make directory
        import os
        self.root_dir = f"{root_dir}/images"
        self.raw_dir = f"{root_dir}/raw"
        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)

    def init_birefnet(self):
        from transformers import AutoModelForImageSegmentation

        birefnet = AutoModelForImageSegmentation.from_pretrained(
            "ZhengPeng7/BiRefNet", trust_remote_code=True
        )
        torch.set_float32_matmul_precision(["high", "highest"][0])
        birefnet.eval()
        return birefnet

    def download_images(self):
        self.images_org = []
        for index, url in enumerate(self.urls):
            print(f'donwload image {index+1}')
            image_path = f"{self.raw_dir}/{index + 1}-org_image.png"
            if os.path.exists(image_path):
                print('File exists, skipping process.')
                image = Image.open(image_path)
            else:
                import requests
                from io import BytesIO
                response = requests.get(url)
                image = Image.open(BytesIO(response.content))
                image.save(image_path)
            self.images_org.append(image)

    def combine_images(self):
        print('combining original images')
        len_to_combine = len(self.urls)
        image_path = f"{self.raw_dir}/0-combined_org_image.png"
        if os.path.exists(image_path):
            print('File exists, skipping process.')
            result = Image.open(image_path)
        else:
            # Combine all images
            size = self.images_org[0].size
            result = Image.new("RGBA", (size[0]*len_to_combine, size[1]))
            for i, image in enumerate(self.images_org):
                result.paste(image, (i * size[0], 0))
            result.save(image_path)
        return image_path

    def extract_objects(self, size):
        self.images = []
        for index, image in enumerate(self.images_org):
            print(f'extract image {index+1}')
            image_path = f"{self.root_dir}/{index + 1}-product_image.png"
            if os.path.exists(image_path):
                print('File exists, skipping process.')
                image_processed = Image.open(image_path)
            else:
                image_processed, mask = self._extract_object(image.resize(size))
                image_processed.save(image_path)
            self.images.append(image_processed)
            # plt.imshow(mask)
            # plt.savefig(f"{self.root_dir}/{self.item}_{index + 1}_mask.jpg")
            # plt.close()

    def combine_objects(self):
        print('combining extract objects')
        image_path = f"{self.root_dir}/0-combined_product_image.png"
        if os.path.exists(image_path):
            print('File exists, skipping process.')
            result = Image.open(image_path)
        else:
            # Combine all images
            size = self.images[0].size
            # TODO: changable
            len_to_thumbnail = len(self.urls)
            # result = Image.new("RGBA", (size[0]*2, size[1]*2))
            # x_set = [0, size[0], 0, size[0], size[0]/2]
            # y_set = [0, 0, size[1], size[1], size[1]/2]
            result = Image.new("RGBA", (size[0]*len_to_thumbnail, size[1]*1))
            # print((size[0]*5, size[1]*1))
            x_set = [size[0]*index for index in range(len_to_thumbnail)]
            y_set = [0] * len_to_thumbnail
            if len(self.images) == 0:
                self.images = [Image.open(f"{self.root_dir}/{self.item}_{index + 1}.png") for index in range(len_to_thumbnail)]
            for index_set in zip(x_set, y_set, self.images):
                x = int(index_set[0])
                y = int(index_set[1])
                image = index_set[2]
                # print(f'{x=}, {y=}')
                result.paste(image, (x, y))
            result.save(image_path)
        return image_path

    def _extract_object(self, image):
        if self.birefnet == None:
            self.birefnet = self.init_birefnet()
        # Data settings
        # image_size = (1024, 1024)
        image_size = (512, 512)
        transform_image = transforms.Compose(
            [
                transforms.Resize(image_size),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )

        # img.save("C:/Utilities/Blog/test1.jpg")
        # image = Image.open(imagepath)
        input_images = transform_image(image.convert('RGB')).unsqueeze(0)

        # Prediction
        with torch.no_grad():
            preds = self.birefnet(input_images)[-1].sigmoid().cpu()
        pred = preds[0].squeeze()
        pred_pil = transforms.ToPILImage()(pred)
        mask = pred_pil.resize(image.size)
        image.putalpha(mask)
        return image, mask
    def download_and_combine_images(self, size=(400, 400)):
        self.download_images()
        # TODO: fix
        self.combine_images()
        self.extract_objects(size)
        image_path = self.combine_objects()
        return image_path
    
    # def add_markers(self):
        

if __name__ == "__main__":
    item = "스팀청소기"
    urls = [
"https://ads-partners.coupang.com/image1/aeyYUiy5czFwP9tfaZ-jwpldQqeLUYnYqsqFRjLQ2QFqaiku3ZAqstmC1jOD7cmXm6DP_a6I4YV7Up9C9xyybYY0cpY175NWbxs2xVaO0h8u84W43MXTGMXOl3Bdx7gCzV13e9h8tqwUd95fp2p31955TJw9-Fu_6eDmeuJcV8wb8I42QqVeLCADda5jYH5jmX2VleYd370ckQZd4iXJSl7D1FBmQyBsGlSHqzXRptqr5WtGwO9WudTKPYo-lGG2OOz5ON14Iz2kRD5THdMWc8mV8KDoP3Na0H-NDyAxd1DNhClUicn6OBBOayYB9gMvDSh_Dqecfqf8CnnGojfMPQ==",
"https://ads-partners.coupang.com/image1/W6qJ9hPWi6XtREerWzRStAqaEuMcVeP9gNkWemjLkbl53rCO9kpr6f0aE2bjJUMqhD6vmJYEyCVSO_f20Rvxgd9LjA4audScmL2MovKosi8SWYbfVlXdkPi6TTlmblHqmY1_7Kug6PgDnrt_pOgGkxCW_8l-QvfeKwE3KrAoZDyqsG1WSdyl15f60d_CEdMHr5DCvf3THkvXQV84A78fV6x0_Q65KrG-xXQFiWpOTpYpB7IwXEblg1Bh7S3fcIBE5_icqvBBbYBJpBAWx9SeXN8o242iNUi3L2gsKk2537VkqmRTHm4_0WcZb763-zPxKvddzwV3Ccxr_9rgYg3yQNviktOTK1w=",
"https://ads-partners.coupang.com/image1/UVA-DZ-29nxCUS_4UekKVrqS9US-ke8spm9tq9ByBlOcjOQ4JJt7d1iBe8gKqP1eGCkfUtsZkHnDCXwA0rhf5lRsKuR4BRI1w-BM8r_ttRAwhof7qWenyV0EihTI0EHG7S0tsiHXEbJVaqeWqrig4x8AgTmVG5LnnZqG-ufrC2pgHrbdRSb3y7jL7xC0yM1qSuRyLQK0Ai6B3B6tHmZRCHV7RPv3Q9Us_WKyjaeDSaxPmoAv70QCP_N7bRs7LlE-CRFmRi9QfWA-5ov_0fPp9fI-EiikO1_lY9CmhNiP2tNahsXkPhGKl1sL_15cxHMBTfSa6NYcYLm7y7VqxnvET4czHz5fkomX",
"https://ads-partners.coupang.com/image1/svqero0mnEwBBu4kstlDs4d6RxxL8qrfeZQn-9KzHVv2wfqRIoBH-C9XKBdPO0XfjmwmBSr6JDHLGmKU4ZSwGqDlgsvNm3HPXE_L2y776qh8SEHA0IXmaiOxyGysybW-1MbXdU_apNRXKPi1fGy7yCAr1cijwWjVmLa9fWPrbmxn6PgwlOlYij8J2tDOc02tkhBv1SOiqZkSQY9rHVDRJhWxzAyVEHFRUd2WJgkS0suwuqYNnlGh176-lzi0Lhb_LTnreafAtjdlwc5V1i8J9peTjhsc4EIjSh1G5CGANmUl9gGj-x0a-Kj2VIuZiAi0J-cXIWDYo1EcHlsjfW2Wig==",
"https://ads-partners.coupang.com/image1/qTIOCGyweqYrLzneqXLUI0U-zox51hyIkBypJs2Fvghqf4N7xfEEhegqjvbXzBa7NaYEfEkjkxRnhccOj34wRB_5qyfomY4cUlb-NwDfoIlsAQTrl9mOO-gaJLOj25ZEsSZ8_5DJx_LxCl22FeGJUbT0q_7uHp9kkjPIDIvpDjC0CJ9vWTjwhxmssuAuI6df6HahSx5YENIQ8cmXzrBn8hNBY7HPjZhqRQ2zjGWi-yYhd_vbBFLXwJxtAvhm4bI3i7h9XDlzmuYEBryYqqWOY6zNG6oybdpnFD-VZ2_AuAiTNWkld3973A_ugcc8go8=",
    ]
    extractor = ImageGenerator(item, urls)
    extractor.download_images()
    extractor.combine_images()
    extractor.extract_objects()
    extractor.combine_objects()
