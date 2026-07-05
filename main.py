from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.core.text import LabelBase
from plyer import filechooser

from PIL import Image, ImageStat, ImageFilter
import os
import sys

# ------------------- 字体 -------------------
def register_chinese_font():
    font_file = "NotoSansSC-Regular.ttf"
    if os.path.exists(font_file):
        LabelBase.register(name='ChineseFont', fn_regular=font_file)
        return 'ChineseFont'
    return None

FONT_NAME = register_chinese_font()

# ------------------- 图像分析（PIL版） -------------------
class ImageQualityAnalyzer:

    @staticmethod
    def load_image(filepath, max_size=1200):
        img = Image.open(filepath).convert("RGB")
        w, h = img.size

        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)))

        gray = img.convert("L")
        return img, gray, (w, h)

    @staticmethod
    def sharpness(gray):
        # Laplacian近似：用边缘方差代替
        edge = gray.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edge)
        return stat.var[0]

    @staticmethod
    def exposure(gray):
        hist = gray.histogram()
        total = sum(hist)

        over = sum(hist[240:])
        under = sum(hist[:15])

        over_r = over / total
        under_r = under / total

        mean = ImageStat.Stat(gray).mean[0]

        base = 1.0 - (over_r + under_r)
        bonus = 0.1 if 70 < mean < 180 else 0

        score = max(0, min(1, base + bonus))
        return score, over_r, under_r, mean

    @staticmethod
    def noise(gray):
        blur = gray.filter(ImageFilter.MedianFilter(size=3))
        diff = ImageChops_difference(gray, blur)

        stat = ImageStat.Stat(diff)
        var = stat.var[0] / 255.0

        score = max(0.1, 1.0 - var * 1.2)
        return score, var

    @staticmethod
    def overall(sharp, exp, noise):
        return int(max(0, min(100, 100 * (0.4*sharp + 0.3*exp + 0.3*noise))))

    @staticmethod
    def evaluate(gray):
        noise_score, noise_var = ImageQualityAnalyzer.noise(gray)
        sharp_raw = ImageQualityAnalyzer.sharpness(gray)
        sharp_norm = min(1.0, sharp_raw / 2000.0) * (0.7 + 0.3 * noise_score)

        exp_score, over_r, under_r, mean = ImageQualityAnalyzer.exposure(gray)

        total = ImageQualityAnalyzer.overall(sharp_norm, exp_score, noise_score)

        return {
            "total": total,
            "sharp": sharp_norm,
            "exp": exp_score,
            "noise": noise_score,
            "over": over_r,
            "under": under_r,
            "mean": mean,
            "noise_var": noise_var
        }


# PIL差分函数（替代numpy）
from PIL import ImageChops
def ImageChops_difference(img1, img2):
    return ImageChops.difference(img1, img2)


# ------------------- UI -------------------
class Styled(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.95, 0.95, 0.97, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self.update, pos=self.update)

    def update(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos


class AppMain(App):

    def build(self):
        Window.size = (900, 700)

        root = Styled(orientation='vertical', padding=15, spacing=10)

        self.label = Label(text="选择图片", font_name=FONT_NAME)
        root.add_widget(self.label)

        btn = Button(text="选择图片", size_hint=(1, 0.1))
        btn.bind(on_press=self.pick)
        root.add_widget(btn)

        self.img = KivyImage()
        root.add_widget(self.img)

        self.result = Label(text="")
        root.add_widget(self.result)

        self.path = None
        return root

    def pick(self, *args):
        filechooser.open_file(on_selection=self.selected)

    def selected(self, files):
        if not files:
            return

        self.path = files[0]

        img, gray, size = ImageQualityAnalyzer.load_image(self.path)

        tmp = os.path.join(self.user_data_dir, "tmp.jpg")
        img.save(tmp)

        self.img.source = tmp
        self.img.reload()

        self.gray = gray
        self.result.text = "已加载"

        Clock.schedule_once(self.run, 0.1)

    def run(self, dt):
        r = ImageQualityAnalyzer.evaluate(self.gray)

        self.result.text = f"""
总分: {r['total']}
清晰度: {r['sharp']:.2f}
曝光: {r['exp']:.2f}
噪声: {r['noise']:.2f}
均值亮度: {r['mean']:.1f}
"""


if __name__ == '__main__':
    AppMain().run()
