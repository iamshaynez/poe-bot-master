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
LLM_MODEL = "Claude-3-Sonnet"
IMAGE_MODEL = "ComicBookStyle-PGV2"

class CartoonAvatarBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        try:
            # pick the one last message
            message = request.query[-1]
            # save original user message
            original_content = message.content

            # create story and a image prompt
            message.content = f"""你是一个童话故事作家，你需要根据用户提供的主题或要求，每一次生成一段简单，单一段落的童话故事的后续情节和一张配图插画描述。根据用户的输入，前面的对话中的故事上下文，以相同的语言，
                并总是按照如下 json 格式输出。
                用户的输入：[{original_content}]
                \`\`\`json
                "story": "",
                "short_image_prompt: ""
                \`\`\`"""
            # the story and image prompt
            story_response = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
            print("story_response returned ...")
            print(story_response)
            print("story_response ends...")

            image_prompt = self.extract_image_prompt(story_response)
            story = self.extract_story(story_response)
            print(f"image prompt: [{image_prompt}]")
            print(f"story: [{story}]")
            yield fp.PartialResponse(text=f'"{story}"')
            new_request = request.model_copy(
                update={
                    "query":  [request.query[-1]]
                }
            )
            new_request.query[-1].content = image_prompt
            image_response = await fp.get_final_response(new_request, bot_name=IMAGE_MODEL, api_key=request.access_key)
            print("--- final ---")
            print(f'"{story}"\n\n{image_response}')

            yield fp.PartialResponse(text=f'\n\n{image_response}')
        except Exception as e:
            print("Exception:", e)
            yield fp.PartialResponse(text="Something went wrong. Please try again or contact the admin.")
            return
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1}, 
                                   introduction_message="Welcome to the Childbook Story Teller Bot running by @xiaowenzhang. Talk to me and I will keep creating story with image for you.",
                                   allow_attachments=True)
    
    # Read the JSON string and extract the image_prompt and caption. Poe does not support JSON object call on GPT3.5/4
    def extract_image_prompt(self, long_string):
    # 定义正则表达式模式
        pattern = r'"short_image_prompt": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"

    def extract_story(self, long_string):
    # 定义正则表达式模式
        pattern = r'"story": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, long_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"
    
REQUIREMENTS = ["fastapi-poe==0.0.34"] # latest 0.0.34
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("child-story-creator-poe")


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
    app = fp.make_app(bot, access_key=os.environ["STORY_BOT_KEY"])
    return app
