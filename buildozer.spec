[app]
title = ImageQuality
package.name = imagequality
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf

version = 0.1

requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, CAMERA, READ_MEDIA_IMAGES, READ_EXTERNAL_STORAGE

android.api = 33
android.minapi = 24
android.ndk = 25b

android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = v2024.01.21
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
