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
  LAYER_MOMENTRY = 4


KeyAssignment = collections.namedtuple('KeyAssignment', ['type', 'code'])
LambdaAssignment = collections.namedtuple('LambdaAssignment', ['on_press', 'on_release'])


SCAN_KEY_MATRIX_INTERVAL = 0.01


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
        KeyAssignment(CodeType.KEYBOARD, Keycode.CAPS_LOCK),
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
        KeyAssignment(CodeType.KEYBOARD, Keycode.OPTION),
        KeyAssignment(CodeType.KEYBOARD, Keycode.COMMAND),  # left_command
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
        KeyAssignment(CodeType.KEYBOARD, Keycode.APPLICATION),
        # ROW7
        KeyAssignment(CodeType.KEYBOARD, Keycode.N),
        KeyAssignment(CodeType.KEYBOARD, Keycode.M),
        KeyAssignment(CodeType.KEYBOARD, Keycode.COMMA),
        KeyAssignment(CodeType.KEYBOARD, Keycode.PERIOD),
        KeyAssignment(CodeType.KEYBOARD, Keycode.FORWARD_SLASH),
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_SHIFT),
        KeyAssignment(CodeType.KEYBOARD, Keycode.RIGHT_GUI),  # right_command
        None,
    ],
]


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

      key_map_layer = 0
      pressed_keys = [None for _ in range(len(key_event_planners))]

      scan_key_matrix_timing = time.monotonic()  # For debounce
      while True:
        current_time = time.monotonic()

        if current_time >= scan_key_matrix_timing:
          are_keys_pressed = key_matrix.scan_matrix()
          for i, key_event_planner in enumerate(key_event_planners):
            key_event = key_event_planner.make_event(
                current_time, are_keys_pressed[i])
            if key_event == KeyEvent.PRESS:
              # print(f"""pressed : {i}""")
              pressed_keys[i] = KEY_MAP_LAYERS[key_map_layer][i]
              key_assignment = pressed_keys[i]
              if key_assignment is None:
                pass
              elif isinstance(key_assignment, KeyAssignment):
                if key_assignment.type == CodeType.LAYER_MOMENTRY:
                  key_map_layer = 1
                elif key_assignment.type == CodeType.KEYBOARD:
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
              elif isinstance(key_assignment, KeyAssignment):
                if key_assignment.type == CodeType.LAYER_MOMENTRY:
                  pass
                elif key_assignment.type == CodeType.KEYBOARD:
                  # print(f"""pressed : {i}""")
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
              elif isinstance(key_assignment, KeyAssignment):
                if key_assignment.type == CodeType.LAYER_MOMENTRY:
                  key_map_layer = 0
                elif key_assignment.type == CodeType.KEYBOARD:
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
