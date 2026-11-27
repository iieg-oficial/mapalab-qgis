from typing import Any

from qgis.PyQt.QtCore import QModelIndex, QRectF, QSize, Qt
from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPainterPath
from qgis.PyQt.QtWidgets import QComboBox, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from ..theme import color_de_rol, color_de_selector

ALTO: int = 32

MARGEN: int = 3

RELLENO: int = 10

RADIO: float = 4.0

MARCADO: int = 2

ROL_SECCION: int = int(Qt.ItemDataRole.UserRole) + 1

ALTO_SECCION: int = 28

HOVER: QColor = QColor(70, 80, 85, 20)


class DelegadoMenu(QStyledItemDelegate):

    def __init__(self, combo: QComboBox) -> None:
        super().__init__(combo)
        self._combo = combo
        self._realce = QColor(color_de_selector('QTreeView::item:selected',
                                                'background-color', '#FFE9CC'))
        self._realce_tinta = QColor(color_de_selector('QTreeView::item:selected',
                                                      'color', '#A85700'))
        self._tinta = QColor(color_de_rol('quiet', 'color', '#465055'))

    def _activo(self, index: QModelIndex) -> bool:
        estado = index.data(Qt.ItemDataRole.CheckStateRole)
        if estado is not None:
            return estado in (Qt.CheckState.Checked, MARCADO)
        return index.row() == self._combo.currentIndex()

    def _pintar_seccion(self, painter: QPainter, option: QStyleOptionViewItem,
                        index: QModelIndex) -> None:
        fuente = QFont(option.font)
        fuente.setBold(True)
        fuente.setPointSizeF(max(1.0, fuente.pointSizeF() - 1))
        painter.setFont(fuente)
        painter.setPen(self._realce_tinta)
        rect = option.rect.adjusted(MARGEN + RELLENO, 4, -RELLENO, 0)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                         str(index.data(Qt.ItemDataRole.DisplayRole) or '').upper())

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        painter.save()
        if index.data(ROL_SECCION):
            self._pintar_seccion(painter, option, index)
            painter.restore()
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(option.rect.adjusted(MARGEN, 1, -MARGEN, -1))
        activo = self._activo(index)
        encima = bool(option.state & (QStyle.StateFlag.State_MouseOver
                                      | QStyle.StateFlag.State_Selected))
        fondo = self._realce if activo else (HOVER if encima else None)
        if fondo is not None:
            camino = QPainterPath()
            camino.addRoundedRect(rect, RADIO, RADIO)
            painter.fillPath(camino, fondo)
        painter.setPen(self._realce_tinta if activo else self._tinta)
        painter.setFont(option.font)
        texto_rect = rect.adjusted(RELLENO, 0, -RELLENO, 0).toRect()
        texto = option.fontMetrics.elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole) or ''),
            Qt.TextElideMode.ElideRight, texto_rect.width())
        painter.drawText(texto_rect, int(Qt.AlignmentFlag.AlignVCenter
                                         | Qt.AlignmentFlag.AlignLeft), texto)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        size = super().sizeHint(option, index)
        if index.data(ROL_SECCION):
            return QSize(size.width(), ALTO_SECCION)
        return QSize(size.width() + RELLENO * 2, max(size.height(), ALTO))


def como_menu(combo: Any) -> None:
    combo.view().setItemDelegate(DelegadoMenu(combo))
    combo.view().setMouseTracking(True)
