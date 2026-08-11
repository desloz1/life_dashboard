import datetime

import qtawesome as qta
from PySide6.QtCore import QByteArray, QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import common
import log
import theme
import webcams

logger = log.get_logger("life_dashboard.webcams_ui")

STATE_TEXT = {"loading": "Carregando…", "live": "AO VIVO", "offline": "OFFLINE"}


class WebcamWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            cams = webcams.fetch_webcams()
        except Exception as exc:
            logger.error("Falha ao buscar webcams: %s", exc)
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        for cam in cams:
            if cam.get("poster_url"):
                cam["poster"] = common.download_image_bytes(cam["poster_url"])
        if not self.isInterruptionRequested():
            self.finished_ok.emit(cams)


class WebcamCard(QFrame):
    open_requested = Signal(str)

    def __init__(self, cam, parent=None):
        super().__init__(parent)
        self.cam = cam
        self._state = "loading"
        self._player = None
        self._audio = None
        self._poster_pix = None
        self.setObjectName("webcamCard")
        self.setProperty("state", self._state)
        self.style().unpolish(self)
        self.style().polish(self)
        common.make_shadow(self, y=3, blur=16)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        icon = QLabel()
        icon.setObjectName("webcamIcon")
        icon.setPixmap(qta.icon("fa5s.video", color=theme.ACCENT).pixmap(20, 20))
        header.addWidget(icon)

        self.name = QLabel(cam["name"])
        self.name.setObjectName("webcamName")
        self.name.setToolTip(cam["name"])
        header.addWidget(self.name)

        self.state_badge = QLabel(STATE_TEXT[self._state])
        self.state_badge.setObjectName("webcamState")
        self.state_badge.setProperty("state", self._state)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)
        header.addWidget(self.state_badge)

        header.addStretch()

        loc = QLabel(cam["location"])
        loc.setObjectName("webcamLoc")
        loc.setToolTip(cam["location"])
        header.addWidget(loc)

        provider = QLabel(cam.get("provider", ""))
        provider.setObjectName("newsSource")
        header.addWidget(provider)

        open_btn = QToolButton()
        open_btn.setObjectName("cardBtn")
        open_btn.setIcon(qta.icon("fa5s.external-link-alt", color=theme.ACCENT))
        open_btn.setIconSize(QSize(14, 14))
        open_btn.setFixedSize(26, 26)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setToolTip("Abrir no navegador")
        open_btn.clicked.connect(lambda: self.open_requested.emit(cam["page"]))
        header.addWidget(open_btn)

        refresh_btn = QToolButton()
        refresh_btn.setObjectName("cardBtn")
        refresh_btn.setIcon(qta.icon("fa5s.redo", color=theme.MUTED))
        refresh_btn.setIconSize(QSize(14, 14))
        refresh_btn.setFixedSize(26, 26)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setToolTip("Recarregar transmissão")
        refresh_btn.clicked.connect(self.retry)
        header.addWidget(refresh_btn)

        root.addLayout(header)

        self.video_stack = QStackedWidget()
        self.video_stack.setObjectName("webcamVideoArea")
        self.video_stack.setFixedHeight(280)
        root.addWidget(self.video_stack)

        self._build_poster_page(cam)
        self._build_player(cam)

    def _build_poster_page(self, cam):
        self.poster_label = QLabel()
        self.poster_label.setObjectName("webcamPoster")
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data = cam.get("poster")
        if data:
            pix = QPixmap()
            if pix.loadFromData(QByteArray(data)):
                self._poster_pix = pix
        if self._poster_pix is None:
            self.poster_label.setPixmap(
                qta.icon("fa5s.video-slash", color=theme.MUTED).pixmap(52, 52)
            )
        else:
            self._fit_poster()
        self.video_stack.addWidget(self.poster_label)

    def _fit_poster(self):
        if self._poster_pix is None or self._poster_pix.isNull():
            return
        area = self.video_stack.size()
        width = max(40, area.width() - 2)
        height = max(40, area.height() - 2)
        self.poster_label.setPixmap(
            self._poster_pix.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _build_player(self, cam):
        stream = cam.get("stream")
        if not stream:
            self._set_state("offline")
            return
        video = QVideoWidget()
        video.setObjectName("webcamVideo")
        self.video_stack.addWidget(video)
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._audio.setMuted(True)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(video)
        self._player.errorOccurred.connect(self._on_error)
        self._player.playbackStateChanged.connect(self._on_playback_state)
        self._player.setSource(QUrl(stream))
        self._player.play()

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.video_stack.setCurrentIndex(1)
            self._set_state("live")

    def _on_error(self, error, error_string):
        if error == QMediaPlayer.Error.NoError:
            return
        logger.warning("Webcam %s com erro de reprodução: %s", self.cam["name"], error_string)
        self._set_state("offline")

    def _set_state(self, state):
        self._state = state
        self.setProperty("state", state)
        self.state_badge.setProperty("state", state)
        self.state_badge.setText(STATE_TEXT[state])
        self.style().unpolish(self)
        self.style().polish(self)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)
        self.update()

    def retry(self):
        if self._player is None:
            return
        self.video_stack.setCurrentIndex(0)
        self._set_state("loading")
        self._player.stop()
        self._player.setSource(QUrl(self.cam["stream"]))
        self._player.play()

    def set_active(self, active):
        if self._player is None:
            return
        if active:
            if self._state != "offline":
                self._player.play()
        else:
            self._player.pause()

    def shutdown(self):
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QUrl())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_poster()


class WebcamsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._cards = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = common.make_title("fa5s.video", "Webcams")
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.refresh_btn = QPushButton(" Atualizar")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_webcams)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.load_webcams()

    def load_webcams(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self._clear_cards()
        self.refresh_btn.setEnabled(False)
        self.status.setText("Buscando transmissões…")
        self._worker = WebcamWorker(self)
        self._worker.finished_ok.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._worker.start()

    def _clear_cards(self):
        for card in self._cards:
            card.shutdown()
        self._cards = []
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_loaded(self, cams):
        self._cards = []
        if not cams:
            empty = QLabel("Nenhuma transmissão encontrada.\nTente atualizar mais tarde.")
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText("Nenhuma transmissão")
            return
        for cam in cams:
            card = WebcamCard(cam)
            card.open_requested.connect(self._open_link)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            self._cards.append(card)
        live = sum(1 for cam in cams if cam.get("stream"))
        total = len(cams)
        noun = "transmissão" if total == 1 else "transmissões"
        self.status.setText(f"{total} {noun} · {live} ao vivo")
        if not self.isVisible():
            self.set_active(False)

    def _on_failed(self, error):
        self._clear_cards()
        empty = QLabel(f"Não foi possível carregar as webcams:\n{error}")
        empty.setObjectName("errorLabel")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.insertWidget(0, empty)
        self.status.setText("Falha ao carregar")

    def refresh(self):
        for card in self._cards:
            card.style().unpolish(card)
            card.style().polish(card)
            card.update()

    def set_active(self, active):
        for card in self._cards:
            card.set_active(active)

    def shutdown(self):
        for card in self._cards:
            card.shutdown()
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(3000)

    def _open_link(self, url):
        QDesktopServices.openUrl(QUrl(url))
