import { Fragment, type ReactNode } from "react";

type KnowledgeContentViewerProps = {
  content: string;
  markdownContent: string | null;
};

type MarkdownBlock =
  | { type: "blockquote"; lines: string[] }
  | { type: "code"; content: string }
  | { type: "heading"; depth: number; text: string }
  | { type: "hr" }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "paragraph"; text: string };

function parseInline(text: string): ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);

  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <Fragment key={index}>{part}</Fragment>;
  });
}

function parseMarkdown(markdown: string): MarkdownBlock[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      blocks.push({ type: "code", content: codeLines.join("\n") });
      index += 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(trimmed);
    if (heading) {
      blocks.push({
        type: "heading",
        depth: heading[1].length,
        text: heading[2],
      });
      index += 1;
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push({ type: "hr" });
      index += 1;
      continue;
    }

    if (/^>\s?/.test(trimmed)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index].trim())) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "blockquote", lines: quoteLines });
      continue;
    }

    const listMatch = /^((?:[-*+])|(?:\d+\.))\s+(.+)$/.exec(trimmed);
    if (listMatch) {
      const ordered = /\d+\./.test(listMatch[1]);
      const items: string[] = [];
      while (index < lines.length) {
        const item = /^((?:[-*+])|(?:\d+\.))\s+(.+)$/.exec(lines[index].trim());
        if (!item || /\d+\./.test(item[1]) !== ordered) {
          break;
        }
        items.push(item[2]);
        index += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (index < lines.length) {
      const current = lines[index].trim();
      if (
        !current ||
        current.startsWith("```") ||
        /^(#{1,6})\s+/.test(current) ||
        /^>\s?/.test(current) ||
        /^((?:[-*+])|(?:\d+\.))\s+/.test(current) ||
        /^(-{3,}|\*{3,}|_{3,})$/.test(current)
      ) {
        break;
      }
      paragraphLines.push(current);
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
  }

  return blocks;
}

function MarkdownPreview({ markdown }: { markdown: string }) {
  const blocks = parseMarkdown(markdown);

  if (!blocks.length) {
    return <p className="muted-copy">没有可预览的 Markdown 内容。</p>;
  }

  function renderHeading(depth: number, text: string, key: number) {
    const children = parseInline(text);

    if (depth === 1) {
      return <h1 key={key}>{children}</h1>;
    }
    if (depth === 2) {
      return <h2 key={key}>{children}</h2>;
    }
    if (depth === 3) {
      return <h3 key={key}>{children}</h3>;
    }
    if (depth === 4) {
      return <h4 key={key}>{children}</h4>;
    }
    if (depth === 5) {
      return <h5 key={key}>{children}</h5>;
    }
    return <h6 key={key}>{children}</h6>;
  }

  return (
    <>
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          return renderHeading(block.depth, block.text, index);
        }

        if (block.type === "paragraph") {
          return <p key={index}>{parseInline(block.text)}</p>;
        }

        if (block.type === "list") {
          const List = block.ordered ? "ol" : "ul";
          return (
            <List key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{parseInline(item)}</li>
              ))}
            </List>
          );
        }

        if (block.type === "blockquote") {
          return (
            <blockquote key={index}>
              {block.lines.map((quote, quoteIndex) => (
                <p key={quoteIndex}>{parseInline(quote)}</p>
              ))}
            </blockquote>
          );
        }

        if (block.type === "code") {
          return (
            <pre key={index}>
              <code>{block.content}</code>
            </pre>
          );
        }

        return <hr key={index} />;
      })}
    </>
  );
}

export function KnowledgeContentViewer({
  content,
  markdownContent,
}: KnowledgeContentViewerProps) {
  const previewMarkdown = markdownContent?.trim() ?? "";
  const hasMarkdown = Boolean(previewMarkdown);

  return (
    <div className="content-viewer" data-content-viewer>
      {hasMarkdown ? (
        <div className="content-viewer-actions">
          <button
            aria-pressed="false"
            className="secondary-button button-small"
            data-markdown-preview-toggle
            type="button"
          >
            预览 Markdown
          </button>
        </div>
      ) : null}

      {hasMarkdown ? (
        <div
          aria-label="Markdown 预览"
          className="markdown-rendered"
          data-markdown-preview-panel
          hidden
          role="region"
        >
          <div className="content-viewer-mode-label">Markdown 预览</div>
          <MarkdownPreview markdown={previewMarkdown} />
        </div>
      ) : null}
      <div className="raw-content" data-markdown-raw-panel>
        {content}
      </div>
    </div>
  );
}
