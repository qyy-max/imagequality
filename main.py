from kivy.app import App
from kivy.uix.label import Label

class Test(App):
    def build(self):
        return Label(text="OK")

Test().run()
