import collections
import time

import board
import digitalio
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

from octave_pcb.key_event import KeyEvent, KeyEventPlanner
from octave_pcb.key_matrix import KeyMatrix


class CodeType:
  KEYBOARD = 0
  MOUSE_MOVE = 1
  MOUSE_BUTTON = 2
  CONSUMER_CONTROL = 3


class KeycodeJp:
  JAPANESE_KANA = 0x90  # LANG1
  JAPANESE_EISUU = 0x91  # LANG2


class KeycodeLayer:
  MO1 = 0xFF01
  MO2 = 0xFF02


def is_code_mo(code):
  return True if code == KeycodeLayer.MO1 or code == KeycodeLayer.MO2 else False


ComplexModifierAssignment = collections.namedtuple('ComplexModifierAssignment', ['modifier', 'code_for_standalone'])
"""
1) If you release the key before it becomes a long press, send the standalone code.
2) When a key becomes a long press, or just before another KeyAssignment becomes press,
    the modifier becomes press.
"""

KeyAssignment = collections.namedtuple('KeyAssignment', ['type', 'code'])
LambdaAssignment = collections.namedtuple('LambdaAssignment', ['on_press', 'on_release'])


SCAN_KEY_MATRIX_INTERVAL = 0.02


KEY_MAP_LAYERS = [
    [
        # ROW0
        KeyAssignment(CodeType.KEYBOARD, Keycode.ESCAPE),
        None,
        KeyAssignment(CodeType.KEYBOARD, Keycode.ONE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.TWO),
        KeyAssignment(CodeType.KEYBOARD, Keycode.THREE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.FOUR),
        KeyAssignment(CodeType.KEYBOARD, Keycode.FIVE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.SIX),
        # ROW1
        KeyAssignment(CodeType.KEYBOARD, Keycode.TAB),
        None,
        None,
        KeyAssignment(CodeType.KEYBOARD, Keycode.Q),
        KeyAssignment(CodeType.KEYBOARD, Keycode.W),
        KeyAssignment(CodeType.KEYBOARD, Keycode.E),
        KeyAssignment(CodeType.KEYBOARD, Keycode.R),
        KeyAssignment(CodeType.KEYBOARD, Keycode.T),
        # ROW2
        ComplexModifierAssignment(KeycodeLayer.MO1, KeycodeJp.JAPANESE_EISUU),  # CAPS_LOCK
        KeyAssignment(CodeType.KEYBOARD, Keycode.Z),
        KeyAssignment(CodeType.KEYBOARD, Keycode.X),
        KeyAssignment(CodeType.KEYBOARD, Keycode.A),
        KeyAssignment(CodeType.KEYBOARD, Keycode.S),
        KeyAssignment(CodeType.KEYBOARD, Keycode.D),
        KeyAssignment(CodeType.KEYBOARD, Keycode.F),
        KeyAssignment(CodeType.KEYBOARD, Keycode.G),
        # ROW3
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_SHIFT),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_CONTROL),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_ALT),  # left_option
        ComplexModifierAssignment(Keycode.LEFT_GUI, KeycodeJp.JAPANESE_EISUU),  # left_command
        KeyAssignment(CodeType.KEYBOARD, Keycode.SPACE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.C),
        KeyAssignment(CodeType.KEYBOARD, Keycode.V),
        KeyAssignment(CodeType.KEYBOARD, Keycode.B),
        # ROW4
        KeyAssignment(CodeType.KEYBOARD, Keycode.SEVEN),
        KeyAssignment(CodeType.KEYBOARD, Keycode.EIGHT),
        KeyAssignment(CodeType.KEYBOARD, Keycode.NINE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.ZERO),
        KeyAssignment(CodeType.KEYBOARD, Keycode.MINUS),
        KeyAssignment(CodeType.KEYBOARD, Keycode.EQUALS),
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSLASH),
        KeyAssignment(CodeType.KEYBOARD, Keycode.GRAVE_ACCENT),
        # ROW5
        KeyAssignment(CodeType.KEYBOARD, Keycode.Y),
        KeyAssignment(CodeType.KEYBOARD, Keycode.U),
        KeyAssignment(CodeType.KEYBOARD, Keycode.I),
        KeyAssignment(CodeType.KEYBOARD, Keycode.O),
        KeyAssignment(CodeType.KEYBOARD, Keycode.P),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_BRACKET),
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_BRACKET),
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSPACE),
        # ROW6
        KeyAssignment(CodeType.KEYBOARD, Keycode.H),
        KeyAssignment(CodeType.KEYBOARD, Keycode.J),
        KeyAssignment(CodeType.KEYBOARD, Keycode.K),
        KeyAssignment(CodeType.KEYBOARD, Keycode.L),
        KeyAssignment(CodeType.KEYBOARD, Keycode.SEMICOLON),
        KeyAssignment(CodeType.KEYBOARD, Keycode.QUOTE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.RETURN),
        KeyAssignment(CodeType.KEYBOARD, KeycodeLayer.MO2),
        # ROW7
        KeyAssignment(CodeType.KEYBOARD, Keycode.N),
        KeyAssignment(CodeType.KEYBOARD, Keycode.M),
        KeyAssignment(CodeType.KEYBOARD, Keycode.COMMA),
        KeyAssignment(CodeType.KEYBOARD, Keycode.PERIOD),
        KeyAssignment(CodeType.KEYBOARD, Keycode.FORWARD_SLASH),
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_SHIFT),
        ComplexModifierAssignment(Keycode.RIGHT_GUI, KeycodeJp.JAPANESE_KANA),  # right_command
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_ALT),  # right_option (tentative))
    ],
    [
        # ROW0 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.ESCAPE),
        None,
        KeyAssignment(CodeType.KEYBOARD, Keycode.F1),  # ONE
        KeyAssignment(CodeType.KEYBOARD, Keycode.F2),  # TWO
        KeyAssignment(CodeType.KEYBOARD, Keycode.F3),  # THREE
        KeyAssignment(CodeType.KEYBOARD, Keycode.F4),  # FOUR
        KeyAssignment(CodeType.KEYBOARD, Keycode.F5),  # FIVE
        KeyAssignment(CodeType.KEYBOARD, Keycode.F6),  # SIX
        # ROW1 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.TAB),
        None,
        None,
        KeyAssignment(CodeType.KEYBOARD, Keycode.HOME),  # Q
        KeyAssignment(CodeType.KEYBOARD, Keycode.UP_ARROW),  # W
        KeyAssignment(CodeType.KEYBOARD, Keycode.END),  # E
        KeyAssignment(CodeType.KEYBOARD, Keycode.PAGE_UP),  # R
        KeyAssignment(CodeType.KEYBOARD, Keycode.T),
        # ROW2 (Layer1)
        None,  # MO(1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.Z),
        KeyAssignment(CodeType.KEYBOARD, Keycode.X),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_ARROW),  # A
        KeyAssignment(CodeType.KEYBOARD, Keycode.DOWN_ARROW),  # S
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_ARROW),  # D
        KeyAssignment(CodeType.KEYBOARD, Keycode.PAGE_DOWN),  # F
        KeyAssignment(CodeType.KEYBOARD, Keycode.G),
        # ROW3 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_SHIFT),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_CONTROL),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_ALT),  # left_option
        ComplexModifierAssignment(Keycode.LEFT_GUI, KeycodeJp.JAPANESE_EISUU),  # left_command
        KeyAssignment(CodeType.KEYBOARD, Keycode.SPACE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.C),
        KeyAssignment(CodeType.KEYBOARD, Keycode.V),
        KeyAssignment(CodeType.KEYBOARD, Keycode.B),
        # ROW4 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.F7),  # SEVEN
        KeyAssignment(CodeType.KEYBOARD, Keycode.F8),  # EIGHT
        KeyAssignment(CodeType.KEYBOARD, Keycode.F9),  # NINE
        KeyAssignment(CodeType.KEYBOARD, Keycode.F10),  # ZERO
        KeyAssignment(CodeType.KEYBOARD, Keycode.F11),  # MINUS
        KeyAssignment(CodeType.KEYBOARD, Keycode.F12),  # EQUALS
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSLASH),
        KeyAssignment(CodeType.KEYBOARD, Keycode.GRAVE_ACCENT),
        # ROW5 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.Y),
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSPACE),  # U
        KeyAssignment(CodeType.KEYBOARD, Keycode.I),
        KeyAssignment(CodeType.KEYBOARD, Keycode.O),
        KeyAssignment(CodeType.KEYBOARD, Keycode.P),
        KeyAssignment(CodeType.KEYBOARD, Keycode.UP_ARROW),  # LEFT_BRACKET
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_BRACKET),
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSPACE),
        # ROW6 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.ENTER),  # H
        KeyAssignment(CodeType.KEYBOARD, KeycodeJp.JAPANESE_KANA),  # J
        KeyAssignment(CodeType.KEYBOARD, Keycode.K),
        KeyAssignment(CodeType.KEYBOARD, Keycode.L),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_ARROW),  # SEMICOLON
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_ARROW),  # QUOTE
        KeyAssignment(CodeType.KEYBOARD, Keycode.RETURN),
        None,  # MO(2)
        # ROW7 (Layer1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.N),
        KeyAssignment(CodeType.KEYBOARD, Keycode.M),
        KeyAssignment(CodeType.KEYBOARD, Keycode.COMMA),
        KeyAssignment(CodeType.KEYBOARD, Keycode.PERIOD),
        KeyAssignment(CodeType.KEYBOARD, Keycode.DOWN_ARROW),  # FORWARD_SLASH
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_SHIFT),
        ComplexModifierAssignment(Keycode.RIGHT_GUI, KeycodeJp.JAPANESE_KANA),  # right_command
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_ALT),  # right_option (tentative))
    ],
    [
        # ROW0 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.ESCAPE),
        None,
        KeyAssignment(CodeType.KEYBOARD, Keycode.ONE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.TWO),
        KeyAssignment(CodeType.KEYBOARD, Keycode.THREE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.FOUR),
        KeyAssignment(CodeType.KEYBOARD, Keycode.FIVE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.SIX),
        # ROW1 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.TAB),
        None,
        None,
        KeyAssignment(CodeType.KEYBOARD, Keycode.Q),
        KeyAssignment(CodeType.KEYBOARD, Keycode.W),
        KeyAssignment(CodeType.KEYBOARD, Keycode.E),
        KeyAssignment(CodeType.KEYBOARD, Keycode.R),
        KeyAssignment(CodeType.KEYBOARD, Keycode.T),
        # ROW2 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.CAPS_LOCK),  # MO(1)
        KeyAssignment(CodeType.KEYBOARD, Keycode.Z),
        KeyAssignment(CodeType.KEYBOARD, Keycode.X),
        KeyAssignment(CodeType.KEYBOARD, Keycode.A),
        KeyAssignment(CodeType.KEYBOARD, Keycode.S),
        KeyAssignment(CodeType.KEYBOARD, Keycode.D),
        KeyAssignment(CodeType.KEYBOARD, Keycode.F),
        KeyAssignment(CodeType.KEYBOARD, Keycode.G),
        # ROW3 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_SHIFT),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_CONTROL),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_ALT),  # left_option
        ComplexModifierAssignment(Keycode.LEFT_GUI, KeycodeJp.JAPANESE_EISUU),  # left_command
        KeyAssignment(CodeType.KEYBOARD, Keycode.SPACE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.C),
        KeyAssignment(CodeType.KEYBOARD, Keycode.V),
        KeyAssignment(CodeType.KEYBOARD, Keycode.B),
        # ROW4 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.SEVEN),
        KeyAssignment(CodeType.KEYBOARD, Keycode.EIGHT),
        KeyAssignment(CodeType.KEYBOARD, Keycode.NINE),
        KeyAssignment(CodeType.KEYBOARD, Keycode.ZERO),
        KeyAssignment(CodeType.KEYBOARD, Keycode.MINUS),
        KeyAssignment(CodeType.KEYBOARD, Keycode.EQUALS),
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSLASH),
        KeyAssignment(CodeType.KEYBOARD, Keycode.GRAVE_ACCENT),
        # ROW5 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.Y),
        KeyAssignment(CodeType.KEYBOARD, Keycode.U),
        KeyAssignment(CodeType.KEYBOARD, Keycode.I),
        KeyAssignment(CodeType.KEYBOARD, Keycode.O),
        KeyAssignment(CodeType.KEYBOARD, Keycode.P),
        KeyAssignment(CodeType.KEYBOARD, Keycode.UP_ARROW),  # LEFT_BRACKET
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_BRACKET),
        KeyAssignment(CodeType.KEYBOARD, Keycode.BACKSPACE),
        # ROW6 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.H),
        KeyAssignment(CodeType.KEYBOARD, Keycode.J),
        KeyAssignment(CodeType.KEYBOARD, Keycode.K),
        KeyAssignment(CodeType.KEYBOARD, Keycode.L),
        KeyAssignment(CodeType.KEYBOARD, Keycode.LEFT_ARROW),  # SEMICOLON
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_ARROW),  # QUOTE
        KeyAssignment(CodeType.KEYBOARD, Keycode.RETURN),
        None,  # MO(2)
        # ROW7 (Layer2)
        KeyAssignment(CodeType.KEYBOARD, Keycode.N),
        KeyAssignment(CodeType.KEYBOARD, Keycode.M),
        KeyAssignment(CodeType.KEYBOARD, Keycode.COMMA),
        KeyAssignment(CodeType.KEYBOARD, Keycode.PERIOD),
        KeyAssignment(CodeType.KEYBOARD, Keycode.DOWN_ARROW),  # FORWARD_SLASH
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_SHIFT),
        ComplexModifierAssignment(Keycode.RIGHT_GUI, KeycodeJp.JAPANESE_KANA),  # right_command
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_ALT),  # right_option (tentative))
    ],
]


class ComplexModifierStatus:
  def __init__(self):
    self.is_still_standalone = True


if __name__ == '__main__':
  key_matrix = KeyMatrix()
  key_event_planners = [KeyEventPlanner() for _ in range(len(key_matrix.row_ios) * len(key_matrix.col_ios))]

  cpu_pixpower = digitalio.DigitalInOut(board.NEOPIX_POWER)
  cpu_pixpower.switch_to_output(True, digitalio.DriveMode.PUSH_PULL)

  # Sleep for a bit to avoid a race condition on some systems
  time.sleep(2)

  while True:
    try:
      keyboard = Keyboard(usb_hid.devices)
      keyboard_layout = KeyboardLayoutUS(keyboard)
      mouse = Mouse(usb_hid.devices)
      consumer_control = ConsumerControl(usb_hid.devices)

      key_events = [None for _ in range(len(key_event_planners))]
      key_map_layer = 0
      pressed_keys = [None for _ in range(len(key_event_planners))]
      complex_modifier_status_list = [None for _ in range(len(key_event_planners))]

      scan_key_matrix_timing = time.monotonic()  # For debounce
      while True:
        current_time = time.monotonic()

        if current_time >= scan_key_matrix_timing:
          are_keys_pressed = key_matrix.scan_matrix()
          for i, key_event_planner in enumerate(key_event_planners):
            key_events[i] = key_event_planner.make_event(
                current_time, are_keys_pressed[i])

          # Check whether to stop standalone of complex modifiers
          stop_standalone_of_complex_modifiers = False
          for i, key_event in enumerate(key_events):
            if key_event == KeyEvent.PRESS:
              if isinstance(KEY_MAP_LAYERS[key_map_layer][i], KeyAssignment):
                stop_standalone_of_complex_modifiers = True
          if stop_standalone_of_complex_modifiers:
            for i in range(len(complex_modifier_status_list)):
              if complex_modifier_status_list[i] is not None and complex_modifier_status_list[i].is_still_standalone:
                complex_modifier_status_list[i].is_still_standalone = False
                if (pressed_keys[i].modifier == KeycodeLayer.MO1):
                  key_map_layer = 1
                elif (pressed_keys[i].modifier == KeycodeLayer.MO2):
                  key_map_layer = 2
                else:
                  keyboard.press(pressed_keys[i].modifier)

          for i, key_event in enumerate(key_events):
            if key_event == KeyEvent.PRESS:
              # print(f"""pressed : {i}""")
              pressed_keys[i] = KEY_MAP_LAYERS[key_map_layer][i]
              key_assignment = pressed_keys[i]
              if key_assignment is None:
                pass
              elif isinstance(key_assignment, ComplexModifierAssignment):
                complex_modifier_status_list[i] = ComplexModifierStatus()
              elif isinstance(key_assignment, KeyAssignment):
                if key_assignment.type == CodeType.KEYBOARD:
                  if (key_assignment.code == KeycodeLayer.MO1):
                    key_map_layer = 1
                  elif (key_assignment.code == KeycodeLayer.MO2):
                    key_map_layer = 2
                  else:
                    keyboard.press(key_assignment.code)
                elif key_assignment.type == CodeType.MOUSE_MOVE:
                  mouse.move(**key_assignment.code)
                elif key_assignment.type == CodeType.MOUSE_BUTTON:
                  mouse.press(key_assignment.code)
                elif key_assignment.type == CodeType.CONSUMER_CONTROL:
                  consumer_control.press(key_assignment.code)
              elif isinstance(key_assignment, LambdaAssignment) and key_assignment.on_press is not None:
                key_assignment.on_press()
            elif key_event == KeyEvent.LONG_PRESS:
              # print(f"""pressed : {i}""")
              key_assignment = pressed_keys[i]
              if key_assignment is None:
                pass
              elif isinstance(key_assignment, ComplexModifierAssignment):
                if complex_modifier_status_list[i].is_still_standalone:
                  complex_modifier_status_list[i].is_still_standalone = False
                  if (key_assignment.modifier == KeycodeLayer.MO1):
                    key_map_layer = 1
                  elif (key_assignment.modifier == KeycodeLayer.MO2):
                    key_map_layer = 2
                  else:
                    keyboard.press(key_assignment.modifier)
              elif isinstance(key_assignment, KeyAssignment):
                if key_assignment.type == CodeType.KEYBOARD:
                  # print(f"""pressed : {i}""")
                  if not is_code_mo(key_assignment.code):
                    keyboard.press(key_assignment.code)
                elif key_assignment.type == CodeType.MOUSE_MOVE:
                  # print(f"""pressed : {i}""")
                  mouse.move(**key_assignment.code)
            elif key_event == KeyEvent.RELEASE:
              # print(f"""released: {i}""")
              key_assignment = pressed_keys[i]
              pressed_keys[i] = None
              if key_assignment is None:
                pass
              elif isinstance(key_assignment, ComplexModifierAssignment):
                complex_modifier_status = complex_modifier_status_list[i]
                if complex_modifier_status.is_still_standalone:
                  if not is_code_mo(key_assignment.code_for_standalone):
                    keyboard.press(key_assignment.code_for_standalone)
                    keyboard.release(key_assignment.code_for_standalone)
                else:
                  if is_code_mo(key_assignment.modifier):
                    key_map_layer = 0
                  else:
                    keyboard.release(key_assignment.modifier)
                complex_modifier_status_list[i] = None
              elif isinstance(key_assignment, KeyAssignment):
                if key_assignment.type == CodeType.KEYBOARD:
                  if is_code_mo(key_assignment.code):
                    key_map_layer = 0
                  else:
                    keyboard.release(key_assignment.code)
                elif key_assignment.type == CodeType.MOUSE_BUTTON:
                  mouse.release(key_assignment.code)
                elif key_assignment.type == CodeType.CONSUMER_CONTROL:
                  consumer_control.release()
              elif isinstance(key_assignment, LambdaAssignment) and key_assignment.on_release is not None:
                key_assignment.on_release()

          scan_key_matrix_timing += SCAN_KEY_MATRIX_INTERVAL
          if scan_key_matrix_timing <= current_time:
            scan_key_matrix_timing = current_time + SCAN_KEY_MATRIX_INTERVAL

    except Exception:
      time.sleep(3)
