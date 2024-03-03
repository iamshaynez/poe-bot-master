"""

Create a memes for tweeting or sharing. With a quota and an image.

Using a LLM and a text2img model.

"""

from __future__ import annotations

from typing import AsyncIterable
import asyncio
import fastapi_poe as fp
from modal import Image, Stub, asgi_app
import modal
import time
import re
import os

LLM_MODEL = "Mistral-Large"
IMAGE_MODEL = "Playground-v2.5"

class MemesCreatorBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:

        last_message = request.query[-1].content
        print(f'Last Messaging: {last_message}')

        # Query LLM for creating memes
        prompt = f"""1. You are comedia good at sarcasm and jokes with deep thoughs.
        2. Create 10 humour and sarcasm and deep joke meme about {last_message}.
        3. Read thru all the memes and pick one of the best meme.
        4. Print the one final meme in below json format.

        \`\`\`json
        "image_prompt": " ",
        "caption": " "
        \`\`\`"""

        print(f'Prompt: {prompt}')
        request.query = [fp.ProtocolMessage(role="user", content=prompt)]

        # Query LLM for creating memes
        final_meme = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
        print(final_meme)

        image_prompt = self.extract_image_prompt(final_meme)
        caption = self.extract_caption_prompt(final_meme)
        print(f'Image Prompt: {image_prompt}')
        print(f'Caption: {caption}')

        yield fp.PartialResponse(text=f'"{caption}"')

        # Query Image Model for creating image
        request.query = [fp.ProtocolMessage(role="user", content=f"{image_prompt}, digital painting")]
        image_response = await fp.get_final_response(request, bot_name=IMAGE_MODEL, api_key=request.access_key)
        print(f'Image Response: {image_response}')

        yield fp.PartialResponse(text=image_response)

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1})
    
    def extract_image_prompt(self, long_string):
    # 定义正则表达式模式
        pattern = r'"image_prompt": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"
    def extract_caption_prompt(self, long_string):
    # 定义正则表达式模式
        pattern = r'"caption": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"

REQUIREMENTS = ["fastapi-poe==0.0.34"] # latest 0.0.34
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("memes-creator-poe")


@stub.function(image=image, secrets=[modal.Secret.from_name("poe-secret"), modal.Secret.from_dotenv()])
@asgi_app()
def fastapi_app():
    bot = MemesCreatorBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)

    #app = fp.make_app(bot, allow_without_key=True)
    app = fp.make_app(bot, access_key=os.environ["MEME_BOT_KEY"])
    return app
