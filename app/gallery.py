"""Thumbnail grid: model (items + selection + thumbnail cache) and the tile painter."""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QListView, QStyle, QStyledItemDelegate

from .engine import ImportHistory, MediaItem, human_size
from .i18n import tr
from .styles import c

TILE = 156          # thumbnail square
CELL = QSize(TILE + 14, TILE + 40)
CACHE_LIMIT = 1500
ItemRole = Qt.UserRole + 1


class GalleryModel(QAbstractListModel):
    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: List[MediaItem] = []
        self.selected: Set[str] = set()
        self.thumbs: "OrderedDict[str, QPixmap]" = OrderedDict()
        self.history: Optional[ImportHistory] = None
        self._row: Dict[str, int] = {}

    # ---- Qt model API
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self.items[index.row()]
        if role == ItemRole:
            return item
        if role == Qt.ToolTipRole:
            when = item.date.strftime("%d/%m/%Y %H:%M") if item.date else ""
            return f"{item.name}\n{when}\n{human_size(item.size)}"
        return None

    # ---- content
    def set_items(self, items: List[MediaItem], select_new: bool = True):
        self.beginResetModel()
        self.items = items
        self._row = {it.id: r for r, it in enumerate(items)}
        if select_new:
            self.selected = {it.id for it in items if not self.is_imported(it)}
        else:
            keep = {it.id for it in items}
            self.selected &= keep
        self.endResetModel()
        self.selection_changed.emit()

    def is_imported(self, item: MediaItem) -> bool:
        return self.history is not None and self.history.contains(item)

    def toggle(self, row: int):
        item = self.items[row]
        if item.id in self.selected:
            self.selected.discard(item.id)
        else:
            self.selected.add(item.id)
        idx = self.index(row)
        self.dataChanged.emit(idx, idx)
        self.selection_changed.emit()

    def select_all(self, on: bool):
        self.selected = {it.id for it in self.items} if on else set()
        if self.items:
            self.dataChanged.emit(self.index(0), self.index(len(self.items) - 1))
        self.selection_changed.emit()

    def selected_items(self) -> List[MediaItem]:
        # oldest first, so files land in the order they were taken
        return sorted((it for it in self.items if it.id in self.selected), key=lambda i: (i.date is None, i.date, i.name))

    def refresh_all(self):
        if self.items:
            self.dataChanged.emit(self.index(0), self.index(len(self.items) - 1))

    # ---- thumbnails
    def set_thumbnail(self, item_id: str, image: QImage):
        pm = _square(image, TILE * 2)
        self.thumbs[item_id] = pm
        self.thumbs.move_to_end(item_id)
        while len(self.thumbs) > CACHE_LIMIT:
            self.thumbs.popitem(last=False)
        row = self._row.get(item_id)
        if row is not None:
            idx = self.index(row)
            self.dataChanged.emit(idx, idx)

    def missing_thumbs(self, start: int = 0) -> List[MediaItem]:
        order = self.items[start:] + self.items[:start]
        return [it for it in order if it.id not in self.thumbs]

    def clear_thumbs(self):
        self.thumbs.clear()


def _square(image: QImage, size: int) -> QPixmap:
    """Centre-crop to a square (like the iPhone's own grid)."""
    w, h = image.width(), image.height()
    side = min(w, h)
    cropped = image.copy((w - side) // 2, (h - side) // 2, side, side)
    return QPixmap.fromImage(cropped.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class TileDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return CELL

    def paint(self, p: QPainter, option, index):
        model: GalleryModel = index.model()
        item: MediaItem = index.data(ItemRole)
        if item is None:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = option.rect
        tile = QRectF(r.x() + 7, r.y() + 6, TILE, TILE)
        selected = item.id in model.selected
        hover = bool(option.state & QStyle.State_MouseOver)

        path = QPainterPath()
        path.addRoundedRect(tile, 12, 12)
        p.setClipPath(path)
        pm = model.thumbs.get(item.id)
        if pm is not None:
            p.drawPixmap(tile.toRect(), pm)
        else:
            p.fillRect(tile, QColor(c("tile")))
            f = QFont(p.font())
            f.setPixelSize(12)
            p.setFont(f)
            p.setPen(QColor(c("muted")))
            p.drawText(tile.adjusted(8, 8, -8, -8), Qt.AlignCenter | Qt.TextWrapAnywhere, item.name)
        if not selected:
            p.fillRect(tile, QColor(255, 255, 255, 70 if hover else 110))
        p.setClipping(False)

        if item.kind == "video":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 140))
            badge = QRectF(tile.left() + 8, tile.bottom() - 28, 30, 20)
            p.drawRoundedRect(badge, 6, 6)
            p.setBrush(QColor("white"))
            cx, cy = badge.center().x(), badge.center().y()
            p.drawPolygon(QPolygonF([QPointF(cx - 4, cy - 6), QPointF(cx - 4, cy + 6), QPointF(cx + 6, cy)]))

        if model.is_imported(item):
            f = QFont(p.font())
            f.setPixelSize(11)
            f.setBold(True)
            p.setFont(f)
            text = tr("imported_badge")
            tw = p.fontMetrics().horizontalAdvance(text) + 14
            badge = QRectF(tile.left() + 8, tile.top() + 8, tw, 20)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(22, 163, 74, 225))
            p.drawRoundedRect(badge, 10, 10)
            p.setPen(QColor("white"))
            p.drawText(badge, Qt.AlignCenter, text)

        # selection ring + check circle
        if selected:
            p.setPen(QPen(QColor(c("accent")), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(tile.adjusted(1.5, 1.5, -1.5, -1.5), 11, 11)
        circle = QRectF(tile.right() - 32, tile.top() + 8, 24, 24)
        if selected:
            p.setPen(QPen(QColor("white"), 2))
            p.setBrush(QColor(c("accent")))
            p.drawEllipse(circle)
            p.setPen(QPen(QColor("white"), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline([QPointF(circle.left() + 6.5, circle.center().y() + 0.5),
                            QPointF(circle.left() + 10.5, circle.bottom() - 7.5),
                            QPointF(circle.right() - 6, circle.top() + 7.5)])
        else:
            p.setPen(QPen(QColor("white"), 2))
            p.setBrush(QColor(0, 0, 0, 50))
            p.drawEllipse(circle)

        # caption: time + name
        f = QFont(p.font())
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(QColor(c("text") if selected else c("muted")))
        when = item.date.strftime("%d/%m/%y %H:%M") if item.date else ""
        cap = QRect(int(tile.left()), int(tile.bottom()) + 4, TILE, 16)
        p.drawText(cap, Qt.AlignLeft | Qt.AlignVCenter, when)
        p.drawText(cap, Qt.AlignRight | Qt.AlignVCenter, item.name.split(".")[-1].upper())
        p.restore()


class GalleryView(QListView):
    scrolled = Signal(int)  # first visible row

    def __init__(self, model: GalleryModel, parent=None):
        super().__init__(parent)
        self.setModel(model)
        self.setItemDelegate(TileDelegate(self))
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setUniformItemSizes(True)
        self.setGridSize(CELL)
        self.setSpacing(0)
        self.setSelectionMode(QListView.NoSelection)
        self.setMouseTracking(True)
        self.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(24)
        self.setContentsMargins(10, 10, 10, 10)
        self.setViewportMargins(10, 10, 10, 0)
        self.clicked.connect(lambda idx: model.toggle(idx.row()))
        self.verticalScrollBar().valueChanged.connect(lambda _v: self.scrolled.emit(self.first_visible()))

    def first_visible(self) -> int:
        idx = self.indexAt(QPoint(20, 20))
        return idx.row() if idx.isValid() else 0
