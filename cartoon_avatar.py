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

# Define 2 models for LLM and image model, can be changed with any POE bots
LLM_MODEL = "RekaFlash"
IMAGE_MODEL = "Playground-v2.5"

class CartoonAvatarBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        for message in reversed(request.query):
            for attachment in message.attachments:
                print(f'Attachment: {attachment.content_type}') 
                print(f'Query: {request.query}')
                #yield fp.PartialResponse(text=f'Attachment: {attachment.content_type}')
                #if attachment.content_type == "application/pdf":
        
        message = request.query[-1]
        message.content = f"""Please read this image as a profile avatar. Describe the key spec of the main person:
            1. Include hair, skin color, gender, cloth, Accessories, posture, facial expression.
            2. Make the information from step 1 a image prompt within 70 words.
            3. Print the prompt in below json format:

            \`\`\`json
            "image_prompt": ""
            \`\`\`"""
        final_vision_prompt = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
        print(final_vision_prompt)
        image_prompt = self.extract_image_prompt(final_vision_prompt)
        print(image_prompt)

        # Query Image Model for creating image
        message.content = f"Illustration photo, soft colors, Japanese anime style, white background, sticker of [{image_prompt}]"
        image_response = await fp.get_final_response(request, bot_name=IMAGE_MODEL, api_key=request.access_key)
        print(image_response)
        yield fp.PartialResponse(text=f'{image_response}')

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1}, 
                                   introduction_message="Welcome to the Cartoon-Avatar Bot running by @xiaowenzhang. Please provide a image I will create a cartoon style avatar image for you...",
                                   allow_attachments=True)
    
    # Read the JSON string and extract the image_prompt and caption. Poe does not support JSON object call on GPT3.5/4
    def extract_image_prompt(self, long_string):
    # 定义正则表达式模式
        pattern = r'"image_prompt": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"


REQUIREMENTS = ["fastapi-poe==0.0.34"] # latest 0.0.34
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("cartoon-avatar-poe")


@stub.function(image=image, secrets=[modal.Secret.from_name("poe-secret"), modal.Secret.from_dotenv()])
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
    app = fp.make_app(bot, access_key=os.environ["AVATAR_BOT_KEY"])
    return app