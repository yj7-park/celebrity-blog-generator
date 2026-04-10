import json
import streamlit as st
from BlogGenerator import BlogGenerator
from NaverAPI import NaverAPI
import os
import datetime
import re

# st.set_option('server.runOnSave', True)
bg = BlogGenerator()
naver = NaverAPI()

steps = [
    # (
    #     "Initialize",
    #     bg.initialize,
    #     [
    #         "root_dir",
    #     ],
    #     [
    #         "item",
    #     ],
    # ),
    (
        "Product List",
        bg.search_product_list,
        [
            "name_file_path",
            "image_file_path",
            "url_file_path",
            "price_file_path",
        ],
        [
            "item",
            "root_dir",
        ],
        [
            "name_file_path",
        ],
    ),
    (
        "Intro/Outro",
        bg.generate_intro_outro,
        [
            "intro_file_path",
            "outro_file_path",
        ],
        [
            "item",
            "root_dir",
        ],
        [
            "intro_file_path",
            "outro_file_path",
        ],
    ),
    (
        "Image Download (Reviews)",
        bg.download_product_images,
        [
            "score_file_path",
            "review_file_path",
        ],
        [
            "item",
            "root_dir",
            "url_file_path",
        ],
        [
            "review_file_path",
        ],
    ),
    (
        "Select Products",
        bg.select_product,
        [
            "select_file_path",
        ],
        [
            "item",
            "root_dir",
            "name_file_path",
            "price_file_path",
            "review_file_path",
        ],
        [
            "select_file_path",
        ],
    ),
    (
        "Thumbnail",
        bg.generate_thumbnail,
        [
            "thumbnail_path",
        ],
        [
            "item",
            "root_dir",
            "image_file_path",
            "select_file_path",
        ],
        [
            "thumbnail_path",
        ],
    ),
    (
        "Description",
        bg.generate_descriptions,
        [
            "desc_file_path",
        ],
        [
            "item",
            "root_dir",
            "name_file_path",
            "select_file_path",
        ],
        [
            "desc_file_path",
        ],
    ),
    (
        "Tags",
        bg.generate_tags,
        [
            "tag_file_path",
        ],
        [
            "item",
            "root_dir",
            "name_file_path",
        ],
        [
            "tag_file_path",
        ],
    ),
    # ( "Video", bg.),
    (
        "Write (URL)",
        bg.write,
        [
            "blog_url_file_path",
        ],
        [
            "item",
            "root_dir",
            "intro_file_path",
            "name_file_path",
            "url_file_path",
            "desc_file_path",
            "outro_file_path",
            "tag_file_path",
            "thumbnail_path",
            "select_file_path",
        ],
        [
            "blog_url_file_path",
        ],
    ),
]

# initialize
if "current_step" not in st.session_state:
    st.session_state["current_step"] = 0
if "item" not in st.session_state:
    st.session_state["item"] = ""
if "keyword" not in st.session_state:
    st.session_state["keyword"] = ""
for i in steps:
    if i[0] not in st.session_state:
        st.session_state[i[0]] = False
# print(json.dumps(st.session_state.to_dict(), sort_keys=True, indent=4))

# title
st.title("Coupas Blogger")

# sidebar
st.sidebar.title("Keyword Search")
keyword = st.sidebar.text_input("검색어")
if keyword != '':
    if keyword not in st.session_state:
        st.session_state[keyword] = naver.get_search_count(keyword)
    with st.sidebar.expander("검색 결과", expanded=False):
        st.sidebar.json(st.session_state[keyword])

st.sidebar.title("History")

# directory list with st_ctime

dirlist = os.listdir(os.path.join(os.path.dirname(__file__), "data"))
dirlist = zip(
    dirlist,
    [
        os.stat(os.path.join(os.path.dirname(__file__), "data", x)).st_mtime
        for x in dirlist
    ],
)
dirlist = sorted(dirlist, key=lambda x: x[1], reverse=True)

now = datetime.datetime.now()
date_str = now.strftime("%Y-%m-%d")

today_list = [x for x in dirlist if date_str in x[0]]
with st.sidebar.expander(f"Today ({len(today_list)})", expanded=False):
    for history in today_list:
        st.success(history[0])

# date_str이 포함되지 않은 파일들
past_list = [x for x in dirlist if date_str not in x[0]]
with st.sidebar.expander(f"Past ({len(past_list)})", expanded=False):
    for history in past_list:
        st.warning(history[0])
        # if st.sidebar.button(history):차량용방향제
        # st.session_state["item"] = history.split('] ')[1]

# Define the text input field
item = st.text_input(
    "아이템", value=st.session_state["item"] if st.session_state["item"] != "" else ""
)
if item and st.session_state["item"] != item:
    st.session_state["item"] = item
    st.session_state["root_dir"] = bg.initialize(item)
    for step in steps:
        st.session_state[step[0]] = False
        st.session_state["current_step"] = 0

# Sidebar
st.divider()

st.header(
    st.session_state["item"]
    if st.session_state["item"] != ""
    else "아이템을 입력하세요."
)

st.divider()


def process_step(step, i):
    yield f"[{i}] {step[0]}  "
    args = [st.session_state[arg] for arg in step[3]]
    results = step[1](*args)
    if len(step[2]) == 1:
        results = [results]
    if len(step[2]) > 0:
        for k, v in zip(step[2], results):
            print(f'- {k}:')
            print(v)
            st.session_state[k] = v
    st.session_state["current_step"] = i
    st.session_state[step[0]] = True
    yield "✅"

for step in steps:
    cancel_button_key = f'{step[0]}_cancel'
    if cancel_button_key in st.session_state and st.session_state[cancel_button_key]:
        for output in step[4]:
            try:
                os.remove(st.session_state[output])
            except:
                pass
    

if st.button("Generate Blog Post", key="generate_blog_post", use_container_width=True):
    if st.session_state["item"] != "":
        for i, step in enumerate(steps):
            i = i + 1
            col1, col2 = st.columns([7, 3])
            with col1:
                st.write_stream(process_step(step, i))
            with col2:
                st.button("🔁", key=f'{step[0]}_cancel' ,use_container_width=True)
            # st.write(outputs)
            # find text with ()
            outputs = step[4]
            output_title = re.findall(r"\((.*?)\)", step[0])
            if not output_title:
                output_title = step[0].split("/")
            for i in range(len(outputs)):
                file_path = st.session_state[outputs[i]]
                with st.expander(output_title[i], expanded=False):
                    if file_path.endswith(".txt"):
                        with open(file_path, "r", encoding="utf-8") as f:
                            contents = "\n".join(f.readlines())
                            if "\\n" in contents:
                                contents = contents.replace("\n", "\n\n----\n").replace(
                                    "\\n", "\n"
                                )
                            st.write(contents)
                    elif file_path.endswith(".png"):
                        st.image(file_path)

st.divider()

st.progress(st.session_state["current_step"] / len(steps), "진행률")

st.divider()

for i, step in enumerate(steps):
    i = i + 1
    if st.button(
        f"[{i}] {step[0]} {'(Done)' if st.session_state[step[0]] else ''}",
        key=i,
        use_container_width=True,
        disabled=st.session_state["item"] == ""
        and not st.session_state[steps[i - 1][0]],
    ):
        args = [st.session_state[arg] for arg in step[3]]
        results = step[1](*args)
        if len(step[2]) == 1:
            results = [results]
        if len(step[2]) > 0:
            for k, v in zip(step[2], results):
                print(k, v)
                st.session_state[k] = v
        st.session_state["current_step"] = i
        st.session_state[step[0]] = True
        st.rerun()
