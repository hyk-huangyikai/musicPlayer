import sys
import os.path

import asyncio
import logging
from quamash import QEventLoop
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from widget import Navigation,Header,MainContent,DetailSings
from player import Player
from function import ConfigNavigation,ConfigWindow,ConfigDetailSings

from search_from_header import ConfigHeader
from search_area import SearchArea
from config_search_area import ConfigSearchArea
from song_list import ConfigMainContent, NetEaseSingsArea, XiamiSingsArea, QQSingsArea, ConfigNetEase 
import addition

transTime = addition.itv2time

# 用于承载整个界面。所有窗口的父窗口，所有窗口都可以在父窗口里找到索引。
class mainWindow(QWidget):
    """Window 承载整个界面 """

    # 初始化
    def __init__(self):
        super(mainWindow, self).__init__()
        self.setObjectName('MainWindow')  # 声明窗口名字
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowIcon(QIcon('resource/format.ico'))  # 图标
        self.setWindowTitle("Music")  # 声明窗口的标题
        self.resize(1000, 800)  # 重设大小

        self.setUI()  # 加载各个组件
        self.setTab()  # 设置tab
        self.addSongList()
        self.setLines()  # 对布局进行细线设置
        self.setLayouts()  # 设置整体布局
        self.setFunction()  # 设置各项组件功能

        with open('QSS/window.qss', 'r') as f:
            self.setStyleSheet(f.read())

    # 设置UI界面
    def setUI(self):
        self.header = Header(self)  # 标题栏
        self.navigation = Navigation(self)  # 左边导航栏
        self.mainContent = MainContent(self)  # 主要内容区
        self.player = Player(self)  # 播放区
        self.mainContents = QTabWidget()  # 页面栏

        self.detailSings = DetailSings(self)  # 音乐资源
        # 搜索页面
        self.searchArea = SearchArea(self)  # 搜索区

    def addSongList(self):
        self.indexNetEaseSings = NetEaseSingsArea(self.mainContent)
        self.indexXiamiSings = XiamiSingsArea(self.mainContent)
        self.indexQQSings = QQSingsArea(self.mainContent)

        self.mainContent.addTab(self.indexNetEaseSings, "网易云歌单")
        self.mainContent.addTab(self.indexXiamiSings, "虾米歌单")
        self.mainContent.addTab(self.indexQQSings, "QQ歌单")

    # 设置布局
    def setLayouts(self):
        self.mainLayout = QVBoxLayout()  # 垂直布局
        self.mainLayout.addWidget(self.header)  # 添加标题栏
        self.mainLayout.addWidget(self.line1)  # 线条

        self.contentLayout = QHBoxLayout()  # 水平布局
        self.contentLayout.setStretch(0, 70)
        self.contentLayout.setStretch(1, 570)

        self.contentLayout.addWidget(self.navigation)  # 添加左边导航栏
        self.contentLayout.addWidget(self.line2)  # 线条
        self.contentLayout.addWidget(self.mainContents)  # 添加主要内容区
        self.contentLayout.setSpacing(0)
        self.contentLayout.setContentsMargins(0, 0, 0, 0)

        self.mainLayout.addLayout(self.contentLayout)
        self.mainLayout.addWidget(self.line1)
        self.mainLayout.addWidget(self.player)  # 添加播放区

        self.mainLayout.setStretch(0, 43)
        self.mainLayout.setStretch(1, 0)
        self.mainLayout.setStretch(2, 576)
        self.mainLayout.setStretch(3, 50)

        self.mainLayout.setSpacing(0)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

    # 布局。
    def setTab(self):
        """设置tab界面。"""
        # 增加搜索显示区域
        
        self.mainContents.addTab(self.mainContent, '')
        self.mainContents.addTab(self.detailSings, '')
        self.mainContents.addTab(self.searchArea, '')
        self.mainContents.setCurrentIndex(0)

    def setLines(self):
        """设置布局小细线。"""
        self.line1 = QFrame(self)  # 用于在组件周围添加边框
        self.line1.setObjectName("line1")
        self.line1.setFrameShape(QFrame.HLine)  # 设置边框，水平线
        self.line1.setFrameShadow(QFrame.Plain)  # 设置窗口无阴影
        self.line1.setLineWidth(4)  # 设置线条宽度


        self.line2 = QFrame(self)
        self.line2.setObjectName("line2")
        self.line2.setFrameShape(QFrame.VLine)  # 设置边框，垂直线
        self.line2.setFrameShadow(QFrame.Plain)  # 设置窗口无阴影
        self.line2.setLineWidth(4)  # 设置线条宽度

    def setFunction(self):
        # self.config = ConfigWindow(self)
        self.navigation.config = ConfigNavigation(self.navigation)
        # self.detailSings.config = ConfigDetailSings(self.detailSings)
        self.searchArea.config = ConfigSearchArea(self.searchArea)
        self.header.config = ConfigHeader(self.header)

        self.mainContent.config = ConfigMainContent(self.mainContent)
        self.detailSings.config = ConfigDetailSings(self.detailSings)
        self.indexNetEaseSings.config = ConfigNetEase(self.indexNetEaseSings)
        # self.indexXiamiSings.config = ConfigXia

        self.indexNetEaseSings.config.initThread()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 将Qt事件循环写到asyncio事件循环里。
    # QEventLoop不是Qt原生事件循环，
    # 是被asyncio重写的事件循环。
    # eventLoop = QEventLoop(app)
    # asyncio.set_event_loop(eventLoop)

    main_window = mainWindow()
    main_window.show()
    sys.exit(app.exec_())
