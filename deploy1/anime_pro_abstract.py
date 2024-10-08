"""

Create a memes for tweeting or sharing. With a quota and an image.

Using a LLM and a text2img model.

"""

from __future__ import annotations

from typing import AsyncIterable
import asyncio
import fastapi_poe as fp
from modal import Image, App, asgi_app
import modal
import time
import re
import os

# Define 2 models for LLM and image model, can be changed with any POE bots
LLM_MODEL = "Gemini-1.0-Pro"
IMAGE_MODEL = "Playground-v3"

class CartoonAvatarBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        try:
            # remove content, only use the latest 1 query.
            request.query = [request.query[-1]]
            # pick the one last message
            message = request.query[-1]
            # save original user message
            original_content = message.content
            # validate attachment, only allow 1 and image 
            if len(message.attachments) != 1 or not message.attachments[0].content_type.startswith('image'):
                yield fp.PartialResponse(text="Please send an image.")
                return

            # prompt to vision model and describe the image
            # if any key infor missed from the converted image, this prompt can be used to optimize
            # current GPT4 on poe doesnot support this prompt.
            message.content = f"""Based on image, describe：
                1. The category of the photograph, composition, angle, the color tone, the theme, a summary of the composition, and a description of the main subject(s) or object(s), including information such as age.
                2. generate a prompt of 60 English words or less for image remix, keep main information and subjects.
                3. Print the prompt in below json format, in english:

                \`\`\`json
                "image_prompt": ""
                \`\`\`"""
            # the prompt for remix image
            final_vision_prompt = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
            print(final_vision_prompt)
            image_prompt = self.extract_image_prompt(final_vision_prompt)
            print(image_prompt)

            # Query Image Model for creating image
            # the attachment is kept within the same request, only prompt is placed in the content
            # use poe remix image model, currently only SDXL and Playground is supported. Let's see when DALLE3 gives the same capability
            message.content = f"in Abstract Harmonics style, expressive, Watercolor style of [{image_prompt}]"
            image_response = await fp.get_final_response(request, bot_name=IMAGE_MODEL, api_key=request.access_key)
            print(image_response)
            yield fp.PartialResponse(text=f'{image_response}')
        except:
            yield fp.PartialResponse(text="Something went wrong. Please try again or contact the admin.")
            return
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1}, 
                                   introduction_message="Welcome to the Anime Image Bot running by @xiaowenzhang. Please provide a image I will create a cartoon style avatar image for you...",
                                   allow_attachments=True)
    
    # Read the JSON string and extract the image_prompt and caption. Poe does not support JSON object call on GPT3.5/4
    def extract_image_prompt(self, long_string):
    # 定义正则表达式模式
        pattern = r'"image_prompt": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"


REQUIREMENTS = ["fastapi-poe==0.0.44"] # latest 0.0.34
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("anime-pro-abstract-poe")


@app.function(image=image, secrets=[modal.Secret.from_name("poe-secret"), modal.Secret.from_dotenv()])
@asgi_app()
def fastapi_app():
    bot = CartoonAvatarBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)

    #app = fp.make_app(bot, allow_without_key=True)
    app = fp.make_app(bot, access_key=os.environ["ANIME_PRO_ABS_BOT_KEY"])
    return app
