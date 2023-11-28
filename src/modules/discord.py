from threading import Thread
import discord
from discord import File
from discord.errors import Forbidden
import threading
import asyncio
from src.common import config, utils
import cv2
import base64
from src.detection import detection
import io


intents = discord.Intents.default()
client = discord.Client(intents=intents)
target_user = None


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
    config.bot.type_solution(answer)


@client.event
async def on_ready():
    global target_user
    print(f'Logged on as {client.user}!')
    try:
        target_user = await client.fetch_user(319685126323961859)
    except Forbidden as e:
        print(f"Error fetching user: {e}")


async def send_captcha(frame, solution):
    print("Sending captcha")
    top = 170
    left = 530
    width = 200
    height = 50

    # Crop the image to the captcha area
    cropped = frame[top:top + height, left:left + width]
    # Ensure this function is defined elsewhere
    await send_image_to_discord(cropped, f'Captcha solved using solution: {solution}')


async def send_image_to_discord(image, txt):
    is_success, buffer = cv2.imencode(".jpg", image)
    io_buf = io.BytesIO(buffer)
    file = File(io_buf, filename="image.jpg")

    try:
        await target_user.send(txt, file=file)
    except Forbidden as e:
        print(f"Error sending message to user: {txt} : {e}")
