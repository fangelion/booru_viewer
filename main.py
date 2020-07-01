from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import sys
import utils
import threading
from time import sleep
import logging

start_url = "https://danbooru.donmai.us/posts"
cur_num = 0
cur_page = 1
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
queue = []
tpool = []
idxpool = []
lock = threading.Lock()
mlock = threading.Lock()


class Manager(threading.Thread):
    def __init__(self):
        super(Manager, self).__init__()
        self.wrk = True
        self.max = 10
        self.localtpool = []

    def run(self):
        global mlock
        while self.wrk:
            with mlock:
                for i, fx in enumerate(tpool):
                    if len(self.localtpool) < self.max:
                        self.localtpool.append(fx)
                        tpool.pop(i)
                        idxpool.pop(idxpool.index(fx.idx))
                        logging.info('added to download')
                    else:
                        break
            for i, fx in enumerate(self.localtpool):
                if not fx.started:
                    fx.start()
                if not fx.is_alive():
                    self.localtpool.pop(i)
                    try:
                        k = len(tpool)
                    except Exception as error:
                        k = "err"
                    logging.info(f'removed deadthread. Left {k} elements')
            sleep(1)

    def exit(self):
        self.wrk = False
        for i in self.localtpool:
            i.join()


class Download(threading.Thread):
    def __init__(self, idx):
        super(Download, self).__init__()
        self.started = False
        self.idx = idx

    def run(self):
        global lock
        self.started = True
        data = utils.get_page(queue[self.idx]["img_url"])
        with lock:
            queue[self.idx]["img_orig"] = data


class Thread(threading.Thread):
    def __init__(self):
        super(Thread, self).__init__()
        self.manager = Manager()
        self.manager.start()
        self.names = {}
        self.cur_page = 1
        self.cur_num = 0
        self.exit_flag = False
        self.add_pics(count=1)
        self.check_cache()

    def add_pics(self, count=1):
        supported_ext = ['png', 'jpg', 'jpeg']
        for i in range(count):
            tmp = utils.get_pages(start_url, params={'page': self.cur_page})
            for item in tmp:
                url = item['data-large-file-url']
                if item['data-file-ext'] not in supported_ext:
                    # print(f"File is not supported. | {item['data-file-ext']}")
                    continue
                pic_name = utils.get_name(url)
                if pic_name not in self.names.keys():
                    self.names[pic_name] = len(self.names)
                    queue.append({
                        "img_url": url,
                        # "img_orig": utils.get_page(url),
                        "img_orig": None,
                        "page": self.cur_page,
                        "num": self.names[pic_name],
                        "name": pic_name,
                        "tags": item['data-tags'],

                    })
            self.cur_page = self.cur_page + 1

    def check_cache(self):
        global mlock
        #logging.info(f'Curpage is {queue[self.cur_num]["page"]}')
        for idx in range(len(queue)):
            if (queue[self.cur_num]["num"] - queue[idx]["num"] > 10) or (queue[idx]["num"] - queue[self.cur_num]["num"] > 10):
                queue[idx]["img_orig"] = None
                # logging.info(f'img #{queue[idx]["num"]} set to None')
            elif queue[idx]["img_orig"] is None:
                #queue[idx]["img_orig"] = utils.get_page(queue[idx]["img_url"])
                #d = threading.Thread(target=download, args=(idx,))
                d = Download(idx)
                with mlock:
                    if idx not in idxpool:
                        tpool.append(d)
                        idxpool.append(idx)
                # logging.info(f'img #{queue[idx]["num"]} set to Loaded')

    def check_pic(self):
        if queue[self.cur_num]["img_orig"] is None:
            queue[self.cur_num]["img_orig"] = utils.get_page(queue[self.cur_num]["img_url"])

    def get_next(self):
        self.cur_num = self.cur_num + 1
        if self.cur_num >= len(queue):
            self.add_pics()
            self.check_cache()
        self.check_pic()
        return queue[self.cur_num]

    def get_prev(self):
        self.cur_num = self.cur_num - 1
        if self.cur_num < 0:
            self.cur_num = 0
        self.check_pic()
        return queue[self.cur_num]

    def get(self):
        return queue[self.cur_num]

    def run(self):
        sleep(2)
        self.add_pics(count=3)
        self.check_cache()
        while not self.exit_flag:
            if self.cur_num >= len(queue) - 20:
                self.add_pics(count=3)
                self.check_cache()
                logging.info("added some pics")
            self.check_cache()
            sleep(1)
        logging.info("thread closed")

    def exit(self):
        self.exit_flag = True
        self.manager.exit()


class MainWindow(QMainWindow):
    def __init__(self, base):
        super(MainWindow, self).__init__()

        self.wrk = base

        screen = QApplication.primaryScreen()
        self.screen_size = screen.size()

        self.resize(1000, 790)
        self.maximumSize()
        self.mainWidget = QWidget()

        itm = self.wrk.get()
        img_data = itm['img_orig']
        self.set_title(itm)

        self.big_pic = QLabel()
        h = self.height()
        self.img = QPixmap()
        self.wrk.check_pic()
        self.img.loadFromData(img_data)
        img_new = self.img.scaledToHeight(h)
        if img_new.width() > self.screen_size.width():
            img_new = self.img.scaledToHeight(self.screen_size.width())
        self.big_pic.setPixmap(img_new)

        self.setCentralWidget(self.big_pic)
        self.big_pic.setAlignment(Qt.AlignCenter)
        logging.info("started")

    def keyPressEvent(self, event):
        # print(event.key())
        if event.key() == Qt.Key_Right:
            self.next_pic()
        elif event.key() == Qt.Key_Left:
            self.prev_pic()
        elif (event.key() == Qt.Key_C) or (event.key() == 1057):
            self.copy_image()
        elif (event.key() == Qt.Key_N) or (event.key() == 1058):
            self.next_pic()
        elif (event.key() == Qt.Key_P) or (event.key() == 1047):
            self.prev_pic()
        elif (event.key() == Qt.Key_S) or (event.key() == 1067):
            self.save_image()
        event.accept()

    def resizeEvent(self, resizeEvent):
        img_new = self.resize_pic()
        self.big_pic.setPixmap(img_new)
        self.big_pic.setAlignment(Qt.AlignCenter)
        self.big_pic.update()
        resizeEvent.accept()

    def next_pic(self):
        itm = self.wrk.get_next()
        self.set_title(itm)
        img_data = itm['img_orig']
        self.img.loadFromData(img_data)
        img_new = self.resize_pic()
        self.big_pic.setPixmap(img_new)
        self.big_pic.update()

    def prev_pic(self):
        itm = self.wrk.get_prev()
        self.set_title(itm)
        img_data = itm['img_orig']
        self.img.loadFromData(img_data)
        img_new = self.resize_pic()
        self.big_pic.setPixmap(img_new)
        self.update()

    def copy_image(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.img)

    def save_image(self):
        itm = self.wrk.get()
        url = itm['img_url']
        data = itm['img_orig']
        utils.save(data, url)

    def set_title(self, itm):
        total = len(queue)
        wname = "|".join(["PicView",
                          " ".join(["Pic", str(itm["num"])]),
                          " ".join(["Page", str(itm["page"])]),
                          " ".join(["Total pic", str(total)]),
                          itm['name']
                          ])
        self.setWindowTitle(wname)

    def resize_pic(self):
        h = self.big_pic.height()
        img_new = self.img.scaledToHeight(h)
        if img_new.width() > self.big_pic.width():
            img_new = self.img.scaledToWidth(self.big_pic.width())
        elif img_new.width() > self.screen_size.width():
            img_new = self.img.scaledToWidth(self.screen_size.width())
        return img_new

    def closeEvent(self, event):
        self.wrk.exit()
        self.wrk.close()
        self.wrk.join()
        self.close()
        event.accept()


def main(base):
    app = QApplication(sys.argv)
    window = MainWindow(base)
    window.show()
    app.exit(app.exec_())


if __name__ == "__main__":
    base = Thread()
    main_thr = threading.Thread(target=main, args=(base,))
    main_thr.start()
    base.start()

    #кеш, метаданные, просмотр миниатюр, фильтр некоторых форматов.
    ee = {'id': 'post_3923158',
          'class': ['post-preview', 'post-status-has-children'],
          'data-id': '3923158',
          'data-has-sound': 'false',
          'data-tags': '1girl bangs bare_shoulders bathroom blush breasts breath brown_eyes brown_hair collarbone commentary_request downblouse dress dress_lift earrings eyebrows_visible_through_hair frilled_panties frills from_above full_body hair_ornament high_heels highres idolmaster idolmaster_cinderella_girls indoors jewelry knees_together_feet_apart koorimizu lifted_by_self long_hair looking_up nose_blush off_shoulder one_side_up open_mouth panties panty_pull peeing pink_dress pink_footwear pink_legwear shimamura_uzuki shiny shiny_hair sitting small_breasts socks solo star sweat tied_hair toilet toilet_use translation_request underwear white_panties',
          'data-pools': '',
          'data-rating': 'q',
          'data-width': '1200',
          'data-height': '1694',
          'data-flags': '',
          'data-has-children': 'true',
          'data-score': '2',
          'data-fav-count': '2',
          'data-pixiv-id': '80583401',
          'data-file-ext': 'png',
          'data-source': 'https://i.pximg.net/img-original/img/2020/04/05/17/20/07/80583401_p1.png',
          'data-uploader-id': '527891',
          'data-normalized-source': 'https://www.pixiv.net/artworks/80583401',
          'data-is-favorited': 'false', 'data-md5': '7f7d2e51b447f4322ed38dac931e36c6',
          'data-file-url': 'https://danbooru.donmai.us/data/7f7d2e51b447f4322ed38dac931e36c6.png',
          'data-large-file-url': 'https://danbooru.donmai.us/data/sample/sample-7f7d2e51b447f4322ed38dac931e36c6.jpg',
     'data-preview-file-url': 'https://cdn.donmai.us/preview/7f/7d/7f7d2e51b447f4322ed38dac931e36c6.jpg'}