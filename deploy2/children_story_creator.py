#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
儿童绘本故事创作服务

基于用户输入创作四段式儿童绘本故事，每段包含故事文本和配图。
使用 LLM 生成故事内容，使用图像模型生成配图。
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
import json

# 定义 LLM 和图像模型，可以根据需要更换为其他 POE 机器人
LLM_MODEL = "Gemini-2.5-Pro-Preview"
IMAGE_MODEL = "Imagen-3-Fast"

class ChildrenStoryCreatorBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        print('开始处理儿童绘本故事创作请求...')
        try:
            # 只使用最新的一条查询
            request.query = [request.query[-1]]
            message = request.query[-1]
            original_content = message.content

            # 第一步：调用 LLM 创作四段式儿童绘本故事
            story_prompt = f"""请根据用户的要求创作一个适合儿童的绘本短篇故事。            

用户要求：[{original_content}]

首先，判断用户要求使用的语言，并使用同样的语种写故事。这是最重要的需求，你必须遵守！

然后，故事需要分成四段，每段都要包含：
1. 故事段落文本，语言要跟[用户要求]的语言使用同一语种。
2. 配图的英文提示词（详细描述画面内容，适合AI绘图）


请严格按照以下JSON格式返回：
```json
[
  {{
    "story_text": "",
    "image_prompt": "Detailed English prompt for illustration"
  }},
  {{
    "story_text": "", 
    "image_prompt": "Detailed English prompt for illustration"
  }},
  {{
    "story_text": "",
    "image_prompt": "Detailed English prompt for illustration"
  }},
  {{
    "story_text": "",
    "image_prompt": "Detailed English prompt for illustration"
  }}
]
```

注意：
- 故事要有完整的起承转合，有寓意或者有趣好笑，小众不落俗套
- 每段文字控制在200字
- 英文提示词要详细描述画面，包含角色、场景、动作、情感等，主角需要保持外观一致性
- 画风要适合儿童绘本，温馨可爱"""
            
            message.content = story_prompt
            print('LLM 提示词: \n', message.content)
            
            # 获取 LLM 生成的故事内容
            story_response = await fp.get_final_response(request, bot_name=LLM_MODEL, api_key=request.access_key)
            print('LLM 响应:', story_response)
            
            # 解析故事 JSON
            story_data = self.extract_story_json(story_response)
            if not story_data:
                yield fp.PartialResponse(text="Sorry, failed to generate story.")
                return
            
            yield fp.PartialResponse(text="🎨 **Creating a new story for you...** \n\n")
            
            # 第二步：遍历每个故事段落，生成文本和图片
            for i, segment in enumerate(story_data, 1):
                story_text = segment.get('story_text', '')
                image_prompt = segment.get('image_prompt', '')
                
                # 2.1 渲染故事文本到客户端
                yield fp.PartialResponse(text=f"**Section {i}：**\n{story_text}\n\n")
                
                # 2.2 生成配图
                if image_prompt:
                    # 优化图像提示词，添加儿童绘本风格
                    enhanced_prompt = f"""{image_prompt}

Style: Children's book illustration, warm and friendly, soft colors, cartoon style, digital art, high quality"""
                    
                    # 调用图像模型生成图片
                    message.content = enhanced_prompt
                    print(f'第{i}段图像提示词: \n{enhanced_prompt}')
                    
                    sent_files = []
                    async for msg in fp.stream_request(
                        request, IMAGE_MODEL, request.access_key
                    ):
                        # Add whatever logic you'd like to handle text responses from the Bot
                        pass
                        # If there is an attachment, add it to the list of sent files
                        if msg.attachment:
                            print(f'第{i}段图像响应:', msg.attachment)
                            sent_files.append(msg.attachment)
                    #print(f'第{i}段图像响应:', image_response)
                    for file in sent_files:
                        yield fp.PartialResponse(text=f"![第{i}段图像]({file.url})\n\n")
                else:
                    yield fp.PartialResponse(text="⚠️ Failed to create image...\n\n")
            
            # 第三步：完成提示
            yield fp.PartialResponse(text="✨ **Done creating story for you！** Hope you and your kid(s) like the story！")
            
        except Exception as e:
            print(f"发生错误: {e}")
            yield fp.PartialResponse(text=f"Sorry, system error：{str(e)}")
            return
    
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={LLM_MODEL: 1, IMAGE_MODEL: 4}, 
            introduction_message="🎨 **Welcome to Children Story Pro！Provide me a topic or requirement! If you are non-Chinese user, specify your language in the prompt.**",
            allow_attachments=False
        )
    
    def extract_story_json(self, response_text):
        """从 LLM 响应中提取故事 JSON 数据"""
        try:
            # 尝试找到 JSON 代码块
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            match = re.search(json_pattern, response_text)
            
            if match:
                json_str = match.group(1).strip()
            else:
                # 如果没有代码块，尝试直接解析整个响应
                # 寻找数组开始和结束
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx+1]
                else:
                    print("无法找到有效的 JSON 数据")
                    return None
            
            # 解析 JSON
            story_data = json.loads(json_str)
            
            # 验证数据格式
            if isinstance(story_data, list) and len(story_data) == 4:
                for segment in story_data:
                    if not isinstance(segment, dict) or 'story_text' not in segment or 'image_prompt' not in segment:
                        print("JSON 数据格式不正确")
                        return None
                return story_data
            else:
                print("故事数据不是包含4个段落的数组")
                return None
                
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            return None
        except Exception as e:
            print(f"提取故事数据时发生错误: {e}")
            return None


REQUIREMENTS = ["fastapi-poe==0.0.63"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("children-story-creator-poe")


@app.function(image=image, secrets=[modal.Secret.from_name("poe-secret"), modal.Secret.from_dotenv()])
@asgi_app()
def fastapi_app():
    bot = ChildrenStoryCreatorBot()
    # 可选：在这里提供您的 Poe 访问密钥
    # 1. 您可以访问 https://poe.com/create_bot?server=1 生成访问密钥
    # 2. 我们强烈建议为生产环境的机器人使用密钥以防止滥用
    # 3. 您也可以将访问密钥存储在 modal.com 上并在此函数中检索
    
    # 使用环境变量中的访问密钥
    app = fp.make_app(bot, access_key=os.environ.get("CHILDREN_STORY_BOT_KEY", ""))
    return app