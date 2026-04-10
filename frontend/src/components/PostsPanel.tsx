import Card from "./Card";

interface Props {
  count: number;
  titles: string[];
}

export default function PostsPanel({ count, titles }: Props) {
  return (
    <Card title="수집된 게시글" badge={count}>
      <ul style={{ margin: 0, padding: "0 0 0 18px", listStyle: "disc" }}>
        {titles.map((t, i) => (
          <li key={i} style={{ fontSize: 13, color: "#374151", marginBottom: 4, lineHeight: 1.5 }}>
            {t}
          </li>
        ))}
      </ul>
    </Card>
  );
}
