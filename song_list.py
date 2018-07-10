"""
获取歌单
"""
import os
import addition
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from widget import DetailSings, makeMd5
from widget import ScrollArea
from queue import Queue
from api_v1 import netease
import network
import pprint
transTime = addition.itv2time

class ConfigMainContent(QObject):

    def __init__(self, mainContent):
        super(ConfigMainContent, self).__init__()
        self.mainContent = mainContent


class SingsFrameBase(ScrollArea):
    """全部歌单。"""

    def __init__(self, parent=None):
        super(SingsFrameBase, self).__init__()
        self.parent = parent
        self.transTime = addition.itv2time

        self.setObjectName("allSingsArea")
        # 为什么有的需要加utf-8呢，因为有中文。
        with open('QSS/sings_frame_base.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())
        
        # 主布局。
        self.mainLayout = QGridLayout(self.frame)
        self.mainLayout.setSpacing(0)
        self.mainLayout.setHorizontalSpacing(10)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)


# 一个Tab，网易云的全部歌单。
class NetEaseSingsArea(SingsFrameBase):
    """全部歌单。"""

    def __init__(self, parent=None):
        super(NetEaseSingsArea, self).__init__(parent)


class XiamiSingsArea(SingsFrameBase):

    def __init__(self, parent=None):
        super(XiamiSingsArea, self).__init__(parent)


class QQSingsArea(SingsFrameBase):

    def __init__(self, parent=None):
        super(QQSingsArea, self).__init__(parent)


# 一个有信号槽机制的安全线程队列。
class QueueObject(QObject):
    add = pyqtSignal()

    def __init__(self):
        super(QueueObject, self).__init__()
        self.queue = Queue()

    def put(self, data):
        self.queue.put(data)
        self.add.emit()

    def get(self):
        if self.queue.empty():
            return 0

        return self.queue.get()


# ---下面是线程，包括网络线程和时钟线程。
class RequestThread(QThread):
    # 该信号用于在线程执行时发出，通知主线程做些界面更新。
    # 因为在其他线程修改主界面是非常危险的事情。
    breakSignal = pyqtSignal(str)

    """异步请求，类似Pyhton封装的Thread形式，用QThread在简单封装一下。"""
    def __init__(self, parent=None, target=None, finishedConnection=None, *args, **kwargs):
        super(RequestThread, self).__init__()

        self.parent = parent
        self.args = args
        self.kwargs = kwargs
        self.target = target
        self.flag = False
        self.result = None
        if finishedConnection:
            self.finished.connect(finishedConnection)

    def run(self):
        self.result = self.target(*self.args, **self.kwargs)

    def setTarget(self, target=None):
        """方便多次调用。"""
        self.target = target

    def setArgs(self, *args, **kwargs):
        """方便多次调用。"""
        self.args = args
        self.kwargs = kwargs

    def setFlag(self, flag):
        self.flag = flag


class ConfigNetEase(QObject):

    def __init__(self, parent=None):
        super(ConfigNetEase, self).__init__()
        self.netEase = parent
        self.netEaseParent = self.netEase.parent
        
        # window - > detailSings.
        self.detailFrame = self.netEaseParent.parent.detailSings
        self.mainContents = self.netEaseParent.parent

        # ThreadPool方式。
        # 线程池方法说明:
        # PyQt的线程池由此创建，最好指定下最大连接数。
        # QThreadPool需要一个QRunnable对象作为目标。
        # 如下所创建的_PicThreadTask，需要重写run函数。
        # 然后在需要使用时创建:
        # task = _PicThreadTask
        # 并交由QThreadPool开始，self.picThreadPool(task)
        # 循环就可以。
        # 由于QRunnable不是由QObject继承来的，所以无法享受到信号槽机制。
        # 而PyQt中跨线程最好是不要进行界面操作。否则会有非常多意想不到的后果。
        self.picThreadPool = QThreadPool()
        self.picThreadPool.setMaxThreadCount(5)

        # QueueObject定义在base中，是一个由Queue与QObject组成的对象。
        # 一方面Queue线程安全，另一方面QObject带有信号槽机制。
        # 那只要QRunnable线程中请求完了内容，将内容添加到QueueObject中，
        # 由QueueObject发出信号通知主线程进行界面操作就可以安全的完成。
        # 这里是图片的操作。
        self.queue = QueueObject()
        self.queue.add.connect(self._setStyleCodesByThreadPool)

        # 连接滑轮到底的信号槽。
        # 同时连接图片下载的线程全部完成的信号槽。
        # 若一轮图片下载完成并且滑到底部则进行下一次线程，否则将不会。
        self.netEase.scrollDown.connect(self.sliderDownEvent)
        # self.picManager.allFinished.connect(self.picManagerFinishedEvent)

        # 用于存储结果。
        self.result = []

        # 歌单请求后的内容和缓存。
        self.reqResult = None
        self.cache = None
        self.singsUrls = None
        self.picName = None

        # 歌单的索引。
        self.singsFrames = []

        # 歌单显示名的url。
        self.singPicUrls = []

        # 歌单名称。
        self.singNames = []

        # 歌单id。
        self.playlistIds = []

        # 歌曲ids。
        self.singsIds = []

        # 一个是否滑到底部的flag。
        self.sliderDown = False

        # 布局用row。
        self.gridRow = 0

        # 布局用column。
        self.gridColumn = 0

        self.offset = 0
        # 用于不足时的补足。
        self.offsetComplement = 30

        self.myHeight = 0

        self.api = netease

        # self.initThread()

    def initThread(self):
        # 一个线程，初始化用于请求歌单的全部内容。
        self.netThread = RequestThread(self, self.getSings)
        self.netThread.finished.connect(self.threadSetSings)

        self.netThread.setFlag(True)
        self.netThread.start()

        self.singsThread = RequestThread(self)
        self.singsThread.setTarget(self.requestsDetail)
        self.singsThread.finished.connect(self.setRequestsDetail)

    def getSings(self):
        """请求一波歌单，一次30个。设置offset会设置请求量。"""
        result = self.api.recommend_playlist(offset=self.offset)
        if not result:
            return
        # print("result:\n", result)
        for i in result:
            self.result.append(i)
            self.singNames.append(i['name'])
            self.singPicUrls.append(i['coverImgUrl'])
            self.playlistIds.append(i['id'])

    """测试线程池方法。"""
    def threadSetSings(self):
        if not self.result:
            return
        length = len(self.singPicUrls)

        for i in range(30):
            i += self.offset
            # 根本原因是不足30个。
            if i >= length:
                self.offsetComplement = length % 30
                break

            picName = makeMd5(self.singPicUrls[i])
            # print('picName:\n', picName, '\n')
            # print('pppp:\n', self.singPicUrls[i], '\n\n')
            frame = OneSing(self.gridRow, self.gridColumn, self.playlistIds[i], self, picName)
            frame.clicked.connect(self.startRequest)
            frame.nameLabel.setText(self.singNames[i])

            self.netEase.mainLayout.addWidget(frame, self.gridRow, self.gridColumn)
            # 建立起索引，一是防止垃圾回收了，二是可以找到他的地址。
            self.singsFrames.append(frame)

            # 用于布局，一行4个。
            if self.gridColumn == 3:
                self.gridColumn = 0
                self.gridRow += 1
            else:
                self.gridColumn += 1

            try:
                cacheList = os.listdir('cache')
            except:
                os.mkdir('cache')
                cacheList = os.listdir('cache')

            url = self.singPicUrls[i]

            # names = str(url[url.rfind('/')+1:])
            names = makeMd5(url)
            if names in cacheList:
                frame.setStyleSheets("QLabel#picLabel{border-image: url(cache/%s)}"%(names))
            else:
                task = _PicThreadTask(self.queue, frame, url)
                self.picThreadPool.start(task)
        else:
            # 如果顺利进行会将offsetComplement变成原30。
            self.offsetComplement = 30

    def _setStyleCodesByThreadPool(self):
        # data是线程池的请求完成后的对象。
        # 0下标处是widget，1是style代码。
        data = self.queue.get()
        if not data:
            return
        else:
            data[0].setStyleSheets(data[1])

    def startRequest(self, ids, picName):
        self.picName = picName
        self.singsThread.setArgs(ids)
        self.singsThread.start()

    def requestsDetail(self, ids):
        reqResult = self.api.get_playlist_songs(ids)
        self.reqResult = reqResult
        # pprint.pprint(reqResult)
        # 网易云此处不再返回歌曲地址，由之后播放时单独获取。
        self.singsIds = [i['id'] for i in reqResult['tracks']]

        self.singsUrls = [netease.get_song_url(i['id']) for i in reqResult['tracks']]

    def setRequestsDetail(self):
        result = self.reqResult

        self.detailFrame.config.setupDetailFrames(result, self.singsUrls, self.singsIds)
        self.detailFrame.picLabel.setSrc('cache/{0}'.format(self.picName))
        self.detailFrame.picLabel.setStyleSheet('''QLabel {padding: 10px;}''')

        # 隐藏原来的区域，显示现在的区域。
        self.mainContents.mainContents.setCurrentIndex(1)

    # 事件。
    def sliderDownEvent(self):
        """滑轮到底的事件。"""
        if self.netEase.isHidden() == False:
            # toDo, 多个
            self.offset += self.offsetComplement
            # 判断是否在工作，免得多次start。
            if self.netThread.isRunning():
                return
            else:
                self.netThread.start()


class _PicThreadTask(QRunnable):
    # finished = pyqtSignal(QFrame, str)
    def __init__(self, queue, widget=None, url=None):
        super(_PicThreadTask, self).__init__()
        self.queue = queue
        self.widget = widget
        self.url = url

    def run(self):
        names = makeMd5(self.url)
        content = network.Requests.get(self.url).content
        pic = QPixmap()
        pic.loadFromData(content)
        # 缩小到合适的大小会让QT合理的利用内存资源。
        pic = pic.scaled(180, 180)
        a = pic.save("cache/{0}".format(names), 'jpg')
        self.queue.put([self.widget, "QLabel#picLabel{border-image: url(cache/%s)}"%(names)])
		

class OneSing(QFrame):
    # 大量创建，这样可以省内存。
    # 保证不可以动态添加对象
    __solts__ = ('parent', 'ggparent', 'detailFrame', 'row', 'column', 'ids',
     'picName', 'picLabel', 'nameLabel',
     'mainLayout',
     'mousePos',
     'result','catch',
     'singsIds', 'singsUrls')

    clicked = pyqtSignal(str, str)

    def __init__(self, row, column, ids=None, parent=None, picName=None):
        super(OneSing, self).__init__()

        self.setObjectName('oneSing')
        # 自己的位置信息。
        self.row = row
        self.column = column
        # 歌单号。
        self.ids = str(ids)
        # 大图的缓存名。
        self.picName = picName

        self.setMinimumSize(180, 235)

        self.picLabel = QLabel()
        self.picLabel.setObjectName('picLabel')
        self.picLabel.setMinimumSize(180, 180)
        self.picLabel.setMaximumSize(180, 180)

        self.nameLabel = QLabel()
        self.nameLabel.setMaximumWidth(180)
        self.nameLabel.setWordWrap(True)

        self.mainLayout = QVBoxLayout(self)

        self.mainLayout.addWidget(self.picLabel)
        self.mainLayout.addWidget(self.nameLabel)

    # 功能。
    def setStyleSheets(self, styleSheet=None):
        if styleSheet:
            self.setStyleSheet(styleSheet)

    # 事件。
    def mousePressEvent(self, event):
        # 记录下当前鼠标的位置。
        self.mousePos = QCursor.pos()

    def mouseReleaseEvent(self, event):
        # 先进行判断，防止误点将鼠标移开后还是会判断为已经点击的尴尬。
        if QCursor.pos() != self.mousePos:
            return
        else:
            self.clicked.emit(self.ids, self.picName)
