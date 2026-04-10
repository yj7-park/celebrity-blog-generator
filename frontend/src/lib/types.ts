export interface CelebItem {
  celeb: string;
  category: string;
  product_name: string;
  image_urls: string[];
  keywords: string[];
  link_url: string;
  source_title: string;
  source_url: string;
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
}

// SSE Pipeline Events
export type PipelineEvent =
  | { type: "progress"; step: string; percent: number }
  | { type: "posts"; data: { count: number; titles: string[] } }
  | { type: "trending"; data: { celebs: string[] } }
  | { type: "items"; data: { items: CelebItem[] } }
  | { type: "blog_post"; data: { celeb: string; post: string } }
  | { type: "error"; message: string }
  | { type: "done" };
