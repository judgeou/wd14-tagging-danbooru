import os
import re
from typing import Mapping, Tuple, Dict

import cv2
import gradio as gr
import numpy as np
import pandas as pd
import requests
from PIL import Image
from huggingface_hub import hf_hub_download
from onnxruntime import InferenceSession
import onnxruntime as rt
from urllib.request import urlopen
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# noinspection PyUnresolvedReferences
def make_square(img, target_size):
    old_size = img.shape[:2]
    desired_size = max(old_size)
    desired_size = max(desired_size, target_size)

    delta_w = desired_size - old_size[1]
    delta_h = desired_size - old_size[0]
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)

    color = [255, 255, 255]
    return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)


# noinspection PyUnresolvedReferences
def smart_resize(img, size):
    # Assumes the image has already gone through make_square
    if img.shape[0] > size:
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    elif img.shape[0] < size:
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)
    else:  # just do nothing
        pass

    return img


class WaifuDiffusionInterrogator:
    def __init__(
            self,
            repo='SmilingWolf/wd-v1-4-convnext-tagger-v2',
            model_path='model.onnx',
            tags_path='selected_tags.csv',
            mode: str = "auto"
    ) -> None:
        self.__repo = repo
        self.__model_path = model_path
        self.__tags_path = tags_path
        self._provider_mode = mode

        self.__initialized = False
        self._model, self._tags = None, None

    def _init(self) -> None:
        if self.__initialized:
            return

        model_path = hf_hub_download(self.__repo, filename=self.__model_path)
        tags_path = hf_hub_download(self.__repo, filename=self.__tags_path)

        providers = rt.get_available_providers()

        self._model = InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
        self._tags = pd.read_csv(tags_path)

        self.__initialized = True

    def _calculation(self, image: Image.Image) -> pd.DataFrame:
        self._init()

        # code for converting the image and running the model is taken from the link below
        # thanks, SmilingWolf!
        # https://huggingface.co/spaces/SmilingWolf/wd-v1-4-tags/blob/main/app.py

        # convert an image to fit the model
        _, height, _, _ = self._model.get_inputs()[0].shape

        # alpha to white
        image = image.convert('RGBA')
        new_image = Image.new('RGBA', image.size, 'WHITE')
        new_image.paste(image, mask=image)
        image = new_image.convert('RGB')
        image = np.asarray(image)

        # PIL RGB to OpenCV BGR
        image = image[:, :, ::-1]

        image = make_square(image, height)
        image = smart_resize(image, height)
        image = image.astype(np.float32)
        image = np.expand_dims(image, 0)

        # evaluate model
        input_name = self._model.get_inputs()[0].name
        label_name = self._model.get_outputs()[0].name
        confidence = self._model.run([label_name], {input_name: image})[0]

        full_tags = self._tags[['name', 'category']].copy()
        full_tags['confidence'] = confidence[0]

        return full_tags

    def interrogate(self, image: Image) -> Tuple[Dict[str, float], Dict[str, float]]:
        full_tags = self._calculation(image)

        # first 4 items are for rating (general, sensitive, questionable, explicit)
        ratings = dict(full_tags[full_tags['category'] == 9][['name', 'confidence']].values)

        # rest are regular tags
        tags = dict(full_tags[full_tags['category'] != 9][['name', 'confidence']].values)

        return ratings, tags


WAIFU_MODELS: Mapping[str, WaifuDiffusionInterrogator] = {
    'wd14-vit': WaifuDiffusionInterrogator(),
    'wd14-convnext': WaifuDiffusionInterrogator(
        repo='SmilingWolf/wd-v1-4-convnextv2-tagger-v2',
    ),
    'wd14-convnext-v3': WaifuDiffusionInterrogator(
        repo="SmilingWolf/wd-swinv2-tagger-v3"
    )
}
RE_SPECIAL = re.compile(r'([\\()])')

def image_to_wd14_tags(image: Image.Image, model_name: str, threshold: float,
                       use_spaces: bool, use_escape: bool, include_ranks: bool, score_descend: bool) \
        -> Tuple[Mapping[str, float], str, Mapping[str, float]]:
    model = WAIFU_MODELS[model_name]
    ratings, tags = model.interrogate(image)

    filtered_tags = {
        tag: score for tag, score in tags.items()
        if score >= threshold
    }

    text_items = []
    tags_pairs = filtered_tags.items()
    if score_descend:
        tags_pairs = sorted(tags_pairs, key=lambda x: (-x[1], x[0]))
    for tag, score in tags_pairs:
        tag_outformat = tag
        if use_spaces:
            tag_outformat = tag_outformat.replace('_', ' ')
        if use_escape:
            tag_outformat = re.sub(RE_SPECIAL, r'\\\1', tag_outformat)
        if include_ranks:
            tag_outformat = f"({tag_outformat}:{score:.3f})"
        text_items.append(tag_outformat)
    output_text = ', '.join(text_items)

    return output_text

def post_to_item_danbooru (post):
    img_url = post['large_file_url']
    tag_string_character = post['tag_string_character']
    tag_string_general = post['tag_string_general']
    tag_all = tag_string_character.split(' ') + tag_string_general.split(' ')
    tag_all_text = ', '.join(tag_all)
    response = urlopen(img_url)
    image_data = response.read()
    image_stream = BytesIO(image_data)
    image = Image.open(image_stream)
    
    return image, tag_all_text

def post_to_item_yande (post):
    img_url = post['sample_url']
    tag_all = post['tags']
    tag_all_text = ', '.join(tag_all.split(' '))
    response = urlopen(img_url)
    image_data = response.read()
    image_stream = BytesIO(image_data)
    image = Image.open(image_stream)
    
    return image, tag_all_text

def search_images_from_danbooru (tags: str, gr_limit_input: int):
    url = 'https://danbooru.donmai.us/posts.json'
    params = { 'tags': tags, 'limit': gr_limit_input }
    response = requests.get(url, params=params)
    data = response.json()
    image_urls = filter(lambda x: 'large_file_url' in x, data)
    with ThreadPoolExecutor(max_workers=8) as executor:
        images = list(executor.map(post_to_item_danbooru, image_urls))
    return images

def search_image_from_yande (tags: str, gr_limit_input: int):
    url = 'https://yande.re/post.json'
    params = { 'tags': tags, 'limit': gr_limit_input }
    response = requests.get(url, params=params)
    data = response.json()
    image_urls = filter(lambda x: 'sample_url' in x, data)
    with ThreadPoolExecutor(max_workers=8) as executor:
        images = list(executor.map(post_to_item_yande, image_urls))
    return images

def on_select_gallery (gallery, model_name: str, threshold: float,
                       use_spaces: bool, use_escape: bool, include_ranks: bool, score_descend: bool, evt: gr.SelectData):
    img_url = gallery[evt.index][0]['name']
    source_tags = gallery[evt.index][1]
    image = Image.open(img_url)

    return image_to_wd14_tags(image, model_name, threshold, use_spaces, use_escape, include_ranks, score_descend), source_tags

def on_click_img_url_interrogate (img_url: str, model_name: str, threshold: float,
                       use_spaces: bool, use_escape: bool, include_ranks: bool, score_descend: bool):
    response = urlopen(img_url)
    image_data = response.read()
    image_stream = BytesIO(image_data)
    image = Image.open(image_stream)

    return image_to_wd14_tags(image, model_name, threshold, use_spaces, use_escape, include_ranks, score_descend)

# if __name__ == '__main__':
#     with gr.Blocks() as demo:
#         with gr.Row():
#             with gr.Column():
#                 with gr.Row():
#                     gr_tags_input = gr.Textbox(label='danbooru tags', value='rating:Safe')
#                     gr_limit_input = gr.Number(label='limit', value=10)
#                 with gr.Row():
#                     btn_search_danbooru = gr.Button(value='Search from Danbooru', variant='primary')
#                     btn_search_yande = gr.Button(value='Search from Yande', variant='primary')
#                 with gr.Row():
#                     gallery = gr.Gallery(label='Gallery').style(
#                         full_width=False, columns=[4], rows=[3], object_fit="contain", height="auto", show_label=False)
#                 with gr.Row():
#                     gr_model = gr.Radio(list(WAIFU_MODELS.keys()), value='wd14-convnext', label='Waifu Model')
#                     gr_threshold = gr.Slider(0.0, 1.0, 0.35, label='Tagging Confidence Threshold')
#                 with gr.Row():
#                     gr_space = gr.Checkbox(value=False, label='Use Space Instead Of _')
#                     gr_escape = gr.Checkbox(value=True, label='Use Text Escape')
#                     gr_confidence = gr.Checkbox(value=False, label='Keep Confidences')
#                     gr_order = gr.Checkbox(value=True, label='Descend By Confidence')

#             with gr.Column():
#                 gr_output_source_tags = gr.TextArea(label='source tags')
#                 gr_output_text = gr.TextArea(label='interrogate tags')
#                 gr_img_url = gr.Textbox(label='image url')
#                 btn_gr_img_interrogate = gr.Button(value='Interrogate', variant='primary')

#         btn_search_danbooru.click(fn=search_images_from_danbooru, inputs=[gr_tags_input, gr_limit_input], outputs=[gallery])
#         btn_search_yande.click(fn=search_image_from_yande, inputs=[gr_tags_input, gr_limit_input], outputs=[gallery])
#         btn_gr_img_interrogate.click(fn=on_click_img_url_interrogate, inputs=[gr_img_url, gr_model, gr_threshold, gr_space, gr_escape, gr_confidence, gr_order], outputs=[gr_output_text])

#         gallery.select(fn=on_select_gallery, 
#                        inputs=[gallery, gr_model, gr_threshold, gr_space, gr_escape, gr_confidence, gr_order],
#                        outputs=[gr_output_text, gr_output_source_tags])

#     demo.queue(os.cpu_count()).launch()