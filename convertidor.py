import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QApplication

from convertidor_ui import Ui_MainWindow  

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.mode = "bin_to_hex"  

        self.ui.pushButton_16.clicked.connect(self.set_bin_to_hex_mode)  # Binario-Hexa
        self.ui.pushButton_17.clicked.connect(self.set_hex_to_bin_mode)  # Hexa-binario

        digit_buttons = {
            '0': self.ui.pushButton_5,
            '1': self.ui.pushButton_6,
            '2': self.ui.pushButton_2,
            '3': self.ui.pushButton_7,
            '4': self.ui.pushButton_20,
            '5': self.ui.pushButton,
            '6': self.ui.pushButton_11,
            '7': self.ui.pushButton_3,
            '8': self.ui.pushButton_19,
            '9': self.ui.pushButton_15,
            'A': self.ui.pushButton_12,
            'B': self.ui.pushButton_4,
            'C': self.ui.pushButton_18,
            'D': self.ui.pushButton_14,
            'E': self.ui.pushButton_13,
            'F': self.ui.pushButton_9,
        }

        for key, btn in digit_buttons.items():
            btn.clicked.connect(lambda _, k=key: self.append_input(k))

        # Conectar botones LIMPIAR y CONVERTIR
        self.ui.pushButton_8.clicked.connect(self.clear_inputs)
        self.ui.pushButton_10.clicked.connect(self.convert)

    def set_bin_to_hex_mode(self):
        self.mode = "bin_to_hex"
        self.clear_inputs()

    def set_hex_to_bin_mode(self):
        self.mode = "hex_to_bin"
        self.clear_inputs()

    def append_input(self, char):
        if self.mode == "bin_to_hex":
            if char in '01':
                self.ui.lineEdit.setText(self.ui.lineEdit.text() + char)
        elif self.mode == "hex_to_bin":
            self.ui.lineEdit_2.setText(self.ui.lineEdit_2.text() + char)

    def clear_inputs(self):
        self.ui.lineEdit.clear()
        self.ui.lineEdit_2.clear()

    def convert(self):
        if self.mode == "bin_to_hex":
            binary_str = self.ui.lineEdit.text()
            try:
                value = int(binary_str, 2)
                self.ui.lineEdit_2.setText(hex(value)[2:].upper())
            except ValueError:
                self.ui.lineEdit_2.setText("ERROR")
        elif self.mode == "hex_to_bin":
            hex_str = self.ui.lineEdit_2.text()
            try:
                value = int(hex_str, 16)
                self.ui.lineEdit.setText(bin(value)[2:])
            except ValueError:
                self.ui.lineEdit.setText("ERROR")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle("Romero Melany")
    window.show()
    sys.exit(app.exec())
