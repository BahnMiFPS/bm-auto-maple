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
    FLASH_JUMP = 'z'

    # Buffs
    THORNS = 'a'
    HASTE = 's'
    FINAL_CUT = 'd'
    RAID = 'ctrl'

    # Skills
    FLYING_ASSAULTER = 'x'
    BLOODY_STORM = 'c'
    ATTACK = 'v'
    CHAIN_OF_HELL = 'f'
    UPPER_STAB = 'f2'
    SUDDEN_RAID = 'f1'


#########################
#       Commands        #
#########################

def step(direction, target):
    """
    Performs one movement step in the given DIRECTION towards TARGET.
    Should not press any arrow keys, as those are handled by Kaizen Auto.
    """

    if config.stage_fright and direction != 'up' and utils.bernoulli(0.75):
        time.sleep(utils.rand_float(0.1, 0.3))
    d_y = target[1] - config.player_pos[1]
    if abs(d_y) > settings.move_tolerance * 1.5:
        if direction == 'down':
            press(Key.JUMP, 1, down_time=0.1, up_time=0.05)
        elif direction == 'up':
            press(Key.JUMP, 1, down_time=0.1, up_time=0.05)
    # press(Key.JUMP, 1, down_time=0.15, up_time=0.05)
    # press(Key.FLASH_JUMP, 1, down_time=0.05, up_time=0.05)
    time.sleep(0.1)


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
                        press(Key.JUMP, 1, down_time=0.1)
                    else:
                        key_down('down')
                        time.sleep(0.05)
                        press(Key.JUMP, 1, down_time=0.1)
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
        self.cd100_buff_time = 0
        self.cd240_buff_time = 0
        self.cd900_buff_time = 0
        self.decent_buff_time = 0

    def main(self):
        buffs = [Key.THORNS, Key.HASTE, Key.FINAL_CUT]
        now = time.time()
        # if self.cd20_buff_time == 0 or now - self.cd20_buff_time > 20:
        #     press(Key.RAID,  1, down_time=0.3)
        #     self.cd20_buff_time = now
        if self.decent_buff_time == 0 or now - self.decent_buff_time > settings.buff_cooldown:
            press(Key.ATTACK, 3)
            time.sleep(0.1)
            press(Key.THORNS,  1, down_time=0.3)
            time.sleep(5.0)
            press(Key.HASTE,  1, down_time=0.3)
            time.sleep(3.0)
            self.decent_buff_time = now
        if self.cd100_buff_time == 0 or now - self.cd100_buff_time > settings.finalcut_cooldown:
            time.sleep(1)
            key_down(Key.FINAL_CUT)
            time.sleep(2)
            key_up(Key.FINAL_CUT)
            time.sleep(2)
            self.cd100_buff_time = now


class FlashJump(Command):
    """Performs a flash jump in the given direction."""

    def __init__(self, direction):
        super().__init__(locals())
        self.direction = settings.validate_arrows(direction)

    def main(self):
        key_down(self.direction)
        time.sleep(0.1)
        press(Key.JUMP, 1)
        time.sleep(0.1)
        press(Key.FLASH_JUMP, 2)
        if self.direction == 'up':
            press(Key.JUMP, 2)
            press(Key.FLASH_JUMP, 3)
        else:
            press(Key.FLASH_JUMP, 1)
        key_up(self.direction)
        time.sleep(0.5)


class ChainCombo(Command):
    """
    ChainCombo in a given direction, or towards the center of the map if
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

            # Press space (jump) and wait 200 milliseconds
            press(Key.JUMP, 1, down_time=0.15, up_time=0.05)
            press(Key.FLASH_JUMP, 1, down_time=0.05, up_time=0.05)
            # Press 'z' and wait 200 milliseconds
            # press(Key.FLASH_JUMP, 2)

            # Press 'x' three times with 50 milliseconds between each press
            press(Key.FLYING_ASSAULTER, 1, down_time=0.1, up_time=0.05)

            time.sleep(0.8)  # Wait 800 milliseconds before the next sequence

            # Press 'c' three times with 50 milliseconds between each press
            press(Key.BLOODY_STORM, 2)
            key_up(current_direction)
            # directional handler
            # Wait 500 milliseconds after the combo is done
            time.sleep(0.8)
        if settings.record_layout:
            config.layout.add(*config.player_pos)


class ReverseChainCombo(Command):
    """
    ChainCombo in a given direction, or towards the center of the map if
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
            reverse_direction = 'left' if current_direction == 'right' else 'right'
            press(reverse_direction, 1, down_time=0.05, up_time=0.05)
            time.sleep(0.1)
            # Press space (jump) and wait 200 milliseconds
            press(Key.JUMP, 1, down_time=0.15, up_time=0.05)
            press(Key.FLASH_JUMP, 1, down_time=0.1, up_time=0.05)

            # Press 'z' and wait 200 milliseconds
            # press(Key.FLASH_JUMP, 2)
            key_down(current_direction)
            time.sleep(0.05)
            # Press 'x' three times with 50 milliseconds between each press
            press(Key.FLYING_ASSAULTER, 1, down_time=0.1, up_time=0.05)

            time.sleep(0.8)  # Wait 800 milliseconds before the next sequence

            # Press 'c' three times with 50 milliseconds between each press
            press(Key.BLOODY_STORM, 2)
            key_up(current_direction)
            # directional handler
            # Wait 500 milliseconds after the combo is done
            time.sleep(0.9)
        if settings.record_layout:
            config.layout.add(*config.player_pos)


class BloodyStorm(Command):
    """
    BloodyStorm in a given direction, or towards the center of the map if
    no direction is specified. Adds the player's position to the current
    Layout if necessary.
    Can add a number of repetitions to the command.
    """

    def __init__(self, direction='none', repetitions=1):
        super().__init__(locals())
        self.direction = direction
        self.repetitions = int(repetitions)

    def main(self):
        for _ in range(self.repetitions):
            if self.direction != 'none':
                press(self.direction, 1, down_time=0.05, up_time=0.05)
            else:
                if config.player_pos[0] > 0.5:
                    press('left', 1, down_time=0.05, up_time=0.05)
                else:
                    press('right', 1, down_time=0.05, up_time=0.05)
            press(Key.BLOODY_STORM, 2)
            time.sleep(0.8)


class UsePortal(Command):
    """Use Portal."""

    def main(self):
        press('up', 3, down_time=0.1, up_time=0.05)


class JumpFlashToRopes(Command):
    """
    Jump Flash in a given direction. 
    Hold up for x amount of seconds to be attached to the ropes
    """

    def __init__(self, direction='none', duration=1.0):
        super().__init__(locals())
        self.direction = direction
        self.duration = float(duration)

    def main(self):

        # directional handler
        if self.direction != 'none':
            current_direction = self.direction
        else:
            if config.player_pos[0] > 0.5:
                current_direction = 'left'
            else:
                current_direction = 'right'
        press(current_direction, 1, down_time=0.05, up_time=0.05)
        press(Key.JUMP, 1, down_time=0.1, up_time=0.05)
        key_down('up')
        press(Key.FLASH_JUMP, 1, down_time=0.05, up_time=0.05)
        time.sleep(self.duration)
        key_up('up')


class ChainOfHell(Command):
    """Use Chain Of Hell."""

    def main(self):
        press(Key.CHAIN_OF_HELL, 1, down_time=0.1, up_time=0.05)
        time.sleep(0.5)


class SuddenRaid(Command):
    """Use Sudden Raid."""

    def main(self):
        press(Key.SUDDEN_RAID, 1, down_time=0.1, up_time=0.05)
        time.sleep(1)


class FinalCut(Command):
    """Use FinalCut."""

    def __init__(self, direction='right', duration=1.0):
        super().__init__(locals())
        self.direction = direction
        self.duration = float(duration)

    def main(self):

        press(self.direction, 1, down_time=0.05, up_time=0.05)
        time.sleep(0.5)
        key_down(Key.FINAL_CUT)
        time.sleep(2)
        key_up(Key.FINAL_CUT)
        time.sleep(1)
