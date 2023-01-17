from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow

import sys
from ui.app import MainApplication
from ui import constants

class MainApplicationContext(ApplicationContext):
    def run(self):
        constants.setup()

        window = MainApplication(self)
        window.resize(350, 250)
        window.setMinimumSize(350, 250)
        window.show()
        return self.app.exec_()

if __name__ == '__main__':
    appctxt = MainApplicationContext()
    exit_code = appctxt.run()    # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)