from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QSize
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPixmap, QPen, QCursor

import cv2
from gui.errors import safe_slot
from core.sanitizer import apply_blur_regions, cv_image_to_qpixmap, render_image


class ImageCanvas(QWidget):
    def __init__(self, cv_image, ocr_boxes: list, auto_regions: list[tuple]):
        super().__init__()
        self.cv_image = cv_image
        self.ocr_boxes = ocr_boxes
        # Each region: {'rect': (x,y,w,h), 'active': bool, 'auto': bool}
        self._regions: list[dict] = [{'rect': r, 'active': True, 'auto': True} for r in auto_regions]
        self._hovered_region_idx: int | None = None
        self._hovered_ocr_idx: int | None = None
        self._drag_start: QPoint | None = None
        self._drag_current: QPoint | None = None
        self._is_dragging = False
        self._crop_rect: tuple[int, int, int, int] = (0, 0, cv_image.shape[1], cv_image.shape[0])
        self._crop_drag_handle: str | None = None
        self._crop_drag_offset: QPoint | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._rendered_pixmap: QPixmap | None = None
        self._rerender()

    def _rerender(self):
        self._rendered_pixmap = render_image(self.cv_image, self.blur_regions)
        self.update()

    @property
    def blur_regions(self) -> list[tuple]:
        return [r['rect'] for r in self._regions if r['active']]

    def _img_to_widget(self, rect: tuple) -> QRect:
        x, y, w, h = rect
        sx, sy, scale = self._scale_params()
        return QRect(int(x * scale + sx), int(y * scale + sy), int(w * scale), int(h * scale))

    def _widget_to_img(self, pos: QPoint) -> QPoint:
        sx, sy, scale = self._scale_params()
        if scale == 0:
            return QPoint(0, 0)
        return QPoint(int((pos.x() - sx) / scale), int((pos.y() - sy) / scale))

    def _clamped_img_pos(self, pos: QPoint) -> QPoint:
        img_pos = self._widget_to_img(pos)
        img_w, img_h = self.cv_image.shape[1], self.cv_image.shape[0]
        return QPoint(
            max(0, min(img_w, img_pos.x())),
            max(0, min(img_h, img_pos.y())),
        )

    def _scale_params(self) -> tuple[float, float, float]:
        if self._rendered_pixmap is None:
            return 0.0, 0.0, 1.0
        pw, ph = self._rendered_pixmap.width(), self._rendered_pixmap.height()
        ww, wh = self.width(), self.height()
        scale = min(ww / pw, wh / ph) if pw and ph else 1.0
        return (ww - pw * scale) / 2, (wh - ph * scale) / 2, scale

    def _region_at(self, pos: QPoint) -> int | None:
        img_pos = self._widget_to_img(pos)
        for i, region in enumerate(self._regions):
            x, y, w, h = region['rect']
            if x <= img_pos.x() <= x + w and y <= img_pos.y() <= y + h:
                return i
        return None

    def _ocr_box_at(self, pos: QPoint) -> int | None:
        img_pos = self._widget_to_img(pos)
        for i, line in enumerate(self.ocr_boxes):
            x, y, w, h = line["rect"]
            if x <= img_pos.x() <= x + w and y <= img_pos.y() <= y + h:
                return i
        return None

    def _crop_handle_at(self, pos: QPoint, allow_move: bool = False) -> str | None:
        crop_wr = self._img_to_widget(self._crop_rect)
        if not crop_wr.adjusted(-8, -8, 8, 8).contains(pos):
            return None

        near_left = abs(pos.x() - crop_wr.left()) <= 8
        near_right = abs(pos.x() - crop_wr.right()) <= 8
        near_top = abs(pos.y() - crop_wr.top()) <= 8
        near_bottom = abs(pos.y() - crop_wr.bottom()) <= 8

        if near_top and near_left:
            return "top_left"
        if near_top and near_right:
            return "top_right"
        if near_bottom and near_left:
            return "bottom_left"
        if near_bottom and near_right:
            return "bottom_right"
        if near_left:
            return "left"
        if near_right:
            return "right"
        if near_top:
            return "top"
        if near_bottom:
            return "bottom"
        if allow_move and crop_wr.contains(pos) and not self._is_full_crop():
            return "move"
        return None

    def _crop_cursor(self, handle: str | None):
        cursors = {
            "move": Qt.CursorShape.SizeAllCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "top_left": Qt.CursorShape.SizeFDiagCursor,
            "bottom_right": Qt.CursorShape.SizeFDiagCursor,
            "top_right": Qt.CursorShape.SizeBDiagCursor,
            "bottom_left": Qt.CursorShape.SizeBDiagCursor,
        }
        return cursors.get(handle)

    def _update_crop_rect(self, handle: str, pos: QPoint):
        img_pos = self._clamped_img_pos(pos)
        img_w, img_h = self.cv_image.shape[1], self.cv_image.shape[0]
        min_size = 10
        x, y, w, h = self._crop_rect

        if handle == "move":
            offset = self._crop_drag_offset or QPoint(w // 2, h // 2)
            new_x = max(0, min(img_w - w, img_pos.x() - offset.x()))
            new_y = max(0, min(img_h - h, img_pos.y() - offset.y()))
            self._crop_rect = (new_x, new_y, w, h)
            self.update()
            return

        left, top = x, y
        right, bottom = x + w, y + h

        if "left" in handle:
            left = min(max(0, img_pos.x()), right - min_size)
        if "right" in handle:
            right = max(min(img_w, img_pos.x()), left + min_size)
        if "top" in handle:
            top = min(max(0, img_pos.y()), bottom - min_size)
        if "bottom" in handle:
            bottom = max(min(img_h, img_pos.y()), top + min_size)

        self._crop_rect = (left, top, right - left, bottom - top)
        self.update()

    def reset_crop(self):
        self._crop_rect = (0, 0, self.cv_image.shape[1], self.cv_image.shape[0])
        self.update()

    def _is_full_crop(self) -> bool:
        return self._crop_rect == (0, 0, self.cv_image.shape[1], self.cv_image.shape[0])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            allow_move = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            crop_handle = self._crop_handle_at(event.pos(), allow_move=allow_move)
            if crop_handle is not None:
                self._crop_drag_handle = crop_handle
                img_pos = self._clamped_img_pos(event.pos())
                x, y, _w, _h = self._crop_rect
                self._crop_drag_offset = QPoint(img_pos.x() - x, img_pos.y() - y)
                self.setCursor(QCursor(self._crop_cursor(crop_handle)))
                return
            self._drag_start = event.pos()
            self._drag_current = event.pos()
            self._is_dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            region_idx = self._region_at(event.pos())
            if region_idx is not None:
                self._regions.pop(region_idx)
                self._hovered_region_idx = None
                self._rerender()

    def mouseMoveEvent(self, event):
        pos = event.pos()

        if self._crop_drag_handle is not None:
            self._update_crop_rect(self._crop_drag_handle, pos)
            return

        if self._drag_start is not None:
            delta = pos - self._drag_start
            if not self._is_dragging and (abs(delta.x()) > 5 or abs(delta.y()) > 5):
                self._is_dragging = True
            if self._is_dragging:
                self._drag_current = pos
                self.update()
                return

        prev_region = self._hovered_region_idx
        prev_ocr = self._hovered_ocr_idx

        allow_move = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        crop_handle = self._crop_handle_at(pos, allow_move=allow_move)
        self._hovered_region_idx = None if crop_handle is not None else self._region_at(pos)
        if crop_handle is not None:
            self._hovered_ocr_idx = None
        elif self._hovered_region_idx is not None:
            self._hovered_ocr_idx = None
        else:
            self._hovered_ocr_idx = self._ocr_box_at(pos)

        crop_cursor = self._crop_cursor(crop_handle)
        if crop_cursor is not None:
            self.setCursor(QCursor(crop_cursor))
        elif self._hovered_region_idx is not None or self._hovered_ocr_idx is not None:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        if prev_region != self._hovered_region_idx or prev_ocr != self._hovered_ocr_idx:
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._crop_drag_handle is not None:
            self._crop_drag_handle = None
            self._crop_drag_offset = None
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        elif self._is_dragging and self._drag_start and self._drag_current:
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
                    self._regions.append({'rect': (x, y, w, h), 'active': True, 'auto': False})
                    self._rerender()
        else:
            pos = event.pos()
            region_idx = self._region_at(pos)
            if region_idx is not None:
                self._regions[region_idx]['active'] = not self._regions[region_idx]['active']
                self._rerender()
            else:
                ocr_idx = self._ocr_box_at(pos)
                if ocr_idx is not None:
                    self._regions.append({'rect': tuple(self.ocr_boxes[ocr_idx]["rect"]), 'active': True, 'auto': False})
                    self._rerender()

        self._drag_start = None
        self._drag_current = None
        self._is_dragging = False

    def leaveEvent(self, event):
        self._hovered_region_idx = None
        self._hovered_ocr_idx = None
        if self._crop_drag_handle is None:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
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

        for region in self._regions:
            wr = self._img_to_widget(region['rect'])
            if region['active']:
                color = QColor(255, 160, 0, 200) if region['auto'] else QColor(255, 80, 80, 200)
                painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
            else:
                painter.setPen(QPen(QColor(160, 160, 160, 180), 2, Qt.PenStyle.DashLine))
                painter.setBrush(QColor(160, 160, 160, 25))
            painter.drawRect(wr)

        if self._hovered_ocr_idx is not None:
            wr = self._img_to_widget(self.ocr_boxes[self._hovered_ocr_idx]["rect"])
            painter.setPen(QPen(QColor(80, 160, 255, 220), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(80, 160, 255, 30))
            painter.drawRect(wr)

        if self._is_dragging and self._drag_start and self._drag_current:
            drag_rect = QRect(self._drag_start, self._drag_current).normalized()
            painter.setPen(QPen(QColor(255, 80, 80, 220), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor(255, 80, 80, 40))
            painter.drawRect(drag_rect)

        self._paint_crop_overlay(painter, QRect(int(ox), int(oy), pw, ph))

        painter.end()

    def _paint_crop_overlay(self, painter: QPainter, image_rect: QRect):
        crop_wr = self._img_to_widget(self._crop_rect)

        overlay = QPainterPath()
        overlay.addRect(QRectF(image_rect))
        hole = QPainterPath()
        hole.addRect(QRectF(crop_wr))
        painter.fillPath(overlay.subtracted(hole), QColor(0, 0, 0, 90))

        painter.setPen(QPen(QColor(255, 255, 255, 230), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_wr)

        painter.setPen(QPen(QColor(40, 40, 40, 220), 1, Qt.PenStyle.SolidLine))
        painter.setBrush(QColor(255, 255, 255, 235))
        for point in self._crop_handle_points(crop_wr):
            painter.drawRect(QRect(point.x() - 4, point.y() - 4, 8, 8))

    def _crop_handle_points(self, rect: QRect) -> list[QPoint]:
        cx = rect.center().x()
        cy = rect.center().y()
        return [
            rect.topLeft(),
            QPoint(cx, rect.top()),
            rect.topRight(),
            QPoint(rect.right(), cy),
            rect.bottomRight(),
            QPoint(cx, rect.bottom()),
            rect.bottomLeft(),
            QPoint(rect.left(), cy),
        ]

    def sizeHint(self) -> QSize:
        if self._rendered_pixmap:
            return QSize(min(self._rendered_pixmap.width(), 1200), min(self._rendered_pixmap.height(), 800))
        return QSize(600, 400)

    def current_pixmap(self) -> QPixmap:
        return cv_image_to_qpixmap(self.current_cv_image())

    def current_cv_image(self):
        result = apply_blur_regions(self.cv_image, self.blur_regions)
        x, y, w, h = self._crop_rect
        return result[y:y+h, x:x+w].copy()

    def save_current(self, file_path: str) -> bool:
        result = self.current_cv_image()
        if file_path.lower().endswith(('.jpg', '.jpeg')):
            return cv2.imwrite(file_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return cv2.imwrite(file_path, result)


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
        btn_reset_crop = QPushButton("Сбросить обрезку")
        btn_reset_crop.clicked.connect(self.canvas.reset_crop)
        buttons_layout.addWidget(btn_reset_crop)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    @safe_slot("Не удалось скопировать изображение")
    def copy_to_clipboard(self, *_args):
        QApplication.clipboard().setPixmap(self.canvas.current_pixmap())
        self.close()

    @safe_slot("Не удалось сохранить изображение")
    def save_to_file(self, *_args):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить изображение", "", "PNG Images (*.png);;JPEG Images (*.jpg)"
        )
        if file_path:
            if not self.canvas.save_current(file_path):
                raise RuntimeError(f"Не удалось записать файл: {file_path}")
            self.close()
