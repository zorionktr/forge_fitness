import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders the coach's markdown replies (headings, **bold**, lists, GFM tables). */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
