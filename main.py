from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.core.text import LabelBase

from PIL import Image, ImageStat, ImageFilter, ImageChops
import os

# ================= 字体 =================
def register_chinese_font():
    font_file = "NotoSansSC-Regular.ttf"
    if os.path.exists(font_file):
        LabelBase.register(name='ChineseFont', fn_regular=font_file)
        return 'ChineseFont'
    return None

FONT_NAME = register_chinese_font()


# ================= 图像分析 =================
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
        diff = ImageChops.difference(gray, blur)

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


# ================= UI =================
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


# ================= APP =================
class AppMain(App):

    def build(self):
        Window.clearcolor = (0.95, 0.95, 0.97, 1)

        root = Styled(orientation='vertical', padding=15, spacing=10)

        self.label = Label(text="选择图片进行分析", font_name=FONT_NAME)
        root.add_widget(self.label)

        btn = Button(text="选择图片", size_hint=(1, 0.1))
        btn.bind(on_press=self.pick)
        root.add_widget(btn)

        self.img = KivyImage()
        root.add_widget(self.img)

        self.result = Label(text="")
        root.add_widget(self.result)

        self.gray = None
        self.path = None

        return root

    # ================= Android 原生选图（SAF） =================
    def pick(self, *args):
        try:
            from android import activity
            from jnius import autoclass

            Intent = autoclass('android.content.Intent')

            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")

            activity.bind(on_activity_result=self._on_activity_result)
            activity.startActivityForResult(intent, 1)

        except Exception as e:
            self.result.text = f"选图失败: {str(e)}"

    def _on_activity_result(self, requestCode, resultCode, data):
        try:
            if resultCode != -1 or data is None:
                return

            uri = data.getData()
            path = str(uri)

            self.load_image_fallback(path)

        except Exception as e:
            self.result.text = f"回调错误: {str(e)}"

    # ================= 安全加载 =================
    def load_image_fallback(self, path):
        try:
            img, gray, size = ImageQualityAnalyzer.load_image(path)

            tmp = os.path.join(self.user_data_dir, "tmp.jpg")
            img.save(tmp)

            self.img.source = tmp
            self.img.reload()

            self.gray = gray
            self.result.text = "已加载，分析中..."

            Clock.schedule_once(self.run, 0.2)

        except Exception as e:
            self.result.text = f"图片加载失败: {str(e)}"

    def run(self, dt):
        if self.gray is None:
            return

        r = ImageQualityAnalyzer.evaluate(self.gray)

        self.result.text = (
            f"总分: {r['total']}\n"
            f"清晰度: {r['sharp']:.2f}\n"
            f"曝光: {r['exp']:.2f}\n"
            f"噪声: {r['noise']:.2f}\n"
            f"均值亮度: {r['mean']:.1f}"
        )


# ================= RUN =================
if __name__ == '__main__':
    AppMain().run()
