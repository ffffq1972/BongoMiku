# pyinstaller -y --noconsole --onefile --uac-admin Source_Code.py

import sys, os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from pynput import keyboard

if getattr(sys, 'frozen', False):
    currentPath = os.path.dirname(sys.executable)
else:
    currentPath = os.path.dirname(os.path.abspath(__file__))

currentPath = os.path.join(currentPath, "Images/")

def getpath(filename):
    return os.path.join(currentPath, filename)

def load_scaled_pixmap(filename, size):
    pix = QPixmap(getpath(filename))
    return pix.scaled(
        size, size,
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

            # Ctrl + F8 감지
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
        self.current_size = 250  # 기본 크기 (250x250)

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

        # 이미지 리소스 로드
        self.reload_images(self.current_size)

        # 캐릭터 라벨
        self.character_label = QLabel(self)
        self.character_label.setPixmap(self.img_idle)
        self.character_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 상단 1줄: 안내 라벨 및 Exit 버튼
        self.info_label = QLabel("Ctrl + F8: 고정 | 드래그: 이동", self)
        self.info_label.setStyleSheet("color: pink; font-size: 11px; background-color: rgba(0, 0, 0, 150); border: 3px; padding: 4px;")

        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.exit_button.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.exit_button.clicked.connect(self.close)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.info_label)
        btn_layout.addWidget(self.exit_button)

        # 상단 2줄: 크기 조절 버튼 5개 (가로 배치 및 콤팩트 스타일 적용)
        self.btn_tiny = QPushButton("SMALL!", self)
        self.btn_small = QPushButton("Small", self)
        self.btn_middle = QPushButton("Middle", self)
        self.btn_big = QPushButton("Big", self)
        self.btn_huge = QPushButton("BIG!", self)

        self.size_buttons = [self.btn_tiny, self.btn_small, self.btn_middle, self.btn_big, self.btn_huge]

        # 버튼들이 옆으로 너무 퍼지지 않도록 작은 패딩과 폰트 크기 지정
        btn_style = "padding: 2px 4px; font-size: 10px;"

        for btn in self.size_buttons:
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(btn_style)

        self.btn_tiny.clicked.connect(lambda: self.resize_character(50))
        self.btn_small.clicked.connect(lambda: self.resize_character(100))
        self.btn_middle.clicked.connect(lambda: self.resize_character(175))
        self.btn_big.clicked.connect(lambda: self.resize_character(250))
        self.btn_huge.clicked.connect(lambda: self.resize_character(600))

        size_layout = QHBoxLayout()
        size_layout.setSpacing(4)  # 버튼 사이 간격 좁히기
        size_layout.addWidget(self.btn_tiny)
        size_layout.addWidget(self.btn_small)
        size_layout.addWidget(self.btn_middle)
        size_layout.addWidget(self.btn_big)
        size_layout.addWidget(self.btn_huge)

        # 전체 레이아웃 구성
        layout = QVBoxLayout()
        layout.addWidget(self.character_label)
        layout.addLayout(btn_layout)
        layout.addLayout(size_layout)

        self.setLayout(layout)

        # 키보드 리스너 연결
        self.listener_thread = KeyboardInputListener()
        self.listener_thread.key_pressed.connect(self.handle_key_input)
        self.listener_thread.start()

    # 이미지들을 주어진 크기로 다시 로드
    def reload_images(self, size):
        self.img_idle = load_scaled_pixmap("idle.png", size)
        self.img_question = load_scaled_pixmap("question.png", size)
        self.img_exclamation = load_scaled_pixmap("exclamation.png", size)
        self.img_left = load_scaled_pixmap("left.png", size)
        self.img_right = load_scaled_pixmap("right.png", size)

    # 버튼 클릭 시 캐릭터 크기 변경
    def resize_character(self, size):
        self.current_size = size
        self.reload_images(size)
        self.character_label.setPixmap(self.img_idle)
        self.adjustSize()

    # 마우스 클릭 관통, 고정, 버튼 및 라벨 숨김 토글
    def toggle_lock(self):
        self.is_locked = not self.is_locked

        if self.is_locked:
            self.exit_button.hide()
            self.info_label.hide()
            for btn in self.size_buttons:
                btn.hide()
            self.setWindowFlags(self.base_flags | Qt.WindowType.WindowTransparentForInput)
        else:
            self.exit_button.show()
            self.info_label.show()
            self.info_label.setText("이동 가능! (Ctrl + F8로 고정)")
            for btn in self.size_buttons:
                btn.show()
            self.setWindowFlags(self.base_flags)

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
        self.settings.setValue("window_pos", self.pos())

    # 창이 닫힐 때 최종 위치 저장
    def closeEvent(self, event):
        self.settings.setValue("window_pos", self.pos())
        event.accept()

    def to_idle(self):
        self.character_label.setPixmap(self.img_idle)

    # 키 입력 처리
    def handle_key_input(self, key_str):
        # Ctrl + F8 감지
        if key_str == 'ctrl+f8':
            self.toggle_lock()
            return

        # 단독 특수 제어키 무시
        if key_str in ('ctrl_l', 'ctrl_r', 'shift', 'shift_r', 'alt_l', 'alt_gr'):
            return

        # !, ? 감지
        if key_str == '!':
            self.character_label.setPixmap(self.img_exclamation)
        elif key_str == '?':
            self.character_label.setPixmap(self.img_question)
        else:
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