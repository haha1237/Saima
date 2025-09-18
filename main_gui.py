#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from gui import BatchCommandGUI

def main():
    # 启动GUI应用程序
    app = BatchCommandGUI()
    app.mainloop()

if __name__ == "__main__":
    main()