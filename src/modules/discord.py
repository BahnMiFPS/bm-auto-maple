from threading import Thread
import discord
from discord import File
from discord.errors import Forbidden
import threading
import asyncio
from src.common import config, utils

import base64
from src.detection import detection
import io


intents = discord.Intents.default()
client = discord.Client(intents=intents)


def init():
    loop = asyncio.new_event_loop()
    loop.create_task(client.start(
        'MTE3NTc2NDM5NDM3OTA1NTEzNA.GPK6gk.6NxQCSIUmrhVMXxDqAiz-hdG3XPL49XH6ZJ174'))
    Thread(target=loop.run_forever).start()


@client.event
async def on_message(message):
    if message.author.id != 319685126323961859:
        return

    print(
        f'Message from {message.author.id}, type: {type(message.author.id)}: {message.content}')
    answer = []
    for letters in message.content:
        answer.append(letters)
    print(type(answer))
    config.bot.type_solution(answer)


@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')


async def send_captcha(frame):
    print("Sending captcha")
    top = 170
    left = 530
    width = 200
    height = 50

    # Crop the image to the captcha area
    cropped = frame[top:top + height, left:left + width]
    # Ensure this function is defined elsewhere
    base64_image = detection.encode_image(cropped)
    image_bytes = base64.b64decode(base64_image)
    file = File(io.BytesIO(image_bytes), filename="image.jpg")
    try:
        user = await client.fetch_user(319685126323961859)
        await user.send('Solve this', file=file)
    except Forbidden as e:
        print(f"Error sending message to user: {e}")
