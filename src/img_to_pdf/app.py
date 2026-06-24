"""Tk desktop interface for Paperloom."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Any

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # Some Linux Python distributions ship Tk separately.
    tk = None  # type: ignore[assignment]
    filedialog = messagebox = ttk = None  # type: ignore[assignment]
    _TK_IMPORT_ERROR: ImportError | None = exc
else:
    _TK_IMPORT_ERROR = None

from PIL import Image, ImageOps

if _TK_IMPORT_ERROR is None:
    try:
        from PIL import ImageTk
    except ImportError as exc:
        ImageTk = None  # type: ignore[assignment]
        _TK_IMPORT_ERROR = exc
else:
    ImageTk = None  # type: ignore[assignment]

from .converter import ConversionError, PdfOptions, SUPPORTED_EXTENSIONS, convert_images_to_pdf, image_info

if tk is not None:
    try:  # Optional: core conversion stays usable without this small UI enhancement.
        from tkinterdnd2 import DND_FILES, TkinterDnD

        _Root = TkinterDnD.Tk
        HAS_DND = True
    except ImportError:
        _Root = tk.Tk
        HAS_DND = False
else:
    _Root = object
    HAS_DND = False

_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


@dataclass
class ImageItem:
    path: Path
    dimensions: tuple[int, int]


class PaperloomApp(_Root):
    """Interactive image ordering and PDF export window."""

    def __init__(self) -> None:
        if _TK_IMPORT_ERROR is not None:
            raise RuntimeError(
                "Paperloom needs Tk and Pillow's ImageTk support. On Debian/Ubuntu, install them with: "
                "sudo apt install python3-tk python3-pil.imagetk"
            ) from _TK_IMPORT_ERROR
        super().__init__()
        self.title("Paperloom — Images to PDF")
        self.minsize(980, 680)
        self.geometry("1180x760")
        self.configure(bg="#F5F7FB")

        self.items: list[ImageItem] = []
        self.thumbnails: dict[str, ImageTk.PhotoImage] = {}
        self.preview_image: ImageTk.PhotoImage | None = None
        self.events: Queue[tuple[str, Any]] = Queue()
        self.is_converting = False
        self.setting_widgets: list[ttk.Widget] = []

        self.output_path = tk.StringVar()
        self.paper_size = tk.StringVar(value="A4")
        self.orientation = tk.StringVar(value="Auto")
        self.margin = tk.StringVar(value="10")
        self.dpi = tk.StringVar(value="300")
        self.quality = tk.StringVar(value="92")
        self.status = tk.StringVar(value="Add images to begin.")

        self._configure_style()
        self._build_interface()
        self.after(100, self._poll_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#F5F7FB")
        style.configure("Panel.TFrame", background="#FFFFFF")
        style.configure("Title.TLabel", background="#F5F7FB", foreground="#15203B", font=("TkDefaultFont", 22, "bold"))
        style.configure("Subtle.TLabel", background="#F5F7FB", foreground="#62708A", font=("TkDefaultFont", 10))
        style.configure("PanelTitle.TLabel", background="#FFFFFF", foreground="#15203B", font=("TkDefaultFont", 11, "bold"))
        style.configure("PanelText.TLabel", background="#FFFFFF", foreground="#65738D")
        style.configure("TButton", padding=(10, 7), font=("TkDefaultFont", 10, "bold"))
        style.configure("Accent.TButton", background="#4C5DEB", foreground="#FFFFFF", borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#3D4DD4"), ("disabled", "#A8B0E9")])
        style.configure("Treeview", rowheight=72, font=("TkDefaultFont", 10), background="#FFFFFF", fieldbackground="#FFFFFF", foreground="#26344D", borderwidth=0)
        style.configure("Treeview.Heading", font=("TkDefaultFont", 9, "bold"), foreground="#60708D", background="#EEF1F8", relief="flat")
        style.map("Treeview", background=[("selected", "#E0E5FF")], foreground=[("selected", "#15203B")])
        style.configure("TCombobox", padding=5)

    def _build_interface(self) -> None:
        header = ttk.Frame(self, padding=(30, 24, 30, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Paperloom", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Arrange your images, then weave them into a polished PDF.", style="Subtle.TLabel").pack(anchor="w", pady=(3, 0))

        body = ttk.Frame(self, padding=(30, 12, 30, 18))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._build_image_panel(body)
        self._build_settings_panel(body)

        footer = ttk.Frame(self, padding=(30, 0, 30, 24))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, style="Subtle.TLabel").pack(side="left")
        self.progress = ttk.Progressbar(footer, mode="determinate", length=180)
        self.progress.pack(side="right", padx=(14, 0))
        self.convert_button = ttk.Button(footer, text="Convert to PDF", style="Accent.TButton", command=self._start_conversion)
        self.convert_button.pack(side="right")

    def _build_image_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)

        top = ttk.Frame(panel, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Your pages", style="PanelTitle.TLabel").pack(side="left")
        self.add_button = ttk.Button(top, text="＋ Add images", command=self._choose_images)
        self.add_button.pack(side="right")

        hint = "Drop images here or use Add images" if HAS_DND else "Choose images, then arrange their order"
        ttk.Label(panel, text=hint, style="PanelText.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 12))

        table_area = ttk.Frame(panel, style="Panel.TFrame")
        table_area.grid(row=2, column=0, sticky="nsew")
        table_area.columnconfigure(0, weight=1)
        table_area.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_area, columns=("position", "dimensions", "file"), show=("tree", "headings"), selectmode="extended")
        self.table.heading("#0", text="Preview")
        self.table.heading("position", text="#")
        self.table.heading("dimensions", text="Dimensions")
        self.table.heading("file", text="File")
        self.table.column("position", width=42, anchor="center", stretch=False)
        self.table.column("dimensions", width=110, anchor="center", stretch=False)
        self.table.column("file", width=290, anchor="w")
        self.table.column("#0", width=82, minwidth=82, stretch=False, anchor="center")
        scroll = ttk.Scrollbar(table_area, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.table.bind("<<TreeviewSelect>>", self._show_selected_preview)

        controls = ttk.Frame(panel, style="Panel.TFrame")
        controls.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self.up_button = ttk.Button(controls, text="↑ Move up", command=lambda: self._move_selected(-1))
        self.down_button = ttk.Button(controls, text="↓ Move down", command=lambda: self._move_selected(1))
        self.remove_button = ttk.Button(controls, text="Remove", command=self._remove_selected)
        self.clear_button = ttk.Button(controls, text="Clear all", command=self._clear_all)
        for button in (self.up_button, self.down_button, self.remove_button):
            button.pack(side="left", padx=(0, 8))
        self.clear_button.pack(side="right")

        if HAS_DND:
            self.table.drop_target_register(DND_FILES)
            self.table.dnd_bind("<<Drop>>", self._handle_drop)

    def _build_settings_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="Export settings", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(panel, text="The layout is applied to every page.", style="PanelText.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 16))

        form = ttk.Frame(panel, style="Panel.TFrame")
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)
        self._field(form, 0, "Paper size", ttk.Combobox(form, textvariable=self.paper_size, values=("A4", "Letter", "Original"), state="readonly"))
        self._field(form, 2, "Orientation", ttk.Combobox(form, textvariable=self.orientation, values=("Auto", "Portrait", "Landscape"), state="readonly"))
        self._field(form, 4, "Margin (mm)", ttk.Spinbox(form, from_=0, to=100, increment=1, textvariable=self.margin))
        self._field(form, 6, "Output DPI", ttk.Combobox(form, textvariable=self.dpi, values=("150", "200", "300", "450", "600"), state="readonly"))
        self._field(form, 8, "JPEG quality", ttk.Spinbox(form, from_=1, to=100, increment=1, textvariable=self.quality))

        ttk.Separator(panel).grid(row=3, column=0, sticky="ew", pady=18)
        ttk.Label(panel, text="Preview", style="PanelTitle.TLabel").grid(row=4, column=0, sticky="w")
        self.preview_label = ttk.Label(panel, text="Select an image to preview", style="PanelText.TLabel", anchor="center")
        self.preview_label.grid(row=5, column=0, sticky="nsew", pady=(10, 4))
        self.preview_detail = ttk.Label(panel, text="", style="PanelText.TLabel", anchor="center")
        self.preview_detail.grid(row=6, column=0, sticky="ew")
        panel.rowconfigure(5, weight=1)

        ttk.Separator(panel).grid(row=7, column=0, sticky="ew", pady=18)
        ttk.Label(panel, text="Save PDF as", style="PanelTitle.TLabel").grid(row=8, column=0, sticky="w")
        output_row = ttk.Frame(panel, style="Panel.TFrame")
        output_row.grid(row=9, column=0, sticky="ew", pady=(7, 0))
        output_row.columnconfigure(0, weight=1)
        self.output_entry = ttk.Entry(output_row, textvariable=self.output_path)
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.output_button = ttk.Button(output_row, text="Browse", command=self._choose_output)
        self.output_button.grid(row=0, column=1)

    def _field(self, parent: ttk.Frame, row: int, label: str, widget: ttk.Widget) -> None:
        ttk.Label(parent, text=label, style="PanelText.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 5))
        widget.grid(row=row + 1, column=0, sticky="ew", pady=(0, 12))
        self.setting_widgets.append(widget)

    def _choose_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Add images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp *.gif"), ("All files", "*.*")],
        )
        self._add_paths(paths)

    def _handle_drop(self, event: Any) -> None:
        self._add_paths(self.tk.splitlist(event.data))

    def _add_paths(self, raw_paths: tuple[str, ...] | list[str]) -> None:
        existing = {item.path for item in self.items}
        skipped: list[str] = []
        added = 0
        for raw_path in raw_paths:
            path = Path(raw_path).expanduser().resolve()
            if path in existing:
                continue
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped.append(path.name)
                continue
            try:
                dimensions = image_info(path)
            except ConversionError:
                skipped.append(path.name)
                continue
            self.items.append(ImageItem(path, dimensions))
            existing.add(path)
            added += 1
        self._refresh_table()
        if self.items and not self.output_path.get():
            self.output_path.set(str(self.items[0].path.with_suffix(".pdf")))
        if added:
            self.status.set(f"{len(self.items)} image{'s' if len(self.items) != 1 else ''} ready to export.")
        if skipped:
            messagebox.showwarning("Some files were skipped", "Unsupported, unreadable, or duplicate files:\n" + "\n".join(skipped[:8]))

    def _refresh_table(self, selected_paths: set[Path] | None = None) -> None:
        self.table.delete(*self.table.get_children())
        self.thumbnails.clear()
        selected_ids: list[str] = []
        for number, item in enumerate(self.items, start=1):
            identifier = str(number - 1)
            thumbnail = self._thumbnail(item.path)
            values = (number, f"{item.dimensions[0]} × {item.dimensions[1]}", item.path.name)
            self.table.insert("", "end", iid=identifier, image=thumbnail, values=values)
            if selected_paths and item.path in selected_paths:
                selected_ids.append(identifier)
        if selected_ids:
            self.table.selection_set(selected_ids)

    def _thumbnail(self, path: Path) -> ImageTk.PhotoImage:
        try:
            with Image.open(path) as image:
                preview = ImageOps.exif_transpose(image)
                preview.thumbnail((66, 58), _LANCZOS)
                thumbnail = ImageTk.PhotoImage(preview.copy())
        except OSError:
            thumbnail = ImageTk.PhotoImage(Image.new("RGB", (66, 58), "#D8DDEA"))
        self.thumbnails[str(path)] = thumbnail
        return thumbnail

    def _show_selected_preview(self, _event: Any = None) -> None:
        selected = self.table.selection()
        if not selected:
            return
        item = self.items[int(selected[0])]
        try:
            with Image.open(item.path) as image:
                preview = ImageOps.exif_transpose(image)
                preview.thumbnail((310, 260), _LANCZOS)
                self.preview_image = ImageTk.PhotoImage(preview.copy())
            self.preview_label.configure(image=self.preview_image, text="")
            self.preview_detail.configure(text=f"{item.path.name}\n{item.dimensions[0]} × {item.dimensions[1]} px")
        except OSError:
            self.preview_label.configure(image="", text="Preview unavailable")
            self.preview_detail.configure(text=item.path.name)

    def _move_selected(self, direction: int) -> None:
        selected_indices = sorted(int(item) for item in self.table.selection())
        if not selected_indices:
            return
        selected_paths = {self.items[index].path for index in selected_indices}
        selected = set(selected_indices)
        if direction < 0:
            for index in selected_indices:
                if index > 0 and index - 1 not in selected:
                    self.items[index - 1], self.items[index] = self.items[index], self.items[index - 1]
        else:
            for index in reversed(selected_indices):
                if index < len(self.items) - 1 and index + 1 not in selected:
                    self.items[index + 1], self.items[index] = self.items[index], self.items[index + 1]
        self._refresh_table(selected_paths)

    def _remove_selected(self) -> None:
        selected = {int(item) for item in self.table.selection()}
        if not selected:
            return
        self.items = [item for index, item in enumerate(self.items) if index not in selected]
        self._refresh_table()
        self._clear_preview()
        self.status.set("No images selected." if not self.items else f"{len(self.items)} images ready to export.")

    def _clear_all(self) -> None:
        if self.items and not messagebox.askyesno("Clear images", "Remove all images from this conversion?"):
            return
        self.items.clear()
        self._refresh_table()
        self._clear_preview()
        self.status.set("Add images to begin.")

    def _clear_preview(self) -> None:
        self.preview_image = None
        self.preview_label.configure(image="", text="Select an image to preview")
        self.preview_detail.configure(text="")

    def _choose_output(self) -> None:
        initial = self.output_path.get() or "images.pdf"
        path = filedialog.asksaveasfilename(
            title="Save PDF as",
            initialfile=Path(initial).name,
            defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")],
        )
        if path:
            self.output_path.set(path)

    def _start_conversion(self) -> None:
        if self.is_converting:
            return
        if not self.items:
            messagebox.showinfo("Add images", "Choose at least one image before converting.")
            return
        output = self.output_path.get().strip()
        if not output:
            self._choose_output()
            output = self.output_path.get().strip()
            if not output:
                return
        output_path = Path(output).expanduser().with_suffix(".pdf")
        if output_path.exists() and not messagebox.askyesno("Replace existing PDF", f"Replace the existing file?\n\n{output_path}"):
            return
        try:
            options = PdfOptions(
                paper_size=self.paper_size.get(),
                orientation=self.orientation.get(),
                margin_mm=float(self.margin.get()),
                dpi=int(self.dpi.get()),
                quality=int(self.quality.get()),
            )
            options.validate()
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Check export settings", str(exc))
            return

        self.is_converting = True
        self._set_controls_enabled(False)
        self.progress.configure(maximum=len(self.items), value=0)
        self.status.set("Preparing images…")
        paths = [item.path for item in self.items]
        Thread(target=self._convert_worker, args=(paths, output_path, options), daemon=True).start()

    def _convert_worker(self, paths: list[Path], output: Path, options: PdfOptions) -> None:
        def report(current: int, total: int, source: Path) -> None:
            self.events.put(("progress", (current, total, source.name)))

        try:
            result = convert_images_to_pdf(paths, output, options, progress=report)
        except Exception as exc:  # All presentation occurs safely on the Tk event thread.
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("complete", result))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    current, total, name = payload
                    self.progress.configure(maximum=total, value=current)
                    self.status.set(f"Preparing {current} of {total}: {name}")
                elif kind == "complete":
                    self.is_converting = False
                    self._set_controls_enabled(True)
                    self.progress.configure(value=self.progress.cget("maximum"))
                    self.status.set(f"PDF saved to {payload}")
                    messagebox.showinfo("PDF created", f"Your PDF is ready.\n\n{payload}")
                elif kind == "error":
                    self.is_converting = False
                    self._set_controls_enabled(True)
                    self.progress.configure(value=0)
                    self.status.set("Conversion did not finish.")
                    messagebox.showerror("Could not create PDF", payload)
        except Empty:
            pass
        self.after(100, self._poll_events)

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in (self.add_button, self.up_button, self.down_button, self.remove_button, self.clear_button, self.convert_button, self.output_entry, self.output_button):
            widget.configure(state=state)
        for widget in self.setting_widgets:
            widget.configure(state="readonly" if enabled and isinstance(widget, ttk.Combobox) else state)


def main() -> None:
    if _TK_IMPORT_ERROR is not None:
        raise SystemExit(
            "Paperloom cannot start because its desktop GUI requirements are missing. "
            "On Debian/Ubuntu, run: sudo apt install python3-tk python3-pil.imagetk"
        )
    app = PaperloomApp()
    app.mainloop()


if __name__ == "__main__":
    main()
