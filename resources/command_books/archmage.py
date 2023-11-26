"""A collection of all commands that Shadower can use to interact with the game. 	"""

from src.common import config, settings, utils
import time
import math
from src.routine.components import Command
from src.common.vkeys import press, key_down, key_up


# List of key mappings
class Key:
    # Movement
    JUMP = 'space'
    TELEPORT = 'z'

    # Buffs
    THORNS = 'a'
    HASTE = 's'

    # Skills
    BIG_BANG = 'x'
    ATTACK = 'v'
    BLIZZARD = 'd'

#########################
#       Commands        #
#########################


def step(direction, target):
    """
    Performs one movement step in the given DIRECTION towards TARGET.
    Should not press any arrow keys, as those are handled by Auto Maple.
    """

    num_presses = 2
    if direction == 'up' or direction == 'down':
        num_presses = 1
    if config.stage_fright and direction != 'up' and utils.bernoulli(0.75):
        time.sleep(utils.rand_float(0.1, 0.3))
    d_y = target[1] - config.player_pos[1]
    if abs(d_y) > settings.move_tolerance * 1.5:
        if direction == 'down':
            press(Key.JUMP, 3)
    press(Key.TELEPORT, num_presses)


class Adjust(Command):
    """Fine-tunes player position using small movements."""

    def __init__(self, x, y, max_steps=5):
        super().__init__(locals())
        self.target = (float(x), float(y))
        self.max_steps = settings.validate_nonnegative_int(max_steps)

    def main(self):
        counter = self.max_steps
        toggle = True
        error = utils.distance(config.player_pos, self.target)
        while config.enabled and counter > 0 and error > settings.adjust_tolerance:
            if toggle:
                d_x = self.target[0] - config.player_pos[0]
                threshold = settings.adjust_tolerance / math.sqrt(2)
                if abs(d_x) > threshold:
                    walk_counter = 0
                    if d_x < 0:
                        key_down('left')
                        while config.enabled and d_x < -1 * threshold and walk_counter < 60:
                            time.sleep(0.05)
                            walk_counter += 1
                            d_x = self.target[0] - config.player_pos[0]
                        key_up('left')
                    else:
                        key_down('right')
                        while config.enabled and d_x > threshold and walk_counter < 60:
                            time.sleep(0.05)
                            walk_counter += 1
                            d_x = self.target[0] - config.player_pos[0]
                        key_up('right')
                    counter -= 1
            else:
                d_y = self.target[1] - config.player_pos[1]
                if abs(d_y) > settings.adjust_tolerance / math.sqrt(2):
                    if d_y < 0:
                        Teleport('up').main()
                    else:
                        key_down('down')
                        time.sleep(0.05)
                        press(Key.JUMP, 3, down_time=0.1)
                        key_up('down')
                        time.sleep(0.05)
                    counter -= 1
            error = utils.distance(config.player_pos, self.target)
            toggle = not toggle


class Buff(Command):
    """Uses each of Shadowers's buffs once."""

    def __init__(self):
        super().__init__(locals())
        self.cd20_buff_time = 0
        self.cd120_buff_time = 0
        self.cd240_buff_time = 0
        self.cd900_buff_time = 0
        self.decent_buff_time = 0

    def main(self, reset=False):
        now = time.time()
        # if self.cd20_buff_time == 0 or now - self.cd20_buff_time > 20:
        #     press(Key.BLIZZARD,  1, down_time=0.3)
        #     self.cd20_buff_time = now
        if self.decent_buff_time == 0 or now - self.decent_buff_time > settings.buff_cooldown or reset:
            press(Key.THORNS,  1, down_time=0.3)
            time.sleep(3.0)
            press(Key.HASTE,  1, down_time=0.3)
            time.sleep(3.0)
            self.decent_buff_time = now


class Teleport(Command):
    """
    Teleports in a given direction, jumping if specified. Adds the player's position
    to the current Layout if necessary.
    """

    def __init__(self, direction, jump='False'):
        super().__init__(locals())
        self.direction = settings.validate_arrows(direction)
        self.jump = settings.validate_boolean(jump)

    def main(self):
        num_presses = 3
        time.sleep(0.05)
        if self.direction in ['up', 'down']:
            num_presses = 2
        key_down(self.direction)
        time.sleep(0.05)
        press(Key.TELEPORT, num_presses)
        key_up(self.direction)
        if settings.record_layout:
            config.layout.add(*config.player_pos)


class TPBigBang(Command):
    """
    Teleport and BigBang in a given direction, or towards the center of the map if
    no direction is specified. Adds the player's position to the current
    Layout if necessary.
    Can add a number of repetitions to the command.
    """

    def __init__(self, direction='none', repetitions=1):
        super().__init__(locals())
        self.direction = direction
        self.repetitions = int(repetitions)

    def main(self):
        # directional handler
        for _ in range(self.repetitions):
            if self.direction != 'none':
                current_direction = self.direction
            else:
                if config.player_pos[0] > 0.5:
                    current_direction = 'left'
                else:
                    current_direction = 'right'
            key_down(current_direction)

            press(Key.TELEPORT, 1, down_time=0.2, up_time=0.05)
            press(Key.BIG_BANG, 1, down_time=0.1, up_time=0.05)
            key_up(current_direction)
            time.sleep(0.4)
        if settings.record_layout:
            config.layout.add(*config.player_pos)


class DoubleTPBigBang(Command):
    """
    Teleport and BigBang in a given direction, or towards the center of the map if
    no direction is specified. Adds the player's position to the current
    Layout if necessary.
    Can add a number of repetitions to the command.
    """

    def __init__(self, direction='none', repetitions=1):
        super().__init__(locals())
        self.direction = direction
        self.repetitions = int(repetitions)

    def main(self):
        # directional handler
        for _ in range(self.repetitions):
            if self.direction != 'none':
                current_direction = self.direction
            else:
                if config.player_pos[0] > 0.5:
                    current_direction = 'left'
                else:
                    current_direction = 'right'
            key_down(current_direction)
            press(Key.TELEPORT, 2, down_time=0.2, up_time=0.05)
            press(Key.TELEPORT, 2)
            press(Key.BIG_BANG, 3, down_time=0.1, up_time=0.05)
            key_up(current_direction)
            time.sleep(0.4)
        if settings.record_layout:
            config.layout.add(*config.player_pos)


class BigBang(Command):
    """
    BigBang in a given direction, or towards the center of the map if
    no direction is specified. Adds the player's position to the current
    Layout if necessary.
    Can add a number of repetitions to the command.
    """

    def __init__(self, repetitions=1):
        super().__init__(locals())
        self.repetitions = int(repetitions)

    def main(self):
        for _ in range(self.repetitions):
            press(Key.BIG_BANG, 1)
            time.sleep(0.35)


class UsePortal(Command):
    """Use Portal."""

    def main(self):
        press('up', 3, down_time=0.1, up_time=0.05)


class Blizzard(Command):
    """Use Portal."""

    def main(self):
        press(Key.BLIZZARD, 3, down_time=0.1, up_time=0.05)
        time.sleep(4)


class ClimbRope(Command):
    """Use Rope at designated point for x amount of time."""

    def __init__(self, time=2):
        super().__init__(locals())
        self.time = int(time)

    def main(self):
        press(Key.JUMP, 1, down_time=0.2, up_time=0.05)
        key_down('up')
        time.sleep(self.time)
        key_up('up')


class JumpInDirection(Command):
    """Use Jump at designated point for x amount of time."""

    def __init__(self, direction):
        super().__init__(locals())
        self.direction = direction

    def main(self):
        key_down(self.direction)
        press(Key.JUMP, 1, down_time=2, up_time=0.05)
        key_up(self.direction)
