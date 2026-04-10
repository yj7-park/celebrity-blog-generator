from pydantic import BaseModel
from typing import List, Dict


class PostItem(BaseModel):
    title: str
    url: str
    date: str
    tag: str = ""


class CollectRequest(BaseModel):
    days: int = 2


class CollectResponse(BaseModel):
    posts: List[PostItem]
    count: int


class AnalyzeRequest(BaseModel):
    posts: List[PostItem]
    openai_api_key: str
    top_n: int = 3


class AnalyzeResponse(BaseModel):
    trending: List[str]
    post_count: int


class ItemsRequest(BaseModel):
    posts: List[PostItem]
    celeb: str


class ItemsResponse(BaseModel):
    celeb: str
    items: Dict[str, str]
    content_snippets: List[str]


class GenerateRequest(BaseModel):
    celeb: str
    items: Dict[str, str]
    content_snippets: List[str]
    openai_api_key: str


class GenerateResponse(BaseModel):
    celeb: str
    blog_post: str
