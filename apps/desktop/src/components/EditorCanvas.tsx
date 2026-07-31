import Highlight from "@tiptap/extension-highlight";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import TaskItem from "@tiptap/extension-task-item";
import TaskList from "@tiptap/extension-task-list";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect, useRef } from "react";

import { htmlToMarkdown, markdownToHtml } from "../lib/document";

interface EditorCanvasProps {
  sessionId: string;
  markdown: string;
  originalMarkdown: string;
  zoom: number;
  showRuler: boolean;
  compareMode: boolean;
  onChange: (markdown: string) => void;
  onEditorReady: (editor: Editor | null) => void;
  onSelectionChange: (selectedText: string) => void;
}

const extensions = [
  StarterKit.configure({
    heading: { levels: [1, 2, 3, 4, 5, 6] },
    history: { depth: 150 },
  }),
  Underline,
  Highlight.configure({ multicolor: false }),
  Link.configure({
    openOnClick: false,
    autolink: true,
    linkOnPaste: true,
    HTMLAttributes: { rel: "noreferrer noopener", target: "_blank" },
  }),
  Subscript,
  Superscript,
  TextAlign.configure({ types: ["heading", "paragraph"] }),
  Table.configure({ resizable: true, lastColumnResizable: true }),
  TableRow,
  TableHeader,
  TableCell,
  TaskList,
  TaskItem.configure({ nested: true }),
  Placeholder.configure({
    placeholder: "Start writing, paste a legal draft, or import a Word document…",
    showOnlyCurrent: true,
  }),
];

export function EditorCanvas({
  sessionId,
  markdown,
  originalMarkdown,
  zoom,
  showRuler,
  compareMode,
  onChange,
  onEditorReady,
  onSelectionChange,
}: EditorCanvasProps) {
  const sessionRef = useRef(sessionId);
  const lastExternalMarkdown = useRef(markdown);
  const editor = useEditor({
    extensions,
    content: markdownToHtml(markdown),
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "autocite-prosemirror",
        spellcheck: "true",
        "aria-label": "Document editor",
      },
      handleDOMEvents: {
        drop: (_view, event) => {
          if (event.dataTransfer?.files.length) {
            event.preventDefault();
            return true;
          }
          return false;
        },
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      const next = htmlToMarkdown(currentEditor.getHTML());
      lastExternalMarkdown.current = next;
      onChange(next);
    },
    onSelectionUpdate: ({ editor: currentEditor }) => {
      const { from, to } = currentEditor.state.selection;
      onSelectionChange(currentEditor.state.doc.textBetween(from, to, " "));
    },
  });

  useEffect(() => {
    onEditorReady(editor);
    return () => onEditorReady(null);
  }, [editor, onEditorReady]);

  useEffect(() => {
    if (!editor) return;
    const changedSession = sessionRef.current !== sessionId;
    const externalChange = markdown !== lastExternalMarkdown.current;
    if (changedSession || externalChange) {
      sessionRef.current = sessionId;
      lastExternalMarkdown.current = markdown;
      editor.commands.setContent(markdownToHtml(markdown), false);
    }
  }, [editor, markdown, sessionId]);

  if (compareMode) {
    return (
      <div className="compare-workspace" aria-label="Original and current document comparison">
        <CompareColumn label="Original import" markdown={originalMarkdown} />
        <CompareColumn label="Current revision" markdown={markdown} />
      </div>
    );
  }

  return (
    <div className="document-stage" style={{ "--document-zoom": zoom / 100 } as React.CSSProperties}>
      {showRuler ? <HorizontalRuler /> : null}
      <div className="page-shadow-shell">
        <article className="document-page" aria-label="Editable document page">
          <EditorContent editor={editor} className="autocite-editor" />
        </article>
      </div>
    </div>
  );
}

function HorizontalRuler() {
  return (
    <div className="horizontal-ruler" aria-hidden="true">
      <span className="ruler-margin ruler-margin-left" />
      <span className="ruler-tab-marker">▾</span>
      {Array.from({ length: 8 }, (_, index) => (
        <span className="ruler-number" style={{ left: `${12.5 * index}%` }} key={index}>
          {index + 1}
        </span>
      ))}
      <span className="ruler-margin ruler-margin-right" />
    </div>
  );
}

function CompareColumn({ label, markdown }: { label: string; markdown: string }) {
  return (
    <section className="compare-column">
      <header>{label}</header>
      <article
        className="document-page compare-page"
        dangerouslySetInnerHTML={{ __html: markdownToHtml(markdown) }}
      />
    </section>
  );
}
