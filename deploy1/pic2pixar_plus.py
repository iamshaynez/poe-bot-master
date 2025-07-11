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
LLM_MODEL = "Gemini-1.5-Pro"
IMAGE_MODEL = "FLUX-pro-1.1"

class Pic2PixarBot(fp.PoeBot):
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
            message.content = f"""Based on image, describe follow below chains of thoughts：

1. understand the key concept of this photo and composition of main objects
2. From the main objects, describe this photo again to keep main information in image, including detail of key objects or person,  especially age, race, hair, cloth and positions in less than 200 words
3. Print the description in below json format, in english:

                \`\`\`json
                "image_prompt": ""
                \`\`\`"""
            # the prompt for remix image
            final_vision_prompt = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
            print(final_vision_prompt)
            image_prompt = self.extract_image_prompt(final_vision_prompt)
            

            # Query Image Model for creating image
            # the attachment is kept within the same request, only prompt is placed in the content
            # use poe remix image model, currently only SDXL and Playground is supported. Let's see when DALLE3 gives the same capability
            if original_content.startswith('--Style'):
                message.content = f"{original_content.replace('--Style', '')} of [{image_prompt}]"
            elif original_content.startswith('--Disney'):
                message.content = f"disney pixar cartoon movie style, norealistic, PS2, PS1, hyper detailed, digital art, trending in artstation, cinematic lighting, studio quality, smooth render of [{image_prompt}]"
            elif original_content.startswith('--Clash'):
                message.content = f"3d, clash of clans, fantasy game, detailed, photorealistic, disney style, pixar style of [{image_prompt}]"
            elif original_content.startswith('--Digital'):
                message.content = f"A digital painting by Artgerm, beautiful, masterpiece, concept art of [{image_prompt}]"
            else:
                message.content = f"disney pixar cartoon movie style, norealistic, PS2, PS1, hyper detailed, digital art, trending in artstation, cinematic lighting, studio quality, smooth render of of [{image_prompt}]"
            
            # remove attachments since the remix for image model changed.
            message.attachments = []
            request.query = [fp.ProtocolMessage(role="user", content=message.content)]

            sent_files = []
            async for msg in fp.stream_request(
                        request, IMAGE_MODEL, request.access_key
            ):
                # Add whatever logic you'd like to handle text responses from the Bot
                pass
                # If there is an attachment, add it to the list of sent files
                if msg.attachment:
                    print(f'图像响应:', msg.attachment)
                    sent_files.append(msg.attachment)

            for file in sent_files:
                yield fp.PartialResponse(text=f"![image]({file.url})\n\n")

            yield fp.PartialResponse(text=f'{image_response}')
        except:
            yield fp.PartialResponse(text="Something went wrong. Please try again or contact the admin.")
            return
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1}, 
                                   introduction_message="Welcome to the Pic2Pixar Image Bot Plus running by @xiaowenzhang. Please provide a image I will create a pixar style image for you...\n\n Update 20241124:\n\n - Change image model to FLUX-pro-1.1",
                                   allow_attachments=True)
    
    # Read the JSON string and extract the image_prompt and caption. Poe does not support JSON object call on GPT3.5/4
    def extract_image_prompt(self, long_string):
    # 定义正则表达式模式
        pattern = r'"image_prompt": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"


REQUIREMENTS = ["fastapi-poe==0.0.63"] # latest 0.0.34
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("pixar-plus-poe")


@app.function(image=image, secrets=[modal.Secret.from_name("poe-secret"), modal.Secret.from_dotenv()])
@asgi_app()
def fastapi_app():
    bot = Pic2PixarBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)

    #app = fp.make_app(bot, allow_without_key=True)
    app = fp.make_app(bot, access_key=os.environ["PIXAR_PLUS_BOT_KEY"])
    return app
