import storage

import board
import digitalio

esc_row_io = digitalio.DigitalInOut(board.GPIO29)
esc_row_io.switch_to_output(False, digitalio.DriveMode.OPEN_DRAIN)
esc_col_io = digitalio.DigitalInOut(board.GPIO21)
esc_col_io.switch_to_input(digitalio.Pull.UP)
is_usb_drive_enabled = esc_col_io.value == False

if is_usb_drive_enabled:
  storage.remount("/", readonly=False)
  m = storage.getmount("/")
  m.label = "OCTAVE_CP"
  storage.remount("/", readonly=True)
  storage.enable_usb_drive()
else:
  storage.disable_usb_drive()
