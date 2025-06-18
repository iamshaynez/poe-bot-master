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
LLM_MODEL = "Gemini-2.5-Flash-Preview"
IMAGE_MODEL = "Ideogram-v3"

class OgImageCreatorBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        print('Started Processing...')
        try:
            # remove content, only use the latest 1 query.
            request.query = [request.query[-1]]
            # pick the one last message
            message = request.query[-1]
            # save original user message
            original_content = message.content

            # prompt to vision model and describe the image
            # if any key infor missed from the converted image, this prompt can be used to optimize
            # current GPT4 on poe doesnot support this prompt.
            message.content = f"""Based on the content user provide, create a creative web landing page design in below format.

\`\`\`content
{original_content}
\`\`\`

Print output in json, your design should be outstanding, creative like art.

\`\`\`json
"describe_the_web_page": " ",
"web_title": " ",
"web_subtitle":"",
"highlight_wording":""
\`\`\`"""
            print('Prompt: \n', message.content)
            # the prompt for remix image
            response_string = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
            print(response_string)
            
            # extract key words
            describe_the_web_page = self.extract_image_prompt(response_string, "describe_the_web_page")
            web_title = self.extract_image_prompt(response_string, "web_title")
            web_subtitle = self.extract_image_prompt(response_string, "web_subtitle")
            highlight_wording = self.extract_image_prompt(response_string, "highlight_wording")

            # final prompt
            message.content = f"""A Web Landing Page design for {describe_the_web_page}
- Title: "{web_title}"
- Subtitle: "{web_subtitle}"
- Highlights: "{highlight_wording}"

--style DESIGN
--aspect 16:9
"""
            print(f'Image Prompt: \n{message.content}')
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

        except Exception as e:
            print(f"An error occurred: {e}")
            yield fp.PartialResponse(text=f"Something went wrong. Please try again or contact the admin.")
            return
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1}, 
                                   introduction_message="Welcome to Web Landing Page Designer Pro running by @xiaowenzhang. Please provide content or even a full article for me to create Creative Web Page for you. \n\n**Click Upvote to Support my work!**",
                                   allow_attachments=True)
    
    # Read the JSON string and extract the image_prompt and caption. Poe does not support JSON object call on GPT3.5/4
    def extract_image_prompt(self, json_string, tag):
    # 定义正则表达式模式
        pattern = rf'"{tag}": "(.*?)"'
        
        # 使用re.search查找第一个匹配项
        match = re.search(pattern, json_string)
        
        # 如果找到匹配项，返回匹配的内容，否则返回"ERROR"
        return match.group(1) if match else "ERROR"


REQUIREMENTS = ["fastapi-poe==0.0.44"] # latest 0.0.34
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("web-designer-pro-poe")


@app.function(image=image, secrets=[modal.Secret.from_name("poe-secret"), modal.Secret.from_dotenv()])
@asgi_app()
def fastapi_app():
    bot = OgImageCreatorBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    print('api started...')
    key = os.environ["WEBDESIGNER_BOT_KEY"]
    print(f"Key:{key}")
    #app = fp.make_app(bot, allow_without_key=True)
    app = fp.make_app(bot, access_key=key)
    return app
