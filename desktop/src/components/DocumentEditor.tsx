import { Extension, type Editor } from "@tiptap/core";
import Color from "@tiptap/extension-color";
import FontFamily from "@tiptap/extension-font-family";
import Highlight from "@tiptap/extension-highlight";
import { TableKit } from "@tiptap/extension-table";
import TextAlign from "@tiptap/extension-text-align";
import TextStyle from "@tiptap/extension-text-style";
import { Markdown } from "@tiptap/markdown";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

interface MarkdownCapableEditor extends Editor {
  getMarkdown(): string;
}

const FontSize = Extension.create({
  name: "fontSize",
  addGlobalAttributes() {
    return [
      {
        types: ["textStyle"],
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) => element.style.fontSize || null,
            renderHTML: (attributes) =>
              typeof attributes.fontSize === "string"
                ? { style: `font-size: ${attributes.fontSize}` }
                : {},
          },
        },
      },
    ];
  },
});

export interface DocumentEditorProps {
  value: string;
  onChange(value: string): void;
  onReady(editor: Editor | null): void;
  editable: boolean;
}

export function DocumentEditor({
  value,
  onChange,
  onReady,
  editable,
}: DocumentEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Markdown,
      TextStyle,
      Color,
      FontFamily,
      FontSize,
      Highlight.configure({ multicolor: true }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      TableKit.configure({ table: { resizable: true } }),
    ],
    content: value,
    contentType: "markdown",
    editable,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "document-prose",
        role: "textbox",
        "aria-label": "Document editor",
        spellcheck: "true",
        autocapitalize: "sentences",
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      onChange((currentEditor as MarkdownCapableEditor).getMarkdown());
    },
  });

  useEffect(() => {
    onReady(editor);
    return () => onReady(null);
  }, [editor, onReady]);

  useEffect(() => {
    if (editor === null) return;
    editor.setEditable(editable);
  }, [editable, editor]);

  useEffect(() => {
    if (editor === null) return;
    const current = (editor as MarkdownCapableEditor).getMarkdown();
    if (current !== value) {
      editor.commands.setContent(value, {
        contentType: "markdown",
        emitUpdate: false,
      });
    }
  }, [editor, value]);

  return <EditorContent editor={editor} className="document-editor" />;
}
