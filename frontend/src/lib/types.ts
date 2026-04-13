export interface CelebItem {
  celeb: string;
  category: string;
  product_name: string;
  image_urls: string[];
  candidate_image_urls?: string[];
  processed_image_path?: string;
  keywords: string[];
  link_url: string;
  source_title: string;
  source_url: string;
}

/** Row from the celeb_items DB table (flat, not nested). */
export interface CelebItemRecord {
  id: string;
  post_url: string;
  post_title: string;
  celeb: string;
  category: string;
  product_name: string;
  keywords: string[];
  image_url: string;
  coupang_url: string;
  created_at: string;
}

/** Row from the scraped_posts DB table. */
export interface ScrapedPostRecord {
  id: string;
  post_url: string;
  post_title: string;
  content_hash: string;
  scraped_at: string;
}

export interface CoupangProduct {
  product_id: string;
  product_name: string;
  product_image: string;
  product_url: string;
  product_price: number;
  rating: number;
  review_count: number;
  affiliate_url?: string;
  short_url?: string;
}

export interface PostItem {
  title: string;
  url: string;
  date: string;
  tag: string;
}

export interface ScheduleJob {
  id: string;
  name: string;
  cron: string;
  enabled: boolean;
  days: number;
  max_posts: number;
  top_celebs: number;
  auto_publish: boolean;
  last_run?: string;
  next_run?: string;
}

export interface AppSettings {
  openai_api_key: string;
  coupang_access_key: string;
  coupang_secret_key: string;
  coupang_domain: string;
  naver_id: string;
  naver_pw: string;
  pipeline_days: number;
  pipeline_max_posts: number;
  pipeline_top_celebs: number;
  chrome_user_data_dir: string;
  image_placement: string;  // "두괄식" | "미괄식"
}

export interface PipelineRun {
  id: string;
  celeb: string;
  created_at: string;
  title: string;
  item_count: number;
  days_ago?: number;
  items?: CelebItem[];
  blog_post?: string;
  elements?: NaverBlogElement[];
}

export interface CheckRunResponse {
  found: boolean;
  run: PipelineRun | null;
}

/** Element consumed by NaverBlogWriter.write() */
export interface NaverBlogElement {
  type: "text" | "header" | "image" | "url" | "url_text" | "video";
  content: string;
}

// SSE Pipeline Events — matches backend _sse() format:
// { type, step, percent, data, error }
export interface PipelineEvent {
  type: "progress" | "done" | "error";
  step: string;
  percent: number;
  error: string;
  data: {
    posts?: PostItem[];
    trending?: string[];
    selected?: string;
    items?: CelebItem[];
    celeb?: string;
    title?: string;
    blog_post?: string;
    elements?: NaverBlogElement[];
    posts_count?: number;
  } | null;
}
