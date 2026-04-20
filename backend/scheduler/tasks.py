"""APScheduler task definitions."""
from __future__ import annotations
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def run_pipeline_job(job_id: str):
    """Execute the full pipeline for a scheduled job."""
    try:
        from routers.scheduler import _jobs
        from services.settings_service import load_settings
        from services.collector import collect_posts, scrape_multiple_posts
        from services.analyzer import get_trending_celebs
        from services.extractor import extract_items_from_posts
        from services.generator import generate_blog_post
        from openai import OpenAI

        meta = _jobs.get(job_id, {})
        settings = load_settings()

        if not settings.openai_api_key:
            logger.error(f"Job {job_id}: OpenAI API 키 없음")
            return

        client = OpenAI(api_key=settings.openai_api_key)
        days = meta.get("days", 2)
        max_posts = meta.get("max_posts", 10)
        top_celebs = meta.get("top_celebs", 3)
        auto_publish = meta.get("auto_publish", False)

        logger.info(f"Job {job_id} 시작: days={days}, max_posts={max_posts}")

        # 1. Collect
        posts = collect_posts(days)
        if not posts:
            logger.warning(f"Job {job_id}: 게시글 없음")
            return

        # 2. Analyze
        trending = get_trending_celebs(posts, client, top_celebs)
        if not trending:
            logger.warning(f"Job {job_id}: 연예인 없음")
            return

        celeb = trending[0]
        logger.info(f"Job {job_id}: 선정 연예인 = {celeb}")

        # 3. Scrape + Extract
        target_posts = [p for p in posts if celeb in p.title] or posts
        scraped = scrape_multiple_posts(target_posts, max_posts)
        all_items = extract_items_from_posts(scraped, client)
        celeb_items = [it for it in all_items if celeb in it.celeb or it.celeb in celeb]
        final_items = celeb_items if celeb_items else all_items

        # 4. Generate blog post
        blog_post = generate_blog_post(final_items, client)
        logger.info(f"Job {job_id}: 블로그 포스트 생성 완료 ({len(blog_post)} chars)")

        # 5. Auto-publish to Naver (if enabled)
        if auto_publish and settings.naver_id and settings.naver_pw:
            from services.naver_writer import NaverBlogWriter
            writer = NaverBlogWriter(settings.naver_id, settings.naver_pw, settings.chrome_user_data_dir)
            elements = [
                {"type": "text", "content": blog_post},
            ]
            # Add buy links
            for item in final_items[:5]:
                if item.link_url:
                    elements.append({"type": "url_text", "content": item.link_url})
            title = f"[오늘의아이템] {celeb} 착용 아이템 추천"
            blog_url = writer.write(title, elements)
            logger.info(f"Job {job_id}: 블로그 발행 완료 → {blog_url}")

        # Update last_run
        if job_id in _jobs:
            _jobs[job_id]["last_run"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Job {job_id} 오류: {e}", exc_info=True)
