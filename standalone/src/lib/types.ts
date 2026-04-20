// ── 공통 타입 정의 ────────────────────────────────────────────────

export interface PostItem {
  title: string;
  url: string;
  date: string;
  tag: string;
}

export interface OrderedBlock {
  type: "text" | "image";
  content?: string; // type === "text"
  url?: string;     // type === "image"
}

export interface ScrapedPostData {
  orderedBlocks: OrderedBlock[];
  imageUrls: string[];
  paragraphs: string[];
  links: Array<{ text: string; href: string }>;
  postUrl: string;
  title: string;
}

/** 최종 구조화 결과: 연예인 × 아이템 매칭 */
export interface CelebItem {
  celeb: string;
  category: string;      // 가방 / 신발 / 의류 / 뷰티 / 식품 / 생활 / 액세서리 / 기타
  product_name: string;  // 브랜드 + 모델명
  image_urls: string[];  // pstatic.net 이미지
  keywords: string[];    // 방송명, 이슈 키워드
  link_url: string;      // 구매 링크 (단축 URL 포함)
  source_title: string;
  source_url: string;
}
