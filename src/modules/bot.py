"""An interpreter that reads and executes user-created routines."""

import threading
import time
import git
import cv2
import asyncio
import numpy as np
from src.common import config, utils
from src.detection import detection
from src.modules.discord import client
from src.routine.routine import Routine
from src.command_book.command_book import CommandBook
from src.common.vkeys import press, click, key_down, key_up
from src.common.interfaces import Configurable
from src.modules.listener import Listener
import random
import asyncio
from src.modules.discord import send_captcha
# The rune's buff icon
RUNE_BUFF_TEMPLATE = cv2.imread('assets/rune_buff_template.jpg', 0)


def schedule_coroutine(loop, coroutine):
    loop.call_soon_threadsafe(lambda: asyncio.create_task(coroutine))


DEBUG = False


class Bot(Configurable):
    """A class that interprets and executes user-defined routines."""

    DEFAULT_CONFIG = {
        'Interact': 'y',
        'Feed pet': '9'
    }

    def __init__(self):
        """Loads a user-defined routine on start up and initializes this Bot's main thread."""

        super().__init__('keybindings')
        config.bot = self
        self.rune_active = False
        self.rune_pos = (0, 0)
        # Location of the Point closest to rune
        self.rune_closest_pos = (0, 0)
        self.submodules = []
        self.command_book = None            # CommandBook instance
        self.captcha_active = False
        self.captcha_timeout = False
        self.other_players = 0
        # self.module_name = None
        # self.buff = components.Buff()

        # self.command_book = {}
        # for c in (components.Wait, components.Walk, components.Fall,
        #           components.Move, components.Adjust, components.Buff):
        #     self.command_book[c.__name__.lower()] = c

        config.routine = Routine()

        self.ready = False
        self.thread = threading.Thread(target=self._main)
        self.thread.daemon = True
        self.captcha_max_attempts = 2
        self.last_captcha_id = None
        self.last_captcha_solved = None
        self.auto_balrog = False

        self.finding_muyoung = False
        self.muyoung_pos = (0, 0)

    def start(self):
        """
        Starts this Bot object's thread.
        :return:    None
        """

        # self.update_submodules()
        print('\n[~] Started main bot loop')
        self.thread.start()

    def _main(self):
        """
        The main body of Bot that executes the user's routine.
        :return:    None
        """
        self.ready = True
        config.listener.enabled = True
        last_fed = time.time()
        last_changed_server = time.time()
        players_detected_time = None
        next_channel_change = random.randint(9999, 99999)
        captcha_attempts = []  # Store timestamps of captcha attempts
        skip_step = False
        # last_loot_rotation = time.time()
        while True:
            # if config.enabled:
            #     self.auto_balrog = config.gui.settings.balrog.auto_balrog.get()
            # if config.enabled and self.auto_balrog:
            #     print(f"Finding Muyoung: {self.finding_muyoung}")
            #     """
            #     key down right until finding muyoung
            #     """
            #     now = time.time()
            #     # Turn book off for debug

            #     if not DEBUG:
            #         self.command_book.buff.main()
            #     pet_settings = config.gui.settings.pets
            #     auto_feed = pet_settings.auto_feed.get()
            #     num_pets = pet_settings.num_pets.get()

            #     if auto_feed and now - last_fed > 1200 / num_pets:
            #         press(self.config['Feed pet'], 1)
            #         last_fed = now
            #         print(
            #             f"Feeding pet at {time.strftime('%H:%M:%S', time.localtime())}")

            #     self.interact_muyoung(isEnter=True)
            #     time.sleep(1.5)
            #     self.fight_balrog()
            #     time.sleep(1)
            #     # self.loot_map()
            #     time.sleep(1)
            #     self.interact_muyoung(isEnter=False)
            #     time.sleep(2)

            if config.enabled and len(config.routine) > 0:

                # Buff and feed pets
                now = time.time()
                self.command_book.buff.main()
                pet_settings = config.gui.settings.pets
                auto_feed = pet_settings.auto_feed.get()
                num_pets = pet_settings.num_pets.get()

                if auto_feed and now - last_fed > 1200 / num_pets:
                    press(self.config['Feed pet'], 1)
                    last_fed = now
                    print(
                        f"Feeding pet at {time.strftime('%H:%M:%S', time.localtime())}")

                # Highlight the current Point
                config.gui.view.routine.select(config.routine.index)
                config.gui.view.details.display_info(config.routine.index)

                element = config.routine[config.routine.index]
                if self.other_players > 0:
                    if players_detected_time is None:
                        players_detected_time = now
                    print(
                        f"Players detected time: {now - players_detected_time}")
                    if now - players_detected_time > 5:
                        skip_step = True
                    if now - players_detected_time > 30 and skip_step:
                        self.change_channel()
                    elif now - players_detected_time > 20 and skip_step:
                        self.go_fm()
                else:
                    players_detected_time = None
                    skip_step = False
                # change channel after every 45 minutes - 1 hour
                if now - last_changed_server > next_channel_change:
                    print(
                        f"change channel after {next_channel_change} seconds")
                    self.change_channel()
                    last_changed_server = now
                    next_channel_change = random.randint(9999, 99999)

                if self.captcha_active:
                    self.captcha_timeout = False
                    captcha_attempts.append(now)
                    if len(captcha_attempts) > 1:
                        print(
                            "Bad captcha solution reported")
                        detection.report_captcha(isGood=False)
                    print(f"Captcha attempts:: {captcha_attempts}")
                    self._solve_captcha()

                else:
                    if captcha_attempts and (now - captcha_attempts[-1] > 600):
                        # report last captcha is good
                        if self.last_captcha_id is not None:
                            print(
                                "Last captcha is good, reporting to server")
                            detection.report_captcha(isGood=True)
                        captcha_attempts.clear()
                if not skip_step and (not captcha_attempts or now - captcha_attempts[-1] > 5):
                    element.execute()
                    config.routine.step()
            else:
                time.sleep(0.01)

    def interact_muyoung(self, isEnter=True):
        """
        Moves to the right until muyoung is found on the screen and click him
        :return:        None
        """
        print("interact_muyoung called")
        self.finding_muyoung = True

        time.sleep(1)

        while self.finding_muyoung:
            key_down('right')
            key_down('z')

        key_up('right')
        key_up('z')
        time.sleep(3)
        self.finding_muyoung = True
        time.sleep(2)
        print(f"finding muyoung is: {self.finding_muyoung}")
        if not self.finding_muyoung:
            click(self.muyoung_pos, button='left')
            time.sleep(1)
            click(self.muyoung_pos, button='left')

            print('\nInteracting with muyoung:')

            if isEnter:
                press('enter', 1)
                time.sleep(1)
                press('enter', 1)
                time.sleep(1)
                click(self.muyoung_pos, button='left')
                time.sleep(1)
                click(self.muyoung_pos, button='left')
                time.sleep(1)
                press('down', 1)
                time.sleep(1)

                press('enter', 1)
                time.sleep(1)
                press('enter', 1)
            else:
                press('left', 1)
                time.sleep(1)

                press('left', 1)
                time.sleep(1)

                press('enter', 1)
                time.sleep(1)

    def fight_balrog(self):
        """
        Moves to the right and teleport twice then hold down attack for 1 minutes straight
        """

        print("Fighting balrog")
        # move to the right
        key_down('right')
        press('z', 1, down_time=0.2)
        time.sleep(1)
        key_up('right')
        time.sleep(0.5)

        for _ in range(30):
            press('f', 1, down_time=0.35)

        time.sleep(1)

    def loot_map(self):
        """
        Move to the right for 5 seconds, constantly press alt to loot while moving
        """
        print("Looting map")
        start_time = time.time()
        key_down('right')
        while time.time() - start_time < 3:
            print(time.time() - start_time)
            press('alt', 1, down_time=0.1)
        key_up('right')
        time.sleep(1)
        end_time = time.time()
        key_down('left')
        while time.time() - end_time < 3:
            print(time.time() - start_time)
            press('alt', 1, down_time=0.1)
        key_up('left')

        # teleport twice

    # @utils.run_if_enabled
    # def _solve_rune(self, model):
    #     """
    #     Moves to the position of the rune and solves the arrow-key puzzle.
    #     :param model:   The TensorFlow model to classify with.
    #     :param sct:     The mss instance object with which to take screenshots.
    #     :return:        None
    #     """
    #     move = self.command_book['move']
    #     move(*self.rune_pos).execute()
    #     adjust = self.command_book['adjust']
    #     adjust(*self.rune_pos).execute()
    #     time.sleep(0.2)
    #     # Inherited from Configurable
    #     press(self.config['Interact'], 1, down_time=0.2)
    #     print('\nSolving rune:')
    #     inferences = []
    #     for _ in range(15):
    #         frame = config.capture.frame
    #         solution = detection.merge_detection(model, frame)
    #         if solution:
    #             print(', '.join(solution))
    #             if solution in inferences:
    #                 print('Solution found, entering result')
    #                 for arrow in solution:
    #                     press(arrow, 1, down_time=0.1)
    #                 time.sleep(1)
    #                 for _ in range(3):
    #                     time.sleep(0.3)
    #                     frame = config.capture.frame
    #                     rune_buff = utils.multi_match(frame[:frame.shape[0] // 8, :],
    #                                                   RUNE_BUFF_TEMPLATE,
    #                                                   threshold=0.9)
    #                     if rune_buff:
    #                         rune_buff_pos = min(rune_buff, key=lambda p: p[0])
    #                         target = (
    #                             round(
    #                                 rune_buff_pos[0] + config.capture.window['left']),
    #                             round(rune_buff_pos[1] +
    #                                   config.capture.window['top'])
    #                         )
    #                         click(target, button='right')
    #                 self.rune_active = False
    #                 break
    #             elif len(solution) == 4:
    #                 inferences.append(solution)
    # def _solve_captcha(self, isLast=False):
    #     if not self.captcha_active:
    #         print("Captcha is not active", self.captcha_active)
    #         return

    #     max_attempts = 4
    #     solution_attempts = []
    #     attempt = 0
    #     initial_delay = 2  # initial delay in seconds
    #     print('\nSolving captcha:')
    #     while attempt < max_attempts and self.captcha_active:
    #         print(
    #             f"Attempt: {attempt} \n Is timeout? {self.captcha_timeout} \n Is active? {self.captcha_active}")
    #         if (attempt == 0):
    #             time.sleep(3)
    #         frame = config.capture.frame

    #         schedule_coroutine(client.loop, send_captcha(frame))

    #         solution = detection.captcha_detection(frame)
    #         if solution:
    #             solution_tuple = tuple(solution)
    #             solution_attempts.append(solution_tuple)
    #             print(f"Solution found on attempt {attempt + 1}: {solution}")
    #             attempt += 1
    #         else:
    #             print(f"No solution found on attempt {attempt + 1}")
    #             attempt += 1

    #         if attempt < 3:
    #             time.sleep(initial_delay * (1.5 * attempt))

    #     if solution_attempts or len(solution_attempts) == max_attempts:
    #         most_common_solution_tuple, _ = Counter(
    #             solution_attempts).most_common(1)[0]
    #         most_common_solution = list(most_common_solution_tuple)
    #         print(f"Most common solution: {most_common_solution}")
    #         self.type_solution(most_common_solution)
    #     else:
    #         print(
    #             f"Max attempts reached, typing out solution regardless. \n Solution Attempts: {solution_attempts} \n Attempt: {attempt}")
    #         self.type_solution(['N', 'a'])

    @utils.run_if_enabled
    def _solve_captcha(self, isLast=False):
        if not self.captcha_active:
            print("Captcha is not active", self.captcha_active)
            return
        frame = config.capture.frame
        solution = detection.captcha_detection(frame)
        schedule_coroutine(client.loop, send_captcha(frame, solution))
        if solution:
            print(f"Solution found: {solution}")
            self.last_captcha_id = solution['captchaId']
            self.type_solution(solution)
        if self.captcha_timeout:
            print(
                f"Timed out, typing out solution regardless.")
            self.type_solution(['N', 'a'])

    @utils.run_if_enabled
    def go_fm(self):
        print("Going to FM")
        target = (1222, 781)
        click(target, button='left')
        time.sleep(120)
        press('up', 2)
        time.sleep(0.1)
        config.routine.back_to_first_index()
        time.sleep(5)

    @utils.run_if_enabled
    def change_channel(self):
        if self.captcha_active:
            return
        print("Changing channel")
        random_channel_to_skip = random.randint(1, 4)
        press('esc', 1)
        time.sleep(2)
        press('enter', 1)
        time.sleep(2)
        press('right', random_channel_to_skip)
        time.sleep(2)
        press('enter', 1)
        time.sleep(4)
        press('ctrl', 3)
        self.command_book.buff.main()
        time.sleep(1)
        config.routine.back_to_first_index()
        time.sleep(1)
        self.players_detected_time = None
        # config.listener.toggle_enabled()

    @utils.run_if_enabled
    def type_solution(self, solution):
        print("Typing solution:")
        target = (572, 229)  # Coordinates to click the solution box
        click(target, button='left')
        for digit in solution['code']:
            if digit.isupper():
                print(digit, end=", ")
                key_down('shift')
                press(digit, 1, down_time=0.1)
                key_up('shift')
                time.sleep(0.2)
            else:
                press(digit, 1, down_time=0.1)
                time.sleep(0.2)
        press('enter', 1)
        time.sleep(1)
        press('enter', 1)
        time.sleep(1)
        self.captcha_timeout = False
        time.sleep(0.1)
        self.captcha_active = False  # Set captcha as solved
        time.sleep(1)

    @utils.run_if_enabled
    def quit_game(self):
        key_down('alt')
        press('f4', 1)
        key_up('alt')
        config.enabled = False
        time.sleep(1)
        self.captcha_timeout = False
        time.sleep(1)
        self.captcha_active = False
        time.sleep(1)

    def load_commands(self, file):
        try:
            self.command_book = CommandBook(file)
            config.gui.settings.update_class_bindings()
        except ValueError:
            pass    # TODO: UI warning popup, say check cmd for errors
        #
        # utils.print_separator()
        # print(f"[~] Loading command book '{basename(file)}':")
        #
        # ext = splitext(file)[1]
        # if ext != '.py':
        #     print(f" !  '{ext}' is not a supported file extension.")
        #     return False
        #
        # new_step = components.step
        # new_cb = {}
        # for c in (components.Wait, components.Walk, components.Fall):
        #     new_cb[c.__name__.lower()] = c
        #
        # # Import the desired command book file
        # module_name = splitext(basename(file))[0]
        # target = '.'.join(['resources', 'command_books', module_name])
        # try:
        #     module = importlib.import_module(target)
        #     module = importlib.reload(module)
        # except ImportError:     # Display errors in the target Command Book
        #     print(' !  Errors during compilation:\n')
        #     for line in traceback.format_exc().split('\n'):
        #         line = line.rstrip()
        #         if line:
        #             print(' ' * 4 + line)
        #     print(f"\n !  Command book '{module_name}' was not loaded")
        #     return
        #
        # # Check if the 'step' function has been implemented
        # step_found = False
        # for name, func in inspect.getmembers(module, inspect.isfunction):
        #     if name.lower() == 'step':
        #         step_found = True
        #         new_step = func
        #
        # # Populate the new command book
        # for name, command in inspect.getmembers(module, inspect.isclass):
        #     new_cb[name.lower()] = command
        #
        # # Check if required commands have been implemented and overridden
        # required_found = True
        # for command in [components.Buff]:
        #     name = command.__name__.lower()
        #     if name not in new_cb:
        #         required_found = False
        #         new_cb[name] = command
        #         print(f" !  Error: Must implement required command '{name}'.")
        #
        # # Look for overridden movement commands
        # movement_found = True
        # for command in (components.Move, components.Adjust):
        #     name = command.__name__.lower()
        #     if name not in new_cb:
        #         movement_found = False
        #         new_cb[name] = command
        #
        # if not step_found and not movement_found:
        #     print(f" !  Error: Must either implement both 'Move' and 'Adjust' commands, "
        #           f"or the function 'step'")
        # if required_found and (step_found or movement_found):
        #     self.module_name = module_name
        #     self.command_book = new_cb
        #     self.buff = new_cb['buff']()
        #     components.step = new_step
        #     config.gui.menu.file.enable_routine_state()
        #     config.gui.view.status.set_cb(basename(file))
        #     config.routine.clear()
        #     print(f" ~  Successfully loaded command book '{module_name}'")
        # else:
        #     print(f" !  Command book '{module_name}' was not loaded")

    def update_submodules(self, force=False):
        """
        Pulls updates from the submodule repositories. If FORCE is True,
        rebuilds submodules by overwriting all local changes.
        """

        utils.print_separator()
        print('[~] Retrieving latest submodules:')
        self.submodules = []
        repo = git.Repo.init()
        with open('.gitmodules', 'r') as file:
            lines = file.readlines()
            i = 0
            while i < len(lines):
                if lines[i].startswith('[') and i < len(lines) - 2:
                    path = lines[i + 1].split('=')[1].strip()
                    url = lines[i + 2].split('=')[1].strip()
                    self.submodules.append(path)
                    try:
                        # First time loading submodule
                        repo.git.clone(url, path)
                        print(f" -  Initialized submodule '{path}'")
                    except git.exc.GitCommandError:
                        sub_repo = git.Repo(path)
                        if not force:
                            sub_repo.git.stash()        # Save modified content
                        sub_repo.git.fetch('origin', 'main')
                        sub_repo.git.reset('--hard', 'FETCH_HEAD')
                        if not force:
                            try:                # Restore modified content
                                sub_repo.git.checkout('stash', '--', '.')
                                print(
                                    f" -  Updated submodule '{path}', restored local changes")
                            except git.exc.GitCommandError:
                                print(f" -  Updated submodule '{path}'")
                        else:
                            print(f" -  Rebuilt submodule '{path}'")
                        sub_repo.git.stash('clear')
                    i += 3
                else:
                    i += 1
