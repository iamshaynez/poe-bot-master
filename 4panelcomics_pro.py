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
LLM_MODEL = "GPT-4o"
IMAGE_MODEL = "Ideogram"

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
            message.content = f"""Based on the content user provide, create a story for 4 panels of comic in less than 10 words for each panel. 

\`\`\`content
{original_content}
\`\`\`

steps:

1. create a story line with one main character(can be person or anything based on the nature of the content)
2. from the story make 4 very simple prompts for each panel of comic in less than 10 words for each
3. print output in json

\`\`\`json
"story_line": " ",
"panel1_prompt": " ",
"panel2_prompt":"",
"panel3_prompt":"",
"panel4_prompt":""
\`\`\`"""
            print('Prompt: \n', message.content)
            # the prompt for remix image
            response_string = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
            print(response_string)
            
            # extract the story and 4 prompts
            story_line = self.extract_image_prompt(response_string, "story_line")
            panel1_prompt = self.extract_image_prompt(response_string, "panel1_prompt")
            panel2_prompt = self.extract_image_prompt(response_string, "panel2_prompt")
            panel3_prompt = self.extract_image_prompt(response_string, "panel3_prompt")
            panel4_prompt = self.extract_image_prompt(response_string, "panel4_prompt")

            # final prompt
            message.content = f"generate a four panel comic with a minimalist style of doodle. about: \n1.{panel1_prompt} 2.{panel2_prompt} 3.{panel3_prompt} 4.{panel4_prompt}"
            print(f'Image Prompt: \n{message.content}')
            image_response = await fp.get_final_response(request, bot_name=IMAGE_MODEL, api_key=request.access_key)
            #print(message.content)
            print(image_response)
            yield fp.PartialResponse(text=f'"**Story**: \n\n{story_line}"\n\n{image_response}')

        except Exception as e:
            print(f"An error occurred: {e}")
            yield fp.PartialResponse(text=f"Something went wrong. Please try again or contact the admin.")
            return
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 1}, 
                                   introduction_message="Welcome to 4PanelComics Pro running by @xiaowenzhang. Please provide content or even a full article for me to create a 4 Panel Comics for you. \n\n**Click Upvote to Support my work!**",
                                   allow_attachments=False)
    
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
app = App("fourpanelcomics-pro-poe")


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

    #app = fp.make_app(bot, allow_without_key=True)
    app = fp.make_app(bot, access_key=os.environ["FOURPANEL_BOT_KEY"])
    return app
