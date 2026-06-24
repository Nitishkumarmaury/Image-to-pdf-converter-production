"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";

type PageSize = "A4" | "Letter" | "Original";
type Orientation = "Auto" | "Portrait" | "Landscape";

type ImagePage = {
  id: string;
  file: File;
  previewUrl: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ACCEPTED_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "tif", "tiff", "bmp", "gif"];

function isSupported(file: File) {
  const extension = file.name.split(".").pop()?.toLowerCase();
  return file.type.startsWith("image/") || (extension ? ACCEPTED_EXTENSIONS.includes(extension) : false);
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function Icon({ name, size = 18 }: { name: "plus" | "arrowUp" | "arrowDown" | "trash" | "wand" | "file" | "lock" | "arrowRight"; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  const shapes = {
    plus: <><path d="M12 5v14M5 12h14" /></>,
    arrowUp: <><path d="m18 15-6-6-6 6" /><path d="M12 9v11" /></>,
    arrowDown: <><path d="m6 9 6 6 6-6" /><path d="M12 15V4" /></>,
    trash: <><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v5M14 11v5" /></>,
    wand: <><path d="m15 4 5 5M5 19l5.5-5.5M14 5l5 5M3 21l7-7M12 3l.8 3.2L16 7l-3.2.8L12 11l-.8-3.2L8 7l3.2-.8L12 3Z" /></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6M8 13h8M8 17h6" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" /></>,
    arrowRight: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  };
  return <svg {...common}>{shapes[name]}</svg>;
}

export default function Home() {
  const [pages, setPages] = useState<ImagePage[]>([]);
  const pagesRef = useRef<ImagePage[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [pageSize, setPageSize] = useState<PageSize>("A4");
  const [orientation, setOrientation] = useState<Orientation>("Auto");
  const [margin, setMargin] = useState(10);
  const [dpi, setDpi] = useState(300);
  const [quality, setQuality] = useState(92);
  const [isConverting, setIsConverting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    pagesRef.current = pages;
  }, [pages]);

  useEffect(() => () => pagesRef.current.forEach((page) => URL.revokeObjectURL(page.previewUrl)), []);

  function addFiles(incoming: FileList | File[]) {
    const candidates = Array.from(incoming);
    const unsupported = candidates.filter((file) => !isSupported(file));
    const usable = candidates.filter(isSupported);
    setError(unsupported.length ? "A few files were skipped. Add JPG, PNG, WebP, TIFF, BMP, or GIF images." : null);
    setMessage(null);
    setPages((current) => {
      const known = new Set(current.map((page) => `${page.file.name}-${page.file.size}-${page.file.lastModified}`));
      const additions = usable
        .filter((file) => !known.has(`${file.name}-${file.size}-${file.lastModified}`))
        .map((file) => ({ id: crypto.randomUUID(), file, previewUrl: URL.createObjectURL(file) }));
      return [...current, ...additions];
    });
  }

  function handleInput(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) addFiles(event.target.files);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (event.dataTransfer.files.length) addFiles(event.dataTransfer.files);
  }

  function removePage(id: string) {
    setPages((current) => {
      const removed = current.find((page) => page.id === id);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      return current.filter((page) => page.id !== id);
    });
  }

  function movePage(index: number, direction: -1 | 1) {
    setPages((current) => {
      const destination = index + direction;
      if (destination < 0 || destination >= current.length) return current;
      const next = [...current];
      [next[index], next[destination]] = [next[destination], next[index]];
      return next;
    });
  }

  function clearPages() {
    pages.forEach((page) => URL.revokeObjectURL(page.previewUrl));
    setPages([]);
    setMessage(null);
    setError(null);
  }

  async function createPdf() {
    if (!pages.length || isConverting) return;
    setIsConverting(true);
    setError(null);
    setMessage("Uploading your pages and weaving the PDF…");
    const form = new FormData();
    pages.forEach((page) => form.append("files", page.file));
    form.append("page_size", pageSize);
    form.append("orientation", orientation);
    form.append("margin_mm", String(margin));
    form.append("dpi", String(dpi));
    form.append("quality", String(quality));

    try {
      const response = await fetch(`${API_URL}/api/convert`, { method: "POST", body: form });
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "The PDF could not be created. Please try again.");
      }
      const pdfBlob = await response.blob();
      const downloadUrl = URL.createObjectURL(pdfBlob);
      const anchor = document.createElement("a");
      anchor.href = downloadUrl;
      anchor.download = "paperloom.pdf";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(downloadUrl);
      setMessage("Your PDF is ready — the download has started.");
    } catch (caught) {
      setMessage(null);
      setError(caught instanceof Error ? caught.message : "Something went sideways while creating the PDF.");
    } finally {
      setIsConverting(false);
    }
  }

  return (
    <main className="site-shell">
      <div className="aurora aurora-one" />
      <div className="aurora aurora-two" />
      <nav className="topbar" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="Paperloom home"><span className="brand-mark">p</span>paperloom</a>
        <div className="nav-note"><span className="signal" />Image to PDF, beautifully</div>
      </nav>

      <section className="hero" id="top">
        <p className="eyebrow"><span /> A slower, better kind of utility</p>
        <h1>Turn a loose stack<br />into <em>something finished.</em></h1>
        <p className="hero-copy">Arrange your images, settle the details, and let Paperloom make a PDF that feels considered from the first page to the last.</p>
        <div className="hero-meta">
          <span><Icon name="lock" size={15} /> Temporary uploads. No account.</span>
          <span>JPG · PNG · WEBP · TIFF</span>
        </div>
      </section>

      <section className="workbench" aria-label="PDF creation workspace">
        <div
          className={`upload-zone ${isDragging ? "is-dragging" : ""} ${pages.length ? "has-pages" : ""}`}
          onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <input id="image-picker" className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp,image/tiff,image/bmp,image/gif" multiple onChange={handleInput} />
          {!pages.length ? (
            <div className="empty-upload">
              <div className="upload-illustration"><span className="sheet back" /><span className="sheet middle" /><span className="sheet front"><Icon name="plus" size={25} /></span></div>
              <h2>Bring in your images</h2>
              <p>Drop a stack here, or browse your device.</p>
              <label className="button button-dark" htmlFor="image-picker"><Icon name="plus" />Select images</label>
              <small>Up to 40 images · 25 MB each</small>
            </div>
          ) : (
            <div className="page-manager">
              <header className="panel-header">
                <div><p className="section-kicker">Your sequence</p><h2>{pages.length} {pages.length === 1 ? "page" : "pages"} in the loom</h2></div>
                <div className="panel-actions"><label className="text-button" htmlFor="image-picker"><Icon name="plus" size={16} />Add more</label><button className="text-button muted" type="button" onClick={clearPages}>Clear all</button></div>
              </header>
              <div className="image-grid">
                {pages.map((page, index) => (
                  <article className="image-card" key={page.id}>
                    <div className="image-number">{String(index + 1).padStart(2, "0")}</div>
                    <div className="image-preview"><img src={page.previewUrl} alt="" /></div>
                    <div className="image-info"><strong title={page.file.name}>{page.file.name}</strong><span>{formatBytes(page.file.size)}</span></div>
                    <div className="image-controls">
                      <button type="button" aria-label={`Move ${page.file.name} earlier`} disabled={index === 0} onClick={() => movePage(index, -1)}><Icon name="arrowUp" size={15} /></button>
                      <button type="button" aria-label={`Move ${page.file.name} later`} disabled={index === pages.length - 1} onClick={() => movePage(index, 1)}><Icon name="arrowDown" size={15} /></button>
                      <button className="remove" type="button" aria-label={`Remove ${page.file.name}`} onClick={() => removePage(page.id)}><Icon name="trash" size={15} /></button>
                    </div>
                  </article>
                ))}
                <label className="add-tile" htmlFor="image-picker"><Icon name="plus" /><span>Add image</span></label>
              </div>
            </div>
          )}
        </div>

        <aside className="settings-panel">
          <div className="settings-title"><div className="star-icon"><Icon name="wand" size={20} /></div><div><p className="section-kicker">The finishing room</p><h2>Make it yours</h2></div></div>
          <label className="field-label">Page format
            <select value={pageSize} onChange={(event) => setPageSize(event.target.value as PageSize)}>
              <option value="A4">A4 — 210 × 297 mm</option><option value="Letter">Letter — 8.5 × 11 in</option><option value="Original">Original image ratio</option>
            </select>
          </label>
          <label className="field-label">Orientation
            <div className="segmented-control">
              {(["Auto", "Portrait", "Landscape"] as Orientation[]).map((choice) => <button key={choice} type="button" className={orientation === choice ? "selected" : ""} onClick={() => setOrientation(choice)}>{choice}</button>)}
            </div>
          </label>
          <div className="range-row"><label className="field-label" htmlFor="margin">Margin <span>{margin} mm</span></label><input id="margin" type="range" min="0" max="35" value={margin} onChange={(event) => setMargin(Number(event.target.value))} /></div>
          <div className="setting-pair">
            <label className="field-label">DPI<select value={dpi} onChange={(event) => setDpi(Number(event.target.value))}><option value="150">150 · light</option><option value="200">200 · balanced</option><option value="300">300 · crisp</option><option value="450">450 · print</option></select></label>
            <label className="field-label">Quality<select value={quality} onChange={(event) => setQuality(Number(event.target.value))}><option value="80">80%</option><option value="86">86%</option><option value="92">92%</option><option value="100">100%</option></select></label>
          </div>
          <div className="tip"><Icon name="file" size={18} /><p><strong>Thoughtful by default.</strong> Images are fitted inside the page, never cropped.</p></div>
        </aside>
      </section>

      <section className="export-bar" aria-live="polite">
        <div className="export-status">
          {error ? <p className="error-message">{error}</p> : message ? <p className="success-message">{message}</p> : <p><span className="ready-dot" />{pages.length ? "Your pages are ready to become a PDF." : "The canvas is waiting for your first image."}</p>}
        </div>
        <button className="button button-lime export-button" type="button" disabled={!pages.length || isConverting} onClick={createPdf}>
          {isConverting ? <span className="spinner" /> : <Icon name="wand" />} {isConverting ? "Weaving your PDF…" : "Create my PDF"}<Icon name="arrowRight" size={17} />
        </button>
      </section>

      <footer><span>Paperloom</span><p>Crafted for the little documents that matter.</p><span>Private by design</span></footer>
    </main>
  );
}
