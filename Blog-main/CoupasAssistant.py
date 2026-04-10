from urllib import parse
import streamlit as st
import requests
import hmac
from time import gmtime, strftime
import hashlib
import gdshortener
import json


def init_session_state():
    # 초기 API 키 설정값 초기화
    keys = [
        "CoupangAccessKey",
        "CoupangSecretKey",
        "NaverClientID",
        "NaverClientSecret",
    ]
    for key in keys:
        if key not in st.session_state:
            st.session_state[key] = ""


def _generateHmac(method, url):
    # if 'Hmac' in st.session_state:
    #     return st.session_state['Hmac']
    path, *query = url.split("?")
    datetimeGMT = (
        strftime("%y%m%d", gmtime()) + "T" + strftime("%H%M%S", gmtime()) + "Z"
    )
    message = datetimeGMT + method + path + (query[0] if query else "")
    signature = hmac.new(
        bytes(st.session_state["CoupangSecretKey"], "utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return (
        "CEA algorithm=HmacSHA256, access-key={}, signed-date={}, signature={}".format(
            st.session_state["CoupangAccessKey"], datetimeGMT, signature
        )
    )


def main():
    init_session_state()
    menu = ["Search", "Link Translate", "Setting",]
    choice = st.sidebar.selectbox("메뉴", menu)

    if choice == "Search":
        search_page()
    elif choice == "Link Translate":
        link_trans_page()
    elif choice == "Setting":
        setting_page()


def search_page():
    st.header("Search")

    with st.form(key="search_form"):
        keyword = st.text_input("검색어를 입력하세요")
        col1, col2 = st.columns(2)
        with col1:
            limit = st.number_input("검색 결과 수", min_value=1, max_value=10, value=5)
        with col2:
            image_size = st.selectbox("이미지 크기", ["1024x1024", "512x512", "256x256"])

        submit = st.form_submit_button("검색")

    if submit and keyword:
        url_keyword = parse.quote(keyword)
        try:
            REQUEST_METHOD = "GET"
            DOMAIN = "https://api-gateway.coupang.com"
            URL = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={url_keyword}&limit={limit}&imageSize={image_size}"

            try:
                authorization = _generateHmac(REQUEST_METHOD, URL)
                url = "{}{}".format(DOMAIN, URL)
                response = requests.request(
                    method=REQUEST_METHOD,
                    url=url,
                    headers={
                        "Authorization": authorization,
                        "Content-Type": "application/json",
                    },
                    # params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    r_code = data['rCode']
                    r_message = data['rMessage']
                    if r_code == "0":
                        s = gdshortener.ISGDShortener()

                        st.subheader("검색 결과")
                        short_url = s.shorten(url=data["data"]["landingUrl"])[0]
                        st.write(f"단축 URL: {short_url}")

                        for product in data["data"]["productData"]:
                            col1, col2, col3 = st.columns([1, 2, 1])

                            with col1:
                                st.image(product["productImage"], width=150)

                            with col2:
                                st.write(f"**{product['productName']}**")
                                st.write(f"{product['productPrice']:,}원")
                                short_url = s.shorten(url=product['productUrl'])[0]
                                st.write(f"{short_url}")
                                # st.write(f"URL: {product['productUrl']}")

                            with col3:
                                st.write(f"순위: {product['rank']}")
                                st.write(f"상품 ID: {product['productId']}")
                                st.write(
                                    f"로켓배송: {'예' if product['isRocket'] else '아니오'}"
                                )
                                st.write(
                                    f"무료배송: {'예' if product['isFreeShipping'] else '아니오'}"
                                )
                    else:
                        st.error(f"오류가 발생했습니다. {r_code} {r_message}")

                elif response.status_code == 429:
                    st.error("요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
                else:
                    st.error(f"API 호출 실패: {response.status_code} {response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"API 호출 중 오류가 발생했습니다: {str(e)}")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                raise

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")

    elif submit and not keyword:
        st.warning("검색어를 입력해주세요.")

def link_trans_page():
    st.header("Link Translate")

    with st.form(key="link_trans_form"):
        keyword = st.text_input("쿠팡 링크를 입력하세요")
        submit = st.form_submit_button("변환")

    if submit and keyword:
        try:
            REQUEST_METHOD = "POST"
            DOMAIN = "https://api-gateway.coupang.com"
            URL = f"/v2/providers/affiliate_open_api/apis/openapi/deeplink"

            try:
                authorization = _generateHmac(REQUEST_METHOD, URL)
                url = "{}{}".format(DOMAIN, URL)
                response = requests.request(
                    method=REQUEST_METHOD,
                    url=url,
                    headers={
                        "Authorization": authorization,
                        "Content-Type": "application/json",
                    },
                    data=json.dumps({
                        "coupangUrls": [
                            keyword
                        ]
                    })
                    # params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    r_code = data['rCode']
                    r_message = data['rMessage']
                    if r_code == '0':
                        s = gdshortener.ISGDShortener()
                        data = response.json()

                        st.subheader("변환 결과")
                        print(data["data"][0]["landingUrl"])
                        short_url = s.shorten(url=data["data"][0]["landingUrl"])[0]
                        st.write(f"{short_url}")
                    else:
                        st.error(f"오류가 발생했습니다. {r_code} {r_message}")

                elif response.status_code == 429:
                    st.error("요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
                else:
                    st.error(f"API 호출 실패: {response.status_code} {response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"API 호출 중 오류가 발생했습니다: {str(e)}")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            raise

    elif submit and not keyword:
        st.warning("검색어를 입력해주세요.")

              

def setting_page():
    st.header("API 설정")

    with st.form(key="api_settings_form"):
        for key in [
            "CoupangAccessKey",
            "CoupangSecretKey",
            "NaverClientID",
            "NaverClientSecret",
        ]:
            st.session_state[key] = st.text_input(
                f"{key}", value=st.session_state[key], type="password"
            )
        submit_button = st.form_submit_button("설정 적용")

    if submit_button:
        st.success("API 설정이 적용되었습니다.")

    if st.button("설정 초기화"):
        for key in [
            "CoupangAccessKey",
            "CoupangSecretKey",
            "NaverClientID",
            "NaverClientSecret",
        ]:
            st.session_state[key] = ""
        st.success("모든 API 설정이 초기화되었습니다!")
        st.experimental_rerun()


if __name__ == "__main__":
    main()
