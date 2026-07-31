import type { Editor } from "@tiptap/react";
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  Baseline,
  Bold,
  BookOpenCheck,
  Braces,
  CheckCheck,
  Clipboard,
  Code2,
  Columns3,
  FileDiff,
  FileDown,
  FilePlus2,
  FileSearch,
  FileText,
  Highlighter,
  IndentDecrease,
  IndentIncrease,
  Italic,
  Link2,
  List,
  ListChecks,
  ListOrdered,
  Maximize2,
  Minus,
  PanelLeft,
  PanelRight,
  Pilcrow,
  Printer,
  Quote,
  RemoveFormatting,
  Rows3,
  Search,
  SpellCheck2,
  Strikethrough,
  Subscript,
  Superscript,
  Table2,
  Underline,
} from "lucide-react";
import { useMemo } from "react";

import { useWorkspace } from "../store/useWorkspace";
import type { ExportFormat, RibbonTab } from "../types";

interface RibbonProps {
  editor: Editor | null;
  onNew: () => void;
  onOpen: () => void;
  onExport: (format: ExportFormat) => void;
}

const tabs: { id: RibbonTab; label: string }[] = [
  { id: "file", label: "File" },
  { id: "home", label: "Home" },
  { id: "insert", label: "Insert" },
  { id: "layout", label: "Layout" },
  { id: "references", label: "References" },
  { id: "review", label: "Review" },
  { id: "view", label: "View" },
];

export function Ribbon({ editor, onNew, onOpen, onExport }: RibbonProps) {
  const tab = useWorkspace((state) => state.ribbonTab);
  const setTab = useWorkspace((state) => state.setRibbonTab);

  return (
    <section className="ribbon" aria-label="Document commands">
      <nav className="ribbon-tabs" aria-label="Ribbon tabs">
        {tabs.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? "is-active" : ""}
            onClick={() => setTab(item.id)}
            aria-selected={tab === item.id}
            role="tab"
          >
            {item.label}
          </button>
        ))}
      </nav>
      <div className="ribbon-content" role="tabpanel">
        {tab === "file" ? (
          <FileRibbon onNew={onNew} onOpen={onOpen} onExport={onExport} />
        ) : null}
        {tab === "home" ? <HomeRibbon editor={editor} /> : null}
        {tab === "insert" ? <InsertRibbon editor={editor} /> : null}
        {tab === "layout" ? <LayoutRibbon /> : null}
        {tab === "references" ? <ReferencesRibbon /> : null}
        {tab === "review" ? <ReviewRibbon /> : null}
        {tab === "view" ? <ViewRibbon /> : null}
      </div>
    </section>
  );
}

function FileRibbon({
  onNew,
  onOpen,
  onExport,
}: Pick<RibbonProps, "onNew" | "onOpen" | "onExport">) {
  const saveNow = useWorkspace((state) => state.saveNow);
  const active = useWorkspace((state) => state.activeSession);
  return (
    <>
      <RibbonGroup label="Document">
        <LargeButton icon={<FilePlus2 />} label="New" onClick={onNew} />
        <LargeButton icon={<FileSearch />} label="Open" onClick={onOpen} />
        <LargeButton
          icon={<FileText />}
          label="Save"
          disabled={!active}
          onClick={() => void saveNow()}
        />
      </RibbonGroup>
      <RibbonGroup label="Export">
        <LargeButton icon={<FileDown />} label="Word" disabled={!active} onClick={() => onExport("docx")} />
        <LargeButton icon={<FileDown />} label="PDF" disabled={!active} onClick={() => onExport("pdf")} />
        <SmallStack>
          <TextButton label="Markdown (.md)" onClick={() => onExport("md")} disabled={!active} />
          <TextButton label="Plain text (.txt)" onClick={() => onExport("txt")} disabled={!active} />
        </SmallStack>
      </RibbonGroup>
      <RibbonGroup label="Print">
        <LargeButton icon={<Printer />} label="Print" disabled={!active} onClick={() => window.print()} />
      </RibbonGroup>
      <RibbonGroup label="Privacy">
        <div className="ribbon-note">
          <strong>Local by default</strong>
          <span>Your document remains on this computer unless source review is explicitly enabled.</span>
        </div>
      </RibbonGroup>
    </>
  );
}

function HomeRibbon({ editor }: { editor: Editor | null }) {
  const setCommandPaletteOpen = useWorkspace((state) => state.setCommandPaletteOpen);
  const run = (command: () => boolean) => {
    command();
  };

  return (
    <>
      <RibbonGroup label="Clipboard">
        <LargeButton
          icon={<Clipboard />}
          label="Paste"
          onClick={() => void navigator.clipboard.readText().then((text) => editor?.chain().focus().insertContent(text).run())}
          disabled={!editor}
        />
        <SmallStack>
          <TextButton label="Cut" onClick={() => document.execCommand("cut")} disabled={!editor} />
          <TextButton label="Copy" onClick={() => document.execCommand("copy")} disabled={!editor} />
        </SmallStack>
      </RibbonGroup>

      <RibbonGroup label="Font">
        <div className="font-row">
          <select
            aria-label="Text style"
            value={activeTextStyle(editor)}
            onChange={(event) => applyTextStyle(editor, event.target.value)}
            disabled={!editor}
          >
            <option value="paragraph">Body text</option>
            <option value="title">Title</option>
            <option value="heading-1">Heading 1</option>
            <option value="heading-2">Heading 2</option>
            <option value="heading-3">Heading 3</option>
            <option value="quote">Quote</option>
          </select>
        </div>
        <div className="button-grid font-buttons">
          <FormatButton label="Bold" active={editor?.isActive("bold")} onClick={() => run(() => editor?.chain().focus().toggleBold().run() ?? false)}><Bold /></FormatButton>
          <FormatButton label="Italic" active={editor?.isActive("italic")} onClick={() => run(() => editor?.chain().focus().toggleItalic().run() ?? false)}><Italic /></FormatButton>
          <FormatButton label="Underline" active={editor?.isActive("underline")} onClick={() => run(() => editor?.chain().focus().toggleUnderline().run() ?? false)}><Underline /></FormatButton>
          <FormatButton label="Strikethrough" active={editor?.isActive("strike")} onClick={() => run(() => editor?.chain().focus().toggleStrike().run() ?? false)}><Strikethrough /></FormatButton>
          <FormatButton label="Highlight" active={editor?.isActive("highlight")} onClick={() => run(() => editor?.chain().focus().toggleHighlight().run() ?? false)}><Highlighter /></FormatButton>
          <FormatButton label="Subscript" active={editor?.isActive("subscript")} onClick={() => run(() => editor?.chain().focus().toggleSubscript().run() ?? false)}><Subscript /></FormatButton>
          <FormatButton label="Superscript" active={editor?.isActive("superscript")} onClick={() => run(() => editor?.chain().focus().toggleSuperscript().run() ?? false)}><Superscript /></FormatButton>
          <FormatButton label="Clear formatting" onClick={() => run(() => editor?.chain().focus().unsetAllMarks().clearNodes().run() ?? false)}><RemoveFormatting /></FormatButton>
        </div>
      </RibbonGroup>

      <RibbonGroup label="Paragraph">
        <div className="button-grid paragraph-buttons">
          <FormatButton label="Bullets" active={editor?.isActive("bulletList")} onClick={() => run(() => editor?.chain().focus().toggleBulletList().run() ?? false)}><List /></FormatButton>
          <FormatButton label="Numbering" active={editor?.isActive("orderedList")} onClick={() => run(() => editor?.chain().focus().toggleOrderedList().run() ?? false)}><ListOrdered /></FormatButton>
          <FormatButton label="Checklist" active={editor?.isActive("taskList")} onClick={() => run(() => editor?.chain().focus().toggleTaskList().run() ?? false)}><ListChecks /></FormatButton>
          <FormatButton label="Block quote" active={editor?.isActive("blockquote")} onClick={() => run(() => editor?.chain().focus().toggleBlockquote().run() ?? false)}><Quote /></FormatButton>
          <FormatButton label="Align left" active={editor?.isActive({ textAlign: "left" })} onClick={() => run(() => editor?.chain().focus().setTextAlign("left").run() ?? false)}><AlignLeft /></FormatButton>
          <FormatButton label="Center" active={editor?.isActive({ textAlign: "center" })} onClick={() => run(() => editor?.chain().focus().setTextAlign("center").run() ?? false)}><AlignCenter /></FormatButton>
          <FormatButton label="Align right" active={editor?.isActive({ textAlign: "right" })} onClick={() => run(() => editor?.chain().focus().setTextAlign("right").run() ?? false)}><AlignRight /></FormatButton>
          <FormatButton label="Justify" active={editor?.isActive({ textAlign: "justify" })} onClick={() => run(() => editor?.chain().focus().setTextAlign("justify").run() ?? false)}><AlignJustify /></FormatButton>
          <FormatButton label="Decrease indent" onClick={() => run(() => editor?.chain().focus().liftListItem("listItem").run() ?? false)}><IndentDecrease /></FormatButton>
          <FormatButton label="Increase indent" onClick={() => run(() => editor?.chain().focus().sinkListItem("listItem").run() ?? false)}><IndentIncrease /></FormatButton>
          <FormatButton label="Show formatting marks" disabled><Pilcrow /></FormatButton>
        </div>
      </RibbonGroup>

      <RibbonGroup label="Styles">
        <div className="style-gallery">
          <button onClick={() => editor?.chain().focus().setParagraph().run()} className={editor?.isActive("paragraph") ? "is-active" : ""}><span>AaBbCc</span>Normal</button>
          <button onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()} className={editor?.isActive("heading", { level: 1 }) ? "is-active" : ""}><span>AaBbCc</span>Heading 1</button>
          <button onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} className={editor?.isActive("heading", { level: 2 }) ? "is-active" : ""}><span>AaBbCc</span>Heading 2</button>
          <button onClick={() => editor?.chain().focus().toggleBlockquote().run()} className={editor?.isActive("blockquote") ? "is-active" : ""}><span>AaBbCc</span>Quote</button>
        </div>
      </RibbonGroup>

      <RibbonGroup label="Editing">
        <SmallStack>
          <TextButton icon={<Search />} label="Find" onClick={() => setCommandPaletteOpen(true)} />
          <TextButton label="Select all" onClick={() => editor?.chain().focus().selectAll().run()} disabled={!editor} />
          <TextButton label="Word count" onClick={() => setCommandPaletteOpen(true)} />
        </SmallStack>
      </RibbonGroup>
    </>
  );
}

function InsertRibbon({ editor }: { editor: Editor | null }) {
  const insertLink = () => {
    if (!editor) return;
    const previous = editor.getAttributes("link").href as string | undefined;
    const href = window.prompt("Link address", previous ?? "https://");
    if (href === null) return;
    if (href.trim() === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href }).run();
  };
  return (
    <>
      <RibbonGroup label="Pages">
        <LargeButton icon={<FilePlus2 />} label="Page break" onClick={() => editor?.chain().focus().insertContent("<hr data-page-break=\"true\" />").run()} disabled={!editor} />
      </RibbonGroup>
      <RibbonGroup label="Tables">
        <LargeButton icon={<Table2 />} label="Table" onClick={() => editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} disabled={!editor} />
        <SmallStack>
          <TextButton label="Add row" onClick={() => editor?.chain().focus().addRowAfter().run()} disabled={!editor?.can().addRowAfter()} />
          <TextButton label="Add column" onClick={() => editor?.chain().focus().addColumnAfter().run()} disabled={!editor?.can().addColumnAfter()} />
          <TextButton label="Delete table" onClick={() => editor?.chain().focus().deleteTable().run()} disabled={!editor?.can().deleteTable()} />
        </SmallStack>
      </RibbonGroup>
      <RibbonGroup label="Links">
        <LargeButton icon={<Link2 />} label="Link" onClick={insertLink} disabled={!editor} />
      </RibbonGroup>
      <RibbonGroup label="Text">
        <FormatButton label="Horizontal rule" onClick={() => editor?.chain().focus().setHorizontalRule().run()} disabled={!editor}><Minus /></FormatButton>
        <FormatButton label="Code block" active={editor?.isActive("codeBlock")} onClick={() => editor?.chain().focus().toggleCodeBlock().run()} disabled={!editor}><Code2 /></FormatButton>
        <FormatButton label="Inline code" active={editor?.isActive("code")} onClick={() => editor?.chain().focus().toggleCode().run()} disabled={!editor}><Braces /></FormatButton>
      </RibbonGroup>
    </>
  );
}

function LayoutRibbon() {
  return (
    <>
      <RibbonGroup label="Page setup">
        <LargeButton icon={<FileText />} label="Margins" onClick={() => toggleStageClass("narrow-page")} />
        <LargeButton icon={<Columns3 />} label="Columns" onClick={() => toggleStageClass("two-column-page")} />
        <LargeButton icon={<Rows3 />} label="Spacing" onClick={() => toggleStageClass("compact-lines")} />
      </RibbonGroup>
      <RibbonGroup label="Paper">
        <label className="ribbon-field">
          <span>Size</span>
          <select defaultValue="letter" onChange={(event) => setStageData("paper", event.target.value)}>
            <option value="letter">Letter 8.5 × 11 in</option>
            <option value="legal">Legal 8.5 × 14 in</option>
            <option value="a4">A4 210 × 297 mm</option>
          </select>
        </label>
        <label className="ribbon-field">
          <span>Orientation</span>
          <select defaultValue="portrait" onChange={(event) => setStageData("orientation", event.target.value)}>
            <option value="portrait">Portrait</option>
            <option value="landscape">Landscape</option>
          </select>
        </label>
      </RibbonGroup>
      <RibbonGroup label="Paragraph">
        <div className="ribbon-note"><strong>Legal-document defaults</strong><span>One-inch margins, readable line spacing, and print-safe pagination.</span></div>
      </RibbonGroup>
    </>
  );
}

function ReferencesRibbon() {
  const mode = useWorkspace((state) => state.mode);
  const jurisdiction = useWorkspace((state) => state.jurisdiction);
  const setMode = useWorkspace((state) => state.setMode);
  const setJurisdiction = useWorkspace((state) => state.setJurisdiction);
  const runReview = useWorkspace((state) => state.runReview);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  return (
    <>
      <RibbonGroup label="Citation system">
        <label className="ribbon-field">
          <span>Document type</span>
          <select value={mode} onChange={(event) => setMode(event.target.value as typeof mode)}>
            <option value="auto">Detect automatically</option>
            <option value="bluepages">Bluepages, filings</option>
            <option value="whitepages">Whitepages, academic</option>
          </select>
        </label>
        <label className="ribbon-field">
          <span>Jurisdiction</span>
          <select value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)}>
            <option value="federal">Federal</option>
            <option value="california">California</option>
            <option value="new-york">New York</option>
            <option value="texas">Texas</option>
            <option value="other">Other state</option>
          </select>
        </label>
      </RibbonGroup>
      <RibbonGroup label="Citations">
        <LargeButton icon={<BookOpenCheck />} label="Review citations" onClick={() => void runReview()} />
        <LargeButton icon={<FileText />} label="Citation guide" onClick={() => setPaneVisibility("review", true)} />
      </RibbonGroup>
      <RibbonGroup label="Verification">
        <div className="ribbon-note"><strong>Evidence stays separate</strong><span>Formatting, source matching, quotations, and legal judgment remain independently labeled.</span></div>
      </RibbonGroup>
    </>
  );
}

function ReviewRibbon() {
  const runReview = useWorkspace((state) => state.runReview);
  const applyAllSafe = useWorkspace((state) => state.applyAllSafe);
  const deepReview = useWorkspace((state) => state.deepReview);
  const useLocalModel = useWorkspace((state) => state.useLocalModel);
  const setDeepReview = useWorkspace((state) => state.setDeepReview);
  const setUseLocalModel = useWorkspace((state) => state.setUseLocalModel);
  const toggleCompareMode = useWorkspace((state) => state.toggleCompareMode);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  return (
    <>
      <RibbonGroup label="Proofing">
        <LargeButton icon={<SpellCheck2 />} label="Review all" onClick={() => void runReview()} />
        <LargeButton icon={<CheckCheck />} label="Apply safe fixes" onClick={() => void applyAllSafe()} />
      </RibbonGroup>
      <RibbonGroup label="Review depth">
        <Toggle label="Local citation model" checked={useLocalModel} onChange={setUseLocalModel} />
        <Toggle label="Source-backed deep review" checked={deepReview} onChange={setDeepReview} />
        <span className="ribbon-hint">Deep review may use CourtListener when configured.</span>
      </RibbonGroup>
      <RibbonGroup label="Changes">
        <LargeButton icon={<FileDiff />} label="Compare" onClick={toggleCompareMode} />
        <LargeButton icon={<PanelRight />} label="Review pane" onClick={() => setPaneVisibility("review", true)} />
      </RibbonGroup>
    </>
  );
}

function ViewRibbon() {
  const showNavigation = useWorkspace((state) => state.showNavigation);
  const showReviewPane = useWorkspace((state) => state.showReviewPane);
  const showRuler = useWorkspace((state) => state.showRuler);
  const focusMode = useWorkspace((state) => state.focusMode);
  const zoom = useWorkspace((state) => state.zoom);
  const setPaneVisibility = useWorkspace((state) => state.setPaneVisibility);
  const toggleRuler = useWorkspace((state) => state.toggleRuler);
  const toggleFocusMode = useWorkspace((state) => state.toggleFocusMode);
  const setZoom = useWorkspace((state) => state.setZoom);
  return (
    <>
      <RibbonGroup label="Show">
        <Toggle label="Navigation pane" checked={showNavigation} onChange={(value) => setPaneVisibility("navigation", value)} icon={<PanelLeft />} />
        <Toggle label="Review pane" checked={showReviewPane} onChange={(value) => setPaneVisibility("review", value)} icon={<PanelRight />} />
        <Toggle label="Ruler" checked={showRuler} onChange={toggleRuler} icon={<Baseline />} />
      </RibbonGroup>
      <RibbonGroup label="Window">
        <Toggle label="Focus mode" checked={focusMode} onChange={toggleFocusMode} icon={<Maximize2 />} />
      </RibbonGroup>
      <RibbonGroup label="Zoom">
        <button className="zoom-preset" onClick={() => setZoom(100)}>100%</button>
        <button className="zoom-preset" onClick={() => setZoom(120)}>Page width</button>
        <label className="zoom-slider ribbon-zoom">
          <input type="range" min="70" max="180" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} />
          <span>{zoom}%</span>
        </label>
      </RibbonGroup>
    </>
  );
}

function RibbonGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return <section className="ribbon-group"><div className="ribbon-group-body">{children}</div><span className="ribbon-group-label">{label}</span></section>;
}

function LargeButton({ icon, label, onClick, disabled }: { icon: React.ReactNode; label: string; onClick: () => void; disabled?: boolean }) {
  return <button className="ribbon-large-button" onClick={onClick} disabled={disabled}>{icon}<span>{label}</span></button>;
}

function FormatButton({ label, onClick, active, disabled, children }: { label: string; onClick?: () => void; active?: boolean; disabled?: boolean; children: React.ReactNode }) {
  return <button className={`format-button ${active ? "is-active" : ""}`} onClick={onClick} disabled={disabled} aria-label={label} title={label}>{children}</button>;
}

function TextButton({ label, onClick, disabled, icon }: { label: string; onClick: () => void; disabled?: boolean; icon?: React.ReactNode }) {
  return <button className="ribbon-text-button" onClick={onClick} disabled={disabled}>{icon}{label}</button>;
}

function SmallStack({ children }: { children: React.ReactNode }) {
  return <div className="small-stack">{children}</div>;
}

function Toggle({ label, checked, onChange, icon }: { label: string; checked: boolean; onChange: (checked: boolean) => void; icon?: React.ReactNode }) {
  return <label className="ribbon-toggle">{icon}<input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /><span>{label}</span></label>;
}

function activeTextStyle(editor: Editor | null): string {
  if (!editor) return "paragraph";
  if (editor.isActive("heading", { level: 1 })) return "heading-1";
  if (editor.isActive("heading", { level: 2 })) return "heading-2";
  if (editor.isActive("heading", { level: 3 })) return "heading-3";
  if (editor.isActive("blockquote")) return "quote";
  return "paragraph";
}

function applyTextStyle(editor: Editor | null, value: string): void {
  if (!editor) return;
  if (value === "title") editor.chain().focus().setHeading({ level: 1 }).setTextAlign("center").run();
  else if (value === "heading-1") editor.chain().focus().setHeading({ level: 1 }).run();
  else if (value === "heading-2") editor.chain().focus().setHeading({ level: 2 }).run();
  else if (value === "heading-3") editor.chain().focus().setHeading({ level: 3 }).run();
  else if (value === "quote") editor.chain().focus().setBlockquote().run();
  else editor.chain().focus().setParagraph().run();
}

function toggleStageClass(className: string): void {
  document.querySelector(".document-stage")?.classList.toggle(className);
}

function setStageData(name: string, value: string): void {
  const stage = document.querySelector<HTMLElement>(".document-stage");
  if (stage) stage.dataset[name] = value;
}
