import type { Editor } from "@tiptap/core";
import {
  ArrowClockwise,
  ArrowCounterClockwise,
  CheckCircle,
  Export,
  FilePlus,
  FolderOpen,
  Highlighter,
  LinkSimple,
  ListBullets,
  ListNumbers,
  Minus,
  Play,
  SidebarSimple,
  Table,
  TextAlignCenter,
  TextAlignJustify,
  TextAlignLeft,
  TextAlignRight,
  TextB,
  TextItalic,
  TextStrikethrough,
  TextUnderline,
} from "@phosphor-icons/react";
import type { ReactNode } from "react";

import type { ExportFormat } from "../services/applicationAdapter";

export type RibbonTab = "File" | "Home" | "Insert" | "Review" | "View";
export type DocumentViewMode = "editing" | "reviewed" | "compare";

interface RibbonProps {
  activeTab: RibbonTab;
  onTabChange(tab: RibbonTab): void;
  editor: Editor | null;
  onNewDocument(): void;
  onOpenDocument(): void;
  onSave(): void;
  onRunReview(): void;
  onExport(format: ExportFormat): void;
  onToggleLibrary(): void;
  onToggleReviewPane(): void;
  reviewPaneVisible: boolean;
  libraryVisible: boolean;
  mode: string;
  onModeChange(mode: string): void;
  jurisdiction: string | null;
  onJurisdictionChange(jurisdiction: string | null): void;
  viewMode: DocumentViewMode;
  onViewModeChange(mode: DocumentViewMode): void;
  zoom: number;
  onZoomChange(zoom: number): void;
  busy: boolean;
}

const TABS: RibbonTab[] = ["File", "Home", "Insert", "Review", "View"];

function RibbonGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="ribbon-group" aria-label={label}>
      <div className="ribbon-group-content">{children}</div>
      <span className="ribbon-group-label">{label}</span>
    </section>
  );
}

interface CommandButtonProps {
  label: string;
  icon?: ReactNode;
  active?: boolean;
  disabled?: boolean;
  compact?: boolean;
  onClick(): void;
}

function CommandButton({
  label,
  icon,
  active = false,
  disabled = false,
  compact = false,
  onClick,
}: CommandButtonProps) {
  return (
    <button
      type="button"
      className={`ribbon-command${active ? " is-active" : ""}${compact ? " is-compact" : ""}`}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      title={label}
    >
      {icon}
      {!compact && <span>{label}</span>}
    </button>
  );
}

function HomeCommands({ editor, onSave }: Pick<RibbonProps, "editor" | "onSave">) {
  const disabled = editor === null;
  const chain = () => editor?.chain().focus();
  return (
    <>
      <RibbonGroup label="Document">
        <CommandButton label="Save" onClick={onSave} />
      </RibbonGroup>
      <RibbonGroup label="Undo">
        <div className="ribbon-row">
          <CommandButton
            compact
            label="Undo"
            icon={<ArrowCounterClockwise size={18} />}
            disabled={disabled || !editor?.can().chain().focus().undo().run()}
            onClick={() => chain()?.undo().run()}
          />
          <CommandButton
            compact
            label="Redo"
            icon={<ArrowClockwise size={18} />}
            disabled={disabled || !editor?.can().chain().focus().redo().run()}
            onClick={() => chain()?.redo().run()}
          />
        </div>
      </RibbonGroup>
      <RibbonGroup label="Font">
        <div className="ribbon-stack">
          <div className="ribbon-row">
            <select
              aria-label="Font family"
              className="ribbon-select font-family-select"
              disabled={disabled}
              defaultValue="Aptos"
              onChange={(event) =>
                chain()?.setFontFamily(event.currentTarget.value).run()
              }
            >
              <option value="Aptos">Aptos</option>
              <option value="Arial">Arial</option>
              <option value="Calibri">Calibri</option>
              <option value="Georgia">Georgia</option>
              <option value="Times New Roman">Times New Roman</option>
            </select>
            <select
              aria-label="Font size"
              className="ribbon-select font-size-select"
              disabled={disabled}
              defaultValue="11"
              onChange={(event) =>
                chain()
                  ?.setMark("textStyle", {
                    fontSize: `${event.currentTarget.value}px`,
                  })
                  .run()
              }
            >
              {[9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
          <div className="ribbon-row">
            <CommandButton
              compact
              label="Bold"
              icon={<TextB size={18} weight="bold" />}
              active={editor?.isActive("bold") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleBold().run()}
            />
            <CommandButton
              compact
              label="Italic"
              icon={<TextItalic size={18} />}
              active={editor?.isActive("italic") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleItalic().run()}
            />
            <CommandButton
              compact
              label="Underline"
              icon={<TextUnderline size={18} />}
              active={editor?.isActive("underline") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleUnderline().run()}
            />
            <CommandButton
              compact
              label="Strikethrough"
              icon={<TextStrikethrough size={18} />}
              active={editor?.isActive("strike") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleStrike().run()}
            />
            <label className="ribbon-color-control" title="Text color">
              <span aria-hidden="true">A</span>
              <input
                type="color"
                aria-label="Text color"
                disabled={disabled}
                defaultValue="#1f2328"
                onChange={(event) => chain()?.setColor(event.currentTarget.value).run()}
              />
            </label>
            <label className="ribbon-color-control" title="Highlight color">
              <Highlighter size={17} aria-hidden="true" />
              <input
                type="color"
                aria-label="Highlight color"
                disabled={disabled}
                defaultValue="#fff2a8"
                onChange={(event) =>
                  chain()?.setHighlight({ color: event.currentTarget.value }).run()
                }
              />
            </label>
          </div>
        </div>
      </RibbonGroup>
      <RibbonGroup label="Paragraph">
        <div className="ribbon-stack">
          <div className="ribbon-row">
            <CommandButton
              compact
              label="Bulleted list"
              icon={<ListBullets size={18} />}
              active={editor?.isActive("bulletList") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleBulletList().run()}
            />
            <CommandButton
              compact
              label="Numbered list"
              icon={<ListNumbers size={18} />}
              active={editor?.isActive("orderedList") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleOrderedList().run()}
            />
            <CommandButton
              compact
              label="Block quote"
              active={editor?.isActive("blockquote") ?? false}
              disabled={disabled}
              onClick={() => chain()?.toggleBlockquote().run()}
            />
          </div>
          <div className="ribbon-row">
            <CommandButton
              compact
              label="Align left"
              icon={<TextAlignLeft size={18} />}
              active={editor?.isActive({ textAlign: "left" }) ?? false}
              disabled={disabled}
              onClick={() => chain()?.setTextAlign("left").run()}
            />
            <CommandButton
              compact
              label="Align center"
              icon={<TextAlignCenter size={18} />}
              active={editor?.isActive({ textAlign: "center" }) ?? false}
              disabled={disabled}
              onClick={() => chain()?.setTextAlign("center").run()}
            />
            <CommandButton
              compact
              label="Align right"
              icon={<TextAlignRight size={18} />}
              active={editor?.isActive({ textAlign: "right" }) ?? false}
              disabled={disabled}
              onClick={() => chain()?.setTextAlign("right").run()}
            />
            <CommandButton
              compact
              label="Justify"
              icon={<TextAlignJustify size={18} />}
              active={editor?.isActive({ textAlign: "justify" }) ?? false}
              disabled={disabled}
              onClick={() => chain()?.setTextAlign("justify").run()}
            />
          </div>
        </div>
      </RibbonGroup>
      <RibbonGroup label="Styles">
        <select
          aria-label="Paragraph style"
          className="ribbon-select style-select"
          disabled={disabled}
          defaultValue="paragraph"
          onChange={(event) => {
            const style = event.currentTarget.value;
            if (style === "paragraph") chain()?.setParagraph().run();
            else chain()?.toggleHeading({ level: Number(style) as 1 | 2 | 3 }).run();
          }}
        >
          <option value="paragraph">Normal</option>
          <option value="1">Title</option>
          <option value="2">Heading 1</option>
          <option value="3">Heading 2</option>
        </select>
      </RibbonGroup>
    </>
  );
}

function FileCommands({
  onNewDocument,
  onOpenDocument,
  onExport,
}: Pick<RibbonProps, "onNewDocument" | "onOpenDocument" | "onExport">) {
  return (
    <>
      <RibbonGroup label="Create">
        <CommandButton
          label="New document"
          icon={<FilePlus size={24} />}
          onClick={onNewDocument}
        />
        <CommandButton
          label="Open"
          icon={<FolderOpen size={24} />}
          onClick={onOpenDocument}
        />
      </RibbonGroup>
      <RibbonGroup label="Export">
        <CommandButton
          label="Word"
          icon={<Export size={22} />}
          onClick={() => onExport("docx")}
        />
        <CommandButton label="PDF" onClick={() => onExport("pdf")} />
        <CommandButton label="Markdown" onClick={() => onExport("md")} />
        <CommandButton label="Text" onClick={() => onExport("txt")} />
      </RibbonGroup>
    </>
  );
}

function InsertCommands({ editor }: Pick<RibbonProps, "editor">) {
  const chain = () => editor?.chain().focus();
  const setLink = () => {
    if (editor === null) return;
    const previous = editor.getAttributes("link").href as string | undefined;
    const href = window.prompt("Link address", previous ?? "https://");
    if (href === null) return;
    if (href.trim() === "") chain()?.unsetLink().run();
    else chain()?.extendMarkRange("link").setLink({ href: href.trim() }).run();
  };
  return (
    <>
      <RibbonGroup label="Tables">
        <CommandButton
          label="Table"
          icon={<Table size={24} />}
          disabled={editor === null}
          onClick={() =>
            chain()?.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
          }
        />
      </RibbonGroup>
      <RibbonGroup label="Links">
        <CommandButton
          label="Link"
          icon={<LinkSimple size={24} />}
          active={editor?.isActive("link") ?? false}
          disabled={editor === null}
          onClick={setLink}
        />
      </RibbonGroup>
      <RibbonGroup label="Elements">
        <CommandButton
          label="Divider"
          icon={<Minus size={24} />}
          disabled={editor === null}
          onClick={() => chain()?.setHorizontalRule().run()}
        />
        <CommandButton
          label="Page break"
          disabled={editor === null}
          onClick={() => chain()?.insertContent("\n\n<div data-page-break></div>\n\n").run()}
        />
      </RibbonGroup>
    </>
  );
}

function ReviewCommands({
  onRunReview,
  busy,
  mode,
  onModeChange,
  jurisdiction,
  onJurisdictionChange,
  reviewPaneVisible,
  onToggleReviewPane,
}: Pick<
  RibbonProps,
  | "onRunReview"
  | "busy"
  | "mode"
  | "onModeChange"
  | "jurisdiction"
  | "onJurisdictionChange"
  | "reviewPaneVisible"
  | "onToggleReviewPane"
>) {
  return (
    <>
      <RibbonGroup label="AutoCite">
        <CommandButton
          label={busy ? "Reviewing" : "Run AutoCite review"}
          icon={<Play size={24} weight="fill" />}
          disabled={busy}
          onClick={onRunReview}
        />
        <CommandButton
          label="Review pane"
          icon={<SidebarSimple size={24} />}
          active={reviewPaneVisible}
          onClick={onToggleReviewPane}
        />
      </RibbonGroup>
      <RibbonGroup label="Citation style">
        <label className="ribbon-field">
          <span>Mode</span>
          <select value={mode} onChange={(event) => onModeChange(event.currentTarget.value)}>
            <option value="auto">Automatic</option>
            <option value="bluepages">Bluepages</option>
            <option value="whitepages">Whitepages</option>
          </select>
        </label>
        <label className="ribbon-field">
          <span>Jurisdiction</span>
          <select
            value={jurisdiction ?? ""}
            onChange={(event) =>
              onJurisdictionChange(event.currentTarget.value || null)
            }
          >
            <option value="">Automatic</option>
            <option value="federal">Federal</option>
            <option value="california">California</option>
            <option value="new-york">New York</option>
            <option value="texas">Texas</option>
          </select>
        </label>
      </RibbonGroup>
      <RibbonGroup label="Decisions">
        <div className="ribbon-callout">
          <CheckCircle size={22} weight="fill" />
          <span>Only supported safe edits apply automatically.</span>
        </div>
      </RibbonGroup>
    </>
  );
}

function ViewCommands({
  onToggleLibrary,
  onToggleReviewPane,
  libraryVisible,
  reviewPaneVisible,
  viewMode,
  onViewModeChange,
  zoom,
  onZoomChange,
}: Pick<
  RibbonProps,
  | "onToggleLibrary"
  | "onToggleReviewPane"
  | "libraryVisible"
  | "reviewPaneVisible"
  | "viewMode"
  | "onViewModeChange"
  | "zoom"
  | "onZoomChange"
>) {
  return (
    <>
      <RibbonGroup label="Panes">
        <CommandButton
          label="Document library"
          active={libraryVisible}
          onClick={onToggleLibrary}
        />
        <CommandButton
          label="AutoCite review"
          active={reviewPaneVisible}
          onClick={onToggleReviewPane}
        />
      </RibbonGroup>
      <RibbonGroup label="Document view">
        {(["editing", "reviewed", "compare"] as const).map((view) => (
          <CommandButton
            key={view}
            label={view[0].toUpperCase() + view.slice(1)}
            active={viewMode === view}
            onClick={() => onViewModeChange(view)}
          />
        ))}
      </RibbonGroup>
      <RibbonGroup label="Zoom">
        <input
          aria-label="Document zoom"
          type="range"
          min="70"
          max="160"
          step="5"
          value={zoom}
          onChange={(event) => onZoomChange(Number(event.currentTarget.value))}
        />
        <span className="zoom-value">{zoom}%</span>
      </RibbonGroup>
    </>
  );
}

export function Ribbon(props: RibbonProps) {
  return (
    <div className="ribbon-shell">
      <div className="ribbon-tabs" role="tablist" aria-label="Document commands">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={props.activeTab === tab}
            className={props.activeTab === tab ? "is-active" : ""}
            onClick={() => props.onTabChange(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="ribbon-content" role="tabpanel" aria-label={`${props.activeTab} commands`}>
        {props.activeTab === "File" && <FileCommands {...props} />}
        {props.activeTab === "Home" && <HomeCommands {...props} />}
        {props.activeTab === "Insert" && <InsertCommands {...props} />}
        {props.activeTab === "Review" && <ReviewCommands {...props} />}
        {props.activeTab === "View" && <ViewCommands {...props} />}
      </div>
    </div>
  );
}
