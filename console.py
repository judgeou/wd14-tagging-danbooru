from PIL import Image, ImageGrab
import clipboard
import app_cpu

# 排除不需要的tag，从 exclude.txt 读取需要排除的tag
def excludeTags (str):
    f = open('exclude.txt', 'r')
    for line in f.readlines():
        str = str.replace(line.strip(), '')
    f.close()
    return str

def replaceTags (str):
    f = open('replace.txt', 'r')
    for line in f.readlines():
        pair = line.split()
        str = str.replace(pair[0], pair[1])
    f.close()
    return str

def is_pil_image(obj):
    return isinstance(obj, Image.Image)

while True:
    clipboard_image = ImageGrab.grabclipboard()
    if clipboard_image is None:
        print("Not Image")
    else:
        if is_pil_image(clipboard_image):
            image = clipboard_image
        elif len(clipboard_image) == 1:
            image = Image.open(clipboard_image[0])
        result = app_cpu.image_to_wd14_tags(image, 'wd-eva02-large-tagger-v3', 0.35, True, True, False, True)
        result = excludeTags(result)
        result = replaceTags(result)
        print(result)
        clipboard.copy(result)
    input('wait your image')