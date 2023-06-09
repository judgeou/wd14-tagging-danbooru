from PIL import Image, ImageGrab
import clipboard
import app

# 排除不需要的tag，从 exclude.txt 读取需要排除的tag
def excludeTags (str):
    f = open('exclude.txt', 'r')
    for line in f.readlines():
        str = str.replace(line.strip(), '')
    f.close()
    return str

while True:
    clipboard_image = ImageGrab.grabclipboard()
    if clipboard_image is None:
        print("Not Image")
    else:
        result = app.image_to_wd14_tags(clipboard_image, 'wd14-convnext', 0.35, False, True, False, True)
        result = excludeTags(result)
        print(result)
        clipboard.copy(result)
    input('wait your image')