from PyQt5.QtWidgets import QPushButton, QFrame, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QScrollArea, QScrollBar, QWidget, QMenu
from PyQt5.QtMultimedia import QMediaContent, QMediaMetaData
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.Qt import QCursor
from random import randint
from play_mode import PlayMode
import utils
import enum


'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''


class PlayList(QFrame):
    '''
    播放列表
    '''

    sig_music_index_changed = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_widget = parent
        self.setObjectName('PlayList')
        self.set_UI()

        '''播放列表，元素类型是QUrl'''
        self.music_list = []
        '''列表条目，元素类型是ListEntry'''
        self.entries = []
        '''歌词，元素类型是str'''
        self.lyrics = []
        
        self.music_count = 0
        self.play_mode = PlayMode.RANDOM

        self.last_play = None
        self.music_index = None

        self.set_connections()
    

    def set_UI(self):
        self.setFrameShape(QFrame.Box)
        self.title = PlayListTitle(self)
        self.table = PlayListTable(self)

        '''
        在构造函数没有结束前
        geometry()的返回值是错误的
        不能在这个函数里面setGeometry()
        '''

        self.set_layout()
        with open('.\\QSS\\play_list.qss', 'r') as file_obj:
            self.setStyleSheet(file_obj.read())
        self.hide()   


    def set_layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.table, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setLayout(self.layout)


    def set_connections(self):
        self.title.close_button.clicked.connect(self.hide)
        '''
        由于ListEntry是动态创建、销毁的
        信号和槽的连接不放在这个函数中
        放在了on_music_added函数中
        '''


    def set_play_mode(self, mode):
        '''切换播放模式'''
        if mode in PlayMode:
            self.play_mode = mode


    def add_music(self, music_info, play=False):
        '''
        向播放列表添加歌曲
        music_info类型是字典
        music_info['url']
        music_info['name']
        music_info['time']
        music_info['author']
        music_info['music_img']
        play标识是否立即播放
        '''
        url = music_info['url']
        flag = False
        duplicate = False

        if isinstance(url, QUrl):
            if url not in self.music_list:
                flag = True
            else:
                duplicate = True

        elif isinstance(url, str):
            '''
            如果是本地文件的路径，要写fromLocalFile
            否则直接用QUrl(song)无法正常播放
            '''
            if 'http' in url or 'https' in url or 'file' in url:
                url = QUrl(url)
            else:
                url = QUrl.fromLocalFile(url)
            if url not in self.music_list:
                flag = True
            else:
                duplicate = True

        if flag:
            self.music_count += 1
            self.music_list.append(url)

            entry, index = self.create_entry(music_info)
            self.entries.append(entry)
            self.table.insert_entry(entry, index)

            lyric = utils.convert_lyric(music_info['lyric'])
            self.lyrics.append(lyric)

            if play:
                self.music_index = self.music_count - 1
                self.sig_music_index_changed.emit()
        
        if play and duplicate:
            self.music_index = self.music_list.index(url)
            self.sig_music_index_changed.emit()


    def get_music(self):
        '''
        得到当前播放的歌
        如果music_index为None，根据播放方式选择一个值
        如果播放列表为空，返回None
        '''
        if self.music_list:
            if self.music_index == None:
                if self.play_mode == PlayMode.RANDOM:
                    self.music_index = randint(0, self.music_count - 1)
                else:
                    self.music_index = 0
            song_url = self.music_list[self.music_index]
            return QMediaContent(song_url)
        return None


    def previous_music(self):
        '''切换到上一首歌'''
        if self.music_list and self.music_index != None:
            if self.play_mode == PlayMode.RANDOM:
                next_index = randint(0, self.music_count - 1)
                if next_index == self.music_index:
                    next_index += 1
                    next_index %= self.music_count

            elif self.play_mode == PlayMode.LOOP:
                next_index  = self.music_index - 1
                if next_index < 0:
                    next_index = self.music_count - 1

            elif self.play_mode == PlayMode.REPEAT:
                next_index = self.music_index

            self.music_index = next_index
            song_url = self.music_list[self.music_index]
            return QMediaContent(song_url)
        return None

    
    def next_music(self):
        '''切换到下一首歌'''
        if self.music_list and self.music_index != None:
            if self.play_mode == PlayMode.RANDOM:
                next_index = randint(0, self.music_count - 1)
                if next_index == self.music_index:
                    next_index += 1
                    next_index %= self.music_count

            elif self.play_mode == PlayMode.LOOP:
                next_index = self.music_index + 1
                if next_index >= self.music_count:
                    next_index = 0

            elif self.play_mode == PlayMode.REPEAT:
                next_index = self.music_index

            self.music_index = next_index
            song_url = self.music_list[self.music_index]
            return QMediaContent(song_url)
        return None


    def create_entry(self, music_info):
        '''把创建entry、连接信号和槽封装'''
        entry = ListEntry(self.table.contents, music_info)
        entry.sig_double_clicked.connect(self.on_double_clicked)
        entry.sig_delete.connect(self.on_entry_deleted, Qt.QueuedConnection)
        return (entry, self.music_count - 1)


    def get_lyric_and_title(self):
        if self.music_index == None:
            return None
        
        lyric = self.lyrics[self.music_index]
        title = self.entries[self.music_index].get_music_title()
        return (lyric, title)


    def on_double_clicked(self, entry):
        '''
        播放列表entry项被双击
        处理ListEntry的sig_double_clicked信号
        '''
        try:
            index = self.entries.index(entry)
        except:
            index = None

        if index != None:
            self.music_index = index
            '''使播放器切换歌曲'''
            self.sig_music_index_changed.emit()


    def on_entry_deleted(self, entry):
        try:
            index = self.entries.index(entry)
        except:
            index = None

        if index != None:
            del self.music_list[index]
            self.table.layout.removeWidget(entry)
            del self.entries[index]
            entry.deleteLater()
            del self.lyrics[index]
            self.music_count -= 1

    
    def on_music_status_changed(self, is_paused):
        '''
        当歌曲播放状态改变（切歌、播放、暂停）时
        调整播放列表中的图片
        '''
        if self.last_play != None and self.last_play in self.entries:
            self.last_play.set_status_label(LabelImage.EMPTY)

        if self.music_index != None:
            self.last_play = self.entries[self.music_index]
            if self.music_index >= 0 and self.music_index < self.music_count:
                if is_paused:
                    self.entries[self.music_index].set_status_label(LabelImage.PAUSE)
                else:
                    self.entries[self.music_index].set_status_label(LabelImage.PLAY)
                    self.table.ensureWidgetVisible(self.entries[self.music_index], 0, 300)


'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''


class PlayListTitle(QFrame):
    '''播放列表的标题'''

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('PlayListTitle')
        self.set_UI()


    def set_UI(self):
        self.setFrameShape(QFrame.NoFrame)

        self.close_button = QPushButton(self)
        self.close_button.setObjectName('CloseButton')
        self.close_button.setToolTip('关闭')

        self.title_label = XLabel(self)
        self.title_label.setObjectName('TitleLabel')
        self.title_label.set_text('播放列表')

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(5, 13, 5, 13)
        self.layout.addWidget(self.title_label)
        self.layout.addStretch(1)
        self.layout.addWidget(self.close_button)
        self.setLayout(self.layout)
        '''设置对齐方式：垂直居中'''
        self.layout.setAlignment(self.title_label, Qt.AlignVCenter)
        self.layout.setAlignment(self.close_button, Qt.AlignVCenter)

        with open('.\\QSS\\play_list_title.qss', 'r') as file_obj:
            self.setStyleSheet(file_obj.read())
        

'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''


class PlayListTable(QScrollArea):
    '''播放列表主体'''
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('PlayListTable')
        self.set_UI()

        
    def set_UI(self):
        self.setFrameShape(QFrame.NoFrame)

        '''
        QScrollArea只能设置一个widget
        因此要在这一个widget上添加其他widget
        '''
        self.contents = QFrame(self)
        self.contents.setObjectName('Contents')
        self.contents.setFrameShape(QFrame.NoFrame)
        '''这个layout是给contents的'''
        self.set_layout()

        '''设置滚动条'''
        self.scroll_bar = QScrollBar(self)
        self.setVerticalScrollBar(self.scroll_bar)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setWidgetResizable(True)
        self.setWidget(self.contents)

        with open('.\\QSS\\play_list_table.qss', 'r') as file_obj:
            self.setStyleSheet(file_obj.read())

    
    def set_layout(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.addStretch(1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.contents.setLayout(self.layout)


    def insert_entry(self, entry, index):
        self.layout.insertWidget(index, entry)


'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''


@enum.unique
class LabelImage(enum.Enum):
    '''标签图像'''
    EMPTY = 0
    PLAY = 1
    PAUSE = 2


'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''


class ListEntry(QFrame):
    '''
    播放列表中的条目
    '''

    sig_double_clicked = pyqtSignal(QFrame)
    sig_delete = pyqtSignal(QFrame)

    def __init__(self, parent, music_info):
        '''
        music_info['url']  music_info['name']  music_info['time']
        music_info['author']  music_info['music_img']
        '''

        super().__init__(parent)
        self.setObjectName('ListEntry')

        self.music_title = music_info['name']
        self.music_artist = music_info['author']
        self.music_duration = music_info['time']
        self.music_image = music_info['music_img']

        self.set_UI()


    def set_UI(self):
        self.setFrameShape(QFrame.NoFrame)

        self.context_menu = XContextMenu(self)
        self.context_menu.delete_button.triggered.connect(self.on_deleted)
        self.context_menu.hide()
        
        self.set_labels()
        self.set_layout()

        with open('.\\QSS\\list_entry.qss', 'r') as file_obj:
            self.setStyleSheet(file_obj.read())


    def set_labels(self):
        self.status_label = XLabel(self)
        self.status_label.setObjectName('StatusLabel')
        
        self.song_label = XLabel(self)
        self.song_label.setObjectName('SongLabel')
        self.song_label.set_text(self.music_title)
        # self.song_label.setText(self.music_title)

        self.artist_label = XLabel(self)
        self.artist_label.setObjectName('ArtistLabel')
        self.artist_label.set_text(self.music_artist)
        # self.artist_label.setText(self.music_artist)

        self.duration_label = XLabel(self)
        self.duration_label.setObjectName('DurationLabel')
        self.duration_label.set_text(self.music_duration)
        # self.duration_label.setText(self.music_duration)


    def set_layout(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.layout.addWidget(self.status_label)
        self.layout.addSpacing(5)
        self.layout.addWidget(self.song_label, 42)
        self.layout.addSpacing(5)
        self.layout.addWidget(self.artist_label, 17)
        self.layout.addSpacing(5)
        self.layout.addWidget(self.duration_label, 8)
        self.setLayout(self.layout)


    def mouseDoubleClickEvent(self, event):
        # print(self.index)
        if event.button() == Qt.LeftButton:
            self.sig_double_clicked.emit(self)


    def contextMenuEvent(self, event):
        self.context_menu.move(QCursor.pos())
        self.context_menu.show()


    def set_status_label(self, image):
        if image == LabelImage.EMPTY:
            pixmap = QPixmap()
        elif image == LabelImage.PLAY:
            pixmap = QPixmap('.\\images\\play_2.png')
        elif image == LabelImage.PAUSE:
            pixmap = QPixmap('.\\images\\pause_2.png')

        self.status_label.setScaledContents(True)
        self.status_label.setPixmap(pixmap)
        self.status_label.setAlignment(Qt.AlignCenter)


    def get_music_title(self):
        return self.music_title


    def on_deleted(self):
        self.sig_delete.emit(self)


'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''

class XLabel(QLabel):
    '''
    自定义标签
    自动调整字符串的显示
    '''

    def __init__(self, parent):
        super().__init__(parent)
        self.text = None

        '''设置字体'''
        font = QFont('YouYuan')
        self.setFont(font)


    def set_text(self, text):
        self.text = text
        self.setToolTip(self.text)


    def resizeEvent(self, event):
        '''调整显示长度'''
        text_to_show = self.fontMetrics().elidedText(self.text,\
            Qt.ElideRight, event.size().width())
        self.setText(text_to_show)


'''-------------------------------------------------------------------------'''
'''-------------------------------------------------------------------------'''

class XContextMenu(QMenu):
    '''右键菜单'''

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('XContextMenu')

        self.set_UI()
        self.set_connections()


    def set_UI(self):
        self.setFont(QFont('YouYuan'))
        self.delete_button = self.addAction('从列表中删除歌曲')


    def set_connections(self):
        pass