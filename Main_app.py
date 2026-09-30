import sys, os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from pynput import keyboard

if getattr(sys, 'frozen', False):
    currentPath = os.path.dirname(sys.executable)
else:
    currentPath = os.path.dirname(os.path.abspath(__file__))

def getpath(filename):
    return os.path.join(currentPath, filename)

# 원하는 캐릭터 표시 크기 지정 (픽셀 단위)
TARGET_WIDTH = 100
TARGET_HEIGHT = 100

def load_scaled_pixmap(filename, w=TARGET_WIDTH, h=TARGET_HEIGHT):
    pix = QPixmap(getpath(filename))
    return pix.scaled(
        w, h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

class KeyboardInputListener(QThread):
    key_pressed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.currently_pressed = set()

    def run(self):
        def on_press(key):
            try:
                key_id = key.char if hasattr(key, 'char') and key.char else key.name
            except Exception:
                key_id = str(key)

            if key_id in self.currently_pressed:
                return

            self.currently_pressed.add(key_id)

            # Ctrl + F8
            has_ctrl = ('ctrl_l' in self.currently_pressed) or ('ctrl_r' in self.currently_pressed)
            
            if key_id == 'f8' and has_ctrl:
                self.key_pressed.emit('ctrl+f8')
            else:
                self.key_pressed.emit(key_id)

        def on_release(key):
            try:
                key_id = key.char if hasattr(key, 'char') and key.char else key.name
            except Exception:
                key_id = str(key)

            self.currently_pressed.discard(key_id)

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard Overlay")

        self.isleft = False
        self.is_locked = False
        self.drag_position = None

        # 위치 저장/불러오기용 QSettings 설정
        self.settings = QSettings("MyPetApp", "KeyboardOverlay")
        saved_pos = self.settings.value("window_pos")
        if saved_pos:
            self.move(saved_pos)

        # 기본 플래그: 테두리 없음 + 항상 위
        self.base_flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(self.base_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 500ms 무입력 타이머
        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.to_idle)

        # 크기 조절된 이미지 불러오기
        self.img_idle = load_scaled_pixmap("idle.png")
        self.img_question = load_scaled_pixmap("question.png")
        self.img_exclamation = load_scaled_pixmap("exclamation.png")
        self.img_left = load_scaled_pixmap("left.png")
        self.img_right = load_scaled_pixmap("right.png")

        # UI
        self.character_label = QLabel(self)
        self.character_label.setPixmap(self.img_idle)

        self.info_label = QLabel("Ctrl + F8: 고정 | 드래그: 이동", self)
        self.info_label.setStyleSheet("color: pink; font-size: 11px; background-color: rgba(0, 0, 0, 150); border: 3px; padding: 4px;")

        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exit_button.clicked.connect(self.close)

        # 텍스트
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.info_label)
        btn_layout.addWidget(self.exit_button)

        # 이미지
        layout = QVBoxLayout()
        layout.addWidget(self.character_label)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 키보드 리스너 연결
        self.listener_thread = KeyboardInputListener()
        self.listener_thread.key_pressed.connect(self.handle_key_input)
        self.listener_thread.start()

    # 마우스 클릭 관통, 고정, 상단에 버튼, 라벨 숨김 토글
    def toggle_lock(self):
        self.is_locked = not self.is_locked

        if self.is_locked:
            # 고정
            self.exit_button.hide()
            self.info_label.hide()
            self.setWindowFlags(self.base_flags | Qt.WindowType.WindowTransparentForInput)
        else:
            # 고정 해제
            self.exit_button.show()
            self.info_label.show()
            self.info_label.setText("이동 가능! (Ctrl + F8로 고정)")
            self.setWindowFlags(self.base_flags)

        # 변경된 윈도우 플래그 적용
        self.show()

    # 창 드래그 이동
    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.is_locked and event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        # 드래그가 끝났을 때 현재 위치 바로 저장
        self.settings.setValue("window_pos", self.pos())

    # 창이 닫힐 때 최종 위치 저장
    def closeEvent(self, event):
        self.settings.setValue("window_pos", self.pos())
        event.accept()

    def to_idle(self):
        self.character_label.setPixmap(self.img_idle)

    # 키 입력
    def handle_key_input(self, key_str):
        # Ctrl + F8 감지
        if key_str == 'ctrl+f8':
            self.toggle_lock()
            return

        # !, ? 감지
        if key_str == '!':
            self.character_label.setPixmap(self.img_exclamation)
        elif key_str == '?':
            self.character_label.setPixmap(self.img_question)
        else:
            # 일반 타자 입력 시 양손 번갈아 치기
            if self.isleft:
                self.character_label.setPixmap(self.img_left)
            else:
                self.character_label.setPixmap(self.img_right)
            self.isleft = not self.isleft

        self.reset_timer.start(500)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec())