from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPixmap, QPen, QCursor

from core.sanitizer import render_image, save_clean


class ImageCanvas(QWidget):
    def __init__(self, cv_image, ocr_boxes: list, auto_regions: list[tuple]):
        super().__init__()
        self.cv_image = cv_image
        self.ocr_boxes = ocr_boxes
        self.blur_regions: list[tuple[int, int, int, int]] = list(auto_regions)
        self._blurred_boxes: set[int] = set()
        self._init_blur_state()
        self._hovered_box_idx: int | None = None
        self._hovered_manual_idx: int | None = None
        self._drag_start: QPoint | None = None
        self._drag_current: QPoint | None = None
        self._is_dragging = False
        self._manual_start_idx = len(auto_regions)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._rendered_pixmap: QPixmap | None = None
        self._rerender()

    def _init_blur_state(self):
        self._blurred_boxes.clear()
        for i, line in enumerate(self.ocr_boxes):
            lx, ly, lw, lh = line["rect"]
            for rx, ry, rw, rh in self.blur_regions:
                if lx < rx + rw and lx + lw > rx and ly < ry + rh and ly + lh > ry:
                    self._blurred_boxes.add(i)
                    break

    def _rerender(self):
        self._rendered_pixmap = render_image(self.cv_image, self.blur_regions)
        self.update()

    def _img_to_widget(self, rect: tuple[int, int, int, int]) -> QRect:
        x, y, w, h = rect
        sx, sy, scale = self._scale_params()
        return QRect(int(x * scale + sx), int(y * scale + sy), int(w * scale), int(h * scale))

    def _widget_to_img(self, pos: QPoint) -> QPoint:
        sx, sy, scale = self._scale_params()
        if scale == 0:
            return QPoint(0, 0)
        return QPoint(int((pos.x() - sx) / scale), int((pos.y() - sy) / scale))

    def _scale_params(self) -> tuple[float, float, float]:
        if self._rendered_pixmap is None:
            return 0.0, 0.0, 1.0
        pw, ph = self._rendered_pixmap.width(), self._rendered_pixmap.height()
        ww, wh = self.width(), self.height()
        scale = min(ww / pw, wh / ph) if pw and ph else 1.0
        return (ww - pw * scale) / 2, (wh - ph * scale) / 2, scale

    def _ocr_box_at(self, pos: QPoint) -> int | None:
        img_pos = self._widget_to_img(pos)
        for i, line in enumerate(self.ocr_boxes):
            x, y, w, h = line["rect"]
            if x <= img_pos.x() <= x + w and y <= img_pos.y() <= y + h:
                return i
        return None

    def _manual_region_at(self, pos: QPoint) -> int | None:
        img_pos = self._widget_to_img(pos)
        for i in range(self._manual_start_idx, len(self.blur_regions)):
            x, y, w, h = self.blur_regions[i]
            if x <= img_pos.x() <= x + w and y <= img_pos.y() <= y + h:
                return i
        return None

    def _any_region_at(self, pos: QPoint) -> int | None:
        img_pos = self._widget_to_img(pos)
        for i, (x, y, w, h) in enumerate(self.blur_regions):
            if x <= img_pos.x() <= x + w and y <= img_pos.y() <= y + h:
                return i
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            self._drag_current = event.pos()
            self._is_dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            manual_idx = self._manual_region_at(event.pos())
            if manual_idx is not None:
                self.blur_regions.pop(manual_idx)
                if manual_idx < self._manual_start_idx:
                    self._manual_start_idx = max(0, self._manual_start_idx - 1)
                self._hovered_manual_idx = None
                self._rerender()

    def mouseMoveEvent(self, event):
        pos = event.pos()

        if self._drag_start is not None:
            delta = pos - self._drag_start
            if not self._is_dragging and (abs(delta.x()) > 5 or abs(delta.y()) > 5):
                self._is_dragging = True
            if self._is_dragging:
                self._drag_current = pos
                self.update()
                return

        prev_ocr = self._hovered_box_idx
        prev_manual = self._hovered_manual_idx

        self._hovered_manual_idx = self._manual_region_at(pos)
        self._hovered_box_idx = self._ocr_box_at(pos) if self._hovered_manual_idx is None else None

        if self._hovered_manual_idx is not None or self._any_region_at(pos) is not None or self._hovered_box_idx is not None:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        if prev_ocr != self._hovered_box_idx or prev_manual != self._hovered_manual_idx:
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._is_dragging and self._drag_start and self._drag_current:
            widget_rect = QRect(self._drag_start, self._drag_current).normalized()
            if widget_rect.width() > 5 and widget_rect.height() > 5:
                p1 = self._widget_to_img(widget_rect.topLeft())
                p2 = self._widget_to_img(widget_rect.bottomRight())
                img_w, img_h = self.cv_image.shape[1], self.cv_image.shape[0]
                x = max(0, p1.x())
                y = max(0, p1.y())
                w = min(img_w - x, p2.x() - p1.x())
                h = min(img_h - y, p2.y() - p1.y())
                if w > 0 and h > 0:
                    self.blur_regions.append((x, y, w, h))
                    self._rerender()
        else:
            pos = event.pos()
            region_idx = self._any_region_at(pos)
            if region_idx is not None:
                self.blur_regions.pop(region_idx)
                if region_idx < self._manual_start_idx:
                    self._manual_start_idx -= 1
                self._blurred_boxes.discard(region_idx)
                self._init_blur_state()
                self._rerender()
            else:
                ocr_idx = self._ocr_box_at(pos)
                if ocr_idx is not None and ocr_idx not in self._blurred_boxes:
                    self.blur_regions.insert(self._manual_start_idx, self.ocr_boxes[ocr_idx]["rect"])
                    self._manual_start_idx += 1
                    self._blurred_boxes.add(ocr_idx)
                    self._rerender()

        self._drag_start = None
        self._drag_current = None
        self._is_dragging = False

    def leaveEvent(self, event):
        self._hovered_box_idx = None
        self._hovered_manual_idx = None
        self.update()

    def paintEvent(self, event):
        if self._rendered_pixmap is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ox, oy, scale = self._scale_params()
        pw = int(self._rendered_pixmap.width() * scale)
        ph = int(self._rendered_pixmap.height() * scale)
        painter.drawPixmap(int(ox), int(oy), pw, ph, self._rendered_pixmap)

        for i, region in enumerate(self.blur_regions):
            wr = self._img_to_widget(region)
            color = QColor(255, 80, 80, 200) if i >= self._manual_start_idx else QColor(255, 160, 0, 200)
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawRect(wr)

        if self._hovered_box_idx is not None and self._hovered_box_idx not in self._blurred_boxes:
            wr = self._img_to_widget(self.ocr_boxes[self._hovered_box_idx]["rect"])
            painter.setPen(QPen(QColor(80, 160, 255, 220), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(80, 160, 255, 30))
            painter.drawRect(wr)

        if self._is_dragging and self._drag_start and self._drag_current:
            drag_rect = QRect(self._drag_start, self._drag_current).normalized()
            painter.setPen(QPen(QColor(255, 80, 80, 220), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(255, 80, 80, 40))
            painter.drawRect(drag_rect)

        painter.end()

    def sizeHint(self) -> QSize:
        if self._rendered_pixmap:
            return QSize(min(self._rendered_pixmap.width(), 1200), min(self._rendered_pixmap.height(), 800))
        return QSize(600, 400)

    def current_pixmap(self) -> QPixmap:
        return render_image(self.cv_image, self.blur_regions)


class PreviewWindow(QWidget):
    def __init__(self, cv_image, ocr_boxes: list, auto_regions: list):
        super().__init__()
        self.setWindowTitle("Blurveil Preview")
        self.canvas = ImageCanvas(cv_image, ocr_boxes, auto_regions)
        hint = self.canvas.sizeHint()
        self.resize(hint.width(), hint.height() + 60)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        main_layout.addWidget(self.canvas)
        buttons_layout = QHBoxLayout()
        btn_copy = QPushButton("Скопировать в буфер")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        buttons_layout.addWidget(btn_copy)
        btn_save = QPushButton("Сохранить как...")
        btn_save.clicked.connect(self.save_to_file)
        buttons_layout.addWidget(btn_save)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def copy_to_clipboard(self):
        QApplication.clipboard().setPixmap(self.canvas.current_pixmap())
        self.close()

    def save_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить изображение", "", "PNG Images (*.png);;JPEG Images (*.jpg)"
        )
        if file_path:
            save_clean(self.canvas.cv_image, self.canvas.blur_regions, file_path)
            self.close()
