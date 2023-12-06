"""A module for detecting and notifying the user of dangerous in-game events."""

from src.common import config, utils
import time
import os
import cv2
import pygame
import threading
import numpy as np
import keyboard as kb
from src.routine.components import Point
from src.modules.bot import Bot
from src.modules.discord import send_image_to_discord
import asyncio
from src.modules.discord import client
# A rune's symbol on the minimap
RUNE_RANGES = (
    ((141, 148, 245), (146, 158, 255)),
)
rune_filtered = utils.filter_color(
    cv2.imread('assets/rune_template.png'), RUNE_RANGES)
RUNE_TEMPLATE = cv2.cvtColor(rune_filtered, cv2.COLOR_BGR2GRAY)

# Other players' symbols on the minimap
OTHER_RANGES = (
    ((0, 245, 215), (10, 255, 255)),
)
other_filtered = utils.filter_color(cv2.imread(
    'assets/other_template.png'), OTHER_RANGES)
OTHER_TEMPLATE = cv2.cvtColor(other_filtered, cv2.COLOR_BGR2GRAY)


# The Elite Boss's warning sign
ELITE_TEMPLATE = cv2.imread('assets/elite_template.jpg', 0)

# The Captcha clock warning
CAPTCHA_TEMPLATE = cv2.imread('assets/captcha_warning.png', 0)
DEBUG = False

MUYOUNG_TEMPLATE = cv2.imread('assets/muyoung.png', 0)
BALROG_BOSS_TEMPLATE = cv2.imread('assets/balrog_boss.png', 0)
CRIMSON_BALROG_TEMPLATE = cv2.imread('assets/crimson_balrog_dead.png', 0)
SCROLLS_TEMPLATE = cv2.imread('assets/scrolls.png', 0)


def schedule_coroutine(loop, coroutine):
    loop.call_soon_threadsafe(lambda: asyncio.create_task(coroutine))


def get_alert_path(name):
    return os.path.join(Notifier.ALERTS_DIR, f'{name}.mp3')


class Notifier:
    ALERTS_DIR = os.path.join('assets', 'alerts')

    def __init__(self):
        """Initializes this Notifier object's main thread."""

        try:
            pygame.mixer.init()
            self.mixer = pygame.mixer.music
        except pygame.error:
            print("Mixer init failed. Audio will not work.")
            self.mixer = None

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True

        self.room_change_threshold = 0.9
        self.rune_alert_delay = 270         # 4.5 minutes
        self.captcha_alert_delay = 50       # 50 seconds

    def start(self):
        """Starts this Notifier's thread."""

        print('\n[~] Started notifier')
        self.thread.start()

    def _main(self):
        self.ready = True
        last_black_screen_alert = None
        while True:
            if config.enabled:
                frame = config.capture.frame
                height, width, _ = frame.shape
                minimap = config.capture.minimap['minimap']

                now = time.time()
                # Check for unexpected black screen
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # if np.count_nonzero(gray < 15) / height / width > self.room_change_threshold:
                #     if last_black_screen_alert is None or now - last_black_screen_alert > 5:
                #         # self._alert('siren')
                #         if config.bot.auto_balrog:
                #             return
                #         print("Black screen detected")

                #         time.sleep(5)
                #         this_frame = config.capture.frame
                #         schedule_coroutine(client.loop, send_image_to_discord(
                #             this_frame, 'Black screen detected'))
                #         last_black_screen_alert = now
                # Check for elite warning
                # elite_frame = frame[height // 4:3 *
                #                     height // 4, width // 4:3 * width // 4]
                # elite = utils.multi_match(
                #     elite_frame, ELITE_TEMPLATE, threshold=0.9)
                # if len(elite) > 0:
                #     self._alert('siren')

                # Check for other players entering the map
                filtered = utils.filter_color(minimap, OTHER_RANGES)
                others = len(utils.multi_match(
                    filtered, OTHER_TEMPLATE, threshold=0.3))
                config.stage_fright = others > 0
                if others != config.bot.other_players:
                    if others > config.bot.other_players:
                        self._ping('ding', volume=0)
                    config.bot.other_players = others
                if config.bot.start_fighting_balrog:
                    balrog_boss = utils.multi_match(
                        frame, BALROG_BOSS_TEMPLATE, threshold=0.7)
                    if len(balrog_boss) > 0:
                        config.bot.balrog_found = True
                    else:
                        config.bot.balrog_found = False
                if config.bot.balrog_found:
                    dead_crimson = utils.multi_match(
                        frame, CRIMSON_BALROG_TEMPLATE, 0.9)
                    if len(dead_crimson) > 0:
                        config.bot.crimson_is_dead = True
                if config.bot.crimson_is_dead:
                    scrolls_on_ground = utils.multi_match(
                        frame, SCROLLS_TEMPLATE, 0.9)
                    if len(scrolls_on_ground) > 0:
                        config.bot.there_is_loot = True
                    else:
                        config.bot.there_is_loot = False
                        print(f"Scrolls are gone, setting there_is_loot to False")
                # Check for captcha warning
                if not config.bot.captcha_active:
                    captcha = utils.multi_match(
                        frame, CAPTCHA_TEMPLATE, threshold=0.9)
                    captcha_start_time = now
                    if captcha and config.routine.sequence:
                        time.sleep(0.1)
                        config.bot.captcha_active = True
                        print(
                            f"Captcha found, setting captcha_active to {config.bot.captcha_active}")
                        element = config.routine[config.routine.index]
                        element.execute()
                        config.routine.step()
                    # self._ping('rune_appeared', volume=0.75)
                elif now - captcha_start_time > self.captcha_alert_delay:
                    print(
                        f"Quitting game due to captcha start_time > {self.captcha_alert_delay}")
                    config.bot.captcha_timeout = True

                if config.bot.finding_muyoung:
                    # Convert the frame to grayscale
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    # Match the template
                    result = cv2.matchTemplate(
                        gray_frame, MUYOUNG_TEMPLATE, cv2.TM_CCOEFF_NORMED)
                    if result.any():
                        time.sleep(0.1)
                        _, max_val, _, max_loc = cv2.minMaxLoc(result)

                        # Calculate the center of the matched area
                        muyoung_center = (
                            max_loc[0] + MUYOUNG_TEMPLATE.shape[1] // 2, max_loc[1] + MUYOUNG_TEMPLATE.shape[0] // 2)

                        if max_val > 0.9:  # Adjust this threshold as needed
                            time.sleep(0.1)
                            config.bot.muyoung_pos = muyoung_center
                            config.bot.finding_muyoung = False

                if DEBUG:
                    config.bot.captcha_active = True

                # Check for rune
                # if not config.bot.rune_active:
                #     filtered = utils.filter_color(minimap, RUNE_RANGES)
                #     matches = utils.multi_match(
                #         filtered, RUNE_TEMPLATE, threshold=0.9)
                #     rune_start_time = now
                #     if matches and config.routine.sequence:
                #         abs_rune_pos = (matches[0][0], matches[0][1])
                #         config.bot.rune_pos = utils.convert_to_relative(
                #             abs_rune_pos, minimap)
                #         distances = list(
                #             map(distance_to_rune, config.routine.sequence))
                #         index = np.argmin(distances)
                #         config.bot.rune_closest_pos = config.routine[index].location
                #         config.bot.rune_active = True
                #         self._ping('rune_appeared', volume=0.75)
                # elif now - rune_start_time > self.rune_alert_delay:     # Alert if rune hasn't been solved
                #     config.bot.rune_active = False
                #     self._alert('siren')
            time.sleep(0.05)

    def _alert(self, name, volume=0.75):
        """
        Plays an alert to notify user of a dangerous event. Stops the alert
        once the key bound to 'Start/stop' is pressed.
        """
        config.enabled = False
        config.listener.enabled = False

        if self.mixer is not None:
            self.mixer.load(get_alert_path(name))
            self.mixer.set_volume(volume)
            self.mixer.play(-1)

        while not kb.is_pressed(config.listener.config['Start/stop']):
            time.sleep(0.1)

        if self.mixer is not None:
            self.mixer.stop()

        time.sleep(2)
        config.listener.enabled = True

    def _ping(self, name, volume=0.5):
        """A quick notification for non-dangerous events."""
        if self.mixer is not None:
            self.mixer.load(get_alert_path(name))
            self.mixer.set_volume(volume)
            self.mixer.play()


#################################
#       Helper Functions        #
#################################
def distance_to_rune(point):
    """
    Calculates the distance from POINT to the rune.
    :param point:   The position to check.
    :return:        The distance from POINT to the rune, infinity if it is not a Point object.
    """

    if isinstance(point, Point):
        return utils.distance(config.bot.rune_pos, point.location)
    return float('inf')
