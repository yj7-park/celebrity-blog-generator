import { useState } from "react";
import { searchCoupang, getAffiliateUrl, shortenUrl } from "../lib/api";
import type { CoupangProduct } from "../lib/types";

const inputStyle: React.CSSProperties = {
  padding: "10px 14px",
  border: "1px solid #d1d5db",
  borderRadius: 10,
  fontSize: 14,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 16,
  padding: "24px 28px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  marginBottom: 16,
};

export default function CoupangPage() {
  const [keyword, setKeyword] = useState("");
  const [limit, setLimit] = useState(10);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [products, setProducts] = useState<CoupangProduct[]>([]);

  // 상품별 상태
  const [affiliateLoading, setAffiliateLoading] = useState<Record<string, boolean>>({});
  const [shortenLoading, setShortenLoading] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [productMap, setProductMap] = useState<Record<string, CoupangProduct>>({});

  const handleSearch = async () => {
    if (!keyword.trim()) return;
    setSearching(true);
    setSearchError(null);
    setProducts([]);
    setProductMap({});
    try {
      const res = await searchCoupang(keyword.trim(), limit);
      setProducts(res.products);
    } catch (e) {
      setSearchError(String(e));
    } finally {
      setSearching(false);
    }
  };

  const handleGetAffiliate = async (product: CoupangProduct) => {
    setAffiliateLoading((prev) => ({ ...prev, [product.product_id]: true }));
    try {
      const res = await getAffiliateUrl(product.product_url);
      setProductMap((prev) => ({
        ...prev,
        [product.product_id]: { ...product, ...prev[product.product_id], affiliate_url: res.affiliate_url },
      }));
    } catch (e) {
      alert(`어필리에이트 링크 생성 실패: ${e}`);
    } finally {
      setAffiliateLoading((prev) => ({ ...prev, [product.product_id]: false }));
    }
  };

  const handleShorten = async (product: CoupangProduct) => {
    const url = productMap[product.product_id]?.affiliate_url ?? product.product_url;
    setShortenLoading((prev) => ({ ...prev, [product.product_id]: true }));
    try {
      const res = await shortenUrl(url);
      setProductMap((prev) => ({
        ...prev,
        [product.product_id]: { ...product, ...prev[product.product_id], short_url: res.short_url },
      }));
    } catch (e) {
      alert(`URL 단축 실패: ${e}`);
    } finally {
      setShortenLoading((prev) => ({ ...prev, [product.product_id]: false }));
    }
  };

  const handleCopyUrl = (product: CoupangProduct) => {
    const p = productMap[product.product_id];
    const url = p?.short_url ?? p?.affiliate_url ?? product.product_url;
    navigator.clipboard.writeText(url);
    setCopiedId(product.product_id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatPrice = (price: number) =>
    price ? `${price.toLocaleString()}원` : "가격 정보 없음";

  return (
    <div>
      {/* 검색 영역 */}
      <div style={cardStyle}>
        <h2 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700, color: "#1e1b4b" }}>
          쿠팡 상품 검색
        </h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            type="text"
            placeholder="검색어 입력 (예: 아이유 선글라스)"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            style={{ ...inputStyle, flex: 1 }}
          />
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{ ...inputStyle, width: 100 }}
          >
            {[5, 10, 20, 30].map((n) => (
              <option key={n} value={n}>{n}개</option>
            ))}
          </select>
          <button
            onClick={handleSearch}
            disabled={searching}
            style={{
              padding: "10px 24px",
              background: searching ? "#a5b4fc" : "linear-gradient(90deg, #6366f1, #8b5cf6)",
              color: "#fff",
              border: "none",
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              cursor: searching ? "not-allowed" : "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {searching ? "검색 중..." : "검색"}
          </button>
        </div>
        {searchError && (
          <div style={{ color: "#ef4444", fontSize: 13, marginTop: 10 }}>⚠️ {searchError}</div>
        )}
      </div>

      {/* 결과 */}
      {products.length > 0 && (
        <div>
          <div style={{ fontSize: 14, color: "#6b7280", marginBottom: 12 }}>
            총 <strong>{products.length}개</strong> 상품 검색됨
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 16,
            }}
          >
            {products.map((product) => {
              const extra = productMap[product.product_id];
              const affiliateUrl = extra?.affiliate_url;
              const shortUrl = extra?.short_url;
              const isAffLoading = affiliateLoading[product.product_id];
              const isShortenLoading = shortenLoading[product.product_id];
              const isCopied = copiedId === product.product_id;

              return (
                <div
                  key={product.product_id}
                  style={{
                    background: "#fff",
                    border: "1px solid #e5e7eb",
                    borderRadius: 14,
                    overflow: "hidden",
                    boxShadow: "0 2px 6px rgba(0,0,0,0.05)",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  {/* 이미지 */}
                  <div style={{ position: "relative", height: 200, background: "#f9fafb" }}>
                    {product.product_image ? (
                      <img
                        src={product.product_image}
                        alt={product.product_name}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          width: "100%",
                          height: "100%",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: 40,
                        }}
                      >
                        🛒
                      </div>
                    )}
                  </div>

                  {/* 정보 */}
                  <div style={{ padding: "14px 16px", flex: 1 }}>
                    <p
                      style={{
                        margin: "0 0 6px",
                        fontSize: 13,
                        fontWeight: 600,
                        color: "#111",
                        lineHeight: 1.4,
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {product.product_name}
                    </p>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#ef4444", marginBottom: 4 }}>
                      {formatPrice(product.product_price)}
                    </div>
                    {product.rating > 0 && (
                      <div style={{ fontSize: 12, color: "#6b7280" }}>
                        ★ {product.rating.toFixed(1)} ({product.review_count.toLocaleString()}개 리뷰)
                      </div>
                    )}

                    {/* 어필리에이트 링크 */}
                    {affiliateUrl && (
                      <div
                        style={{
                          marginTop: 8,
                          fontSize: 11,
                          color: "#6b7280",
                          background: "#f9fafb",
                          borderRadius: 6,
                          padding: "6px 8px",
                          wordBreak: "break-all",
                        }}
                      >
                        {shortUrl ? (
                          <span style={{ color: "#10b981", fontWeight: 600 }}>단축 URL: {shortUrl}</span>
                        ) : (
                          <span>어필리에이트: {affiliateUrl.substring(0, 50)}...</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* 버튼들 */}
                  <div style={{ padding: "0 16px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
                    <button
                      onClick={() => handleGetAffiliate(product)}
                      disabled={isAffLoading || !!affiliateUrl}
                      style={{
                        padding: "8px",
                        background: affiliateUrl ? "#d1fae5" : "#ede9fe",
                        color: affiliateUrl ? "#065f46" : "#7c3aed",
                        border: "none",
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: isAffLoading || affiliateUrl ? "not-allowed" : "pointer",
                      }}
                    >
                      {isAffLoading ? "생성 중..." : affiliateUrl ? "✅ 어필리에이트 링크 생성됨" : "어필리에이트 링크 생성"}
                    </button>

                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        onClick={() => handleShorten(product)}
                        disabled={isShortenLoading || !!shortUrl}
                        style={{
                          flex: 1,
                          padding: "8px",
                          background: shortUrl ? "#dbeafe" : "#f3f4f6",
                          color: shortUrl ? "#1d4ed8" : "#4b5563",
                          border: "none",
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: isShortenLoading || shortUrl ? "not-allowed" : "pointer",
                        }}
                      >
                        {isShortenLoading ? "단축 중..." : shortUrl ? "✅ 단축됨" : "URL 단축"}
                      </button>
                      <button
                        onClick={() => handleCopyUrl(product)}
                        style={{
                          flex: 1,
                          padding: "8px",
                          background: isCopied ? "#d1fae5" : "#f9fafb",
                          color: isCopied ? "#065f46" : "#374151",
                          border: "1px solid #e5e7eb",
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {isCopied ? "✅ 복사됨" : "링크 복사"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!searching && products.length === 0 && keyword && !searchError && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "#9ca3af",
            fontSize: 14,
          }}
        >
          검색 결과가 없습니다. 다른 키워드로 시도해보세요.
        </div>
      )}

      {!searching && products.length === 0 && !keyword && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "#9ca3af",
            fontSize: 14,
          }}
        >
          키워드를 입력하고 검색 버튼을 클릭하세요.
        </div>
      )}
    </div>
  );
}
