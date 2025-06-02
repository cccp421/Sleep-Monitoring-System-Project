import sys
from TGAM.version3.gui import TGAMGUI
from PyQt5.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = TGAMGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()