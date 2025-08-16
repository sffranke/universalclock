import network, ntptime, socket, os, time, machine, math, random
ntptime.host = "de.pool.ntp.org"
from neopixel import Neopixel

import urequests

# ---- Sonnenzeiten (UTC-Minuten) ----
sunrise_minutes = None
sunset_minutes = None

# Dynamischer Helligkeitsfaktor, 1x pro Minute/bei Bedarf aktualisieren
current_brightness_scale = 1.0
last_scale_minute = -1

def update_sun_times(lat, lon):
    global sunrise_minutes, sunset_minutes
    try:
        url = "http://api.sunrise-sunset.org/json?lat={}&lng={}&formatted=0".format(lat, lon)
        r = urequests.get(url)
        data = r.json()["results"]
        r.close()

        def to_minutes(timestr):
            # z.B. "2025-08-15T05:43:00+00:00"
            h = int(timestr[11:13])
            m = int(timestr[14:16])
            return h * 60 + m

        sunrise_minutes = to_minutes(data["sunrise"])
        sunset_minutes  = to_minutes(data["sunset"])
        print("Sonnenaufgang (UTC min):", sunrise_minutes)
        print("Sonnenuntergang (UTC min):", sunset_minutes)

    except Exception as e:
        print("Fehler beim Laden der Sonnenzeiten:", e)

def get_current_brightness():
    """Tag: brightness, Nacht: 20% davon (dynamische Skalierung)."""
    global brightness, sunrise_minutes, sunset_minutes
    if sunrise_minutes is None or sunset_minutes is None:
        return brightness  # Fallback bis Daten da sind

    # aktuelle Zeit in UTC Minuten
    t = time.gmtime()  # NTP setzt UTC
    now_min = t[3] * 60 + t[4]

    if sunrise_minutes <= now_min <= sunset_minutes:
        return brightness  # Tag
    else:
        return brightness * 0.5  # Nacht (sanft, nicht quasi aus)

def refresh_brightness_scale():
    """Berechnet current_brightness_scale ohne pro Pixel time.gmtime() aufzurufen."""
    global current_brightness_scale, last_scale_minute
    # aktuelle Minute (UTC) bestimmen
    t = time.gmtime()
    minute_id = t[3] * 60 + t[4]  # 0..1439

    # Nur neu berechnen, wenn Minute gewechselt hat
    if minute_id == last_scale_minute:
        return

    # Falls sunrise/sunset noch nicht da: Fallback
    if sunrise_minutes is None or sunset_minutes is None:
        current_brightness_scale = 1.0
    else:
        if sunrise_minutes <= minute_id <= sunset_minutes:
            current_brightness_scale = 1.0               # Tag
        else:
            current_brightness_scale = 0.5               # Nacht

    last_scale_minute = minute_id
### SIMULATION und Testzeit ###
SIMULATE_TIME = False  # Für Tests True, sonst False
SIMULATED_TIME = (2025, 4, 7, 2, 0, 3, 0, 97)
last_cuckoo_hour = -1

### Neopixel Setup (16×16 LED-Matrix) ###
anzahl_LEDs = 256         # 16x16 LEDs
pin = 1                   # z.B. GP2 des Pico W
pixels = Neopixel(anzahl_LEDs, 1, pin)

### Double Buffering ###
led_state = [(0, 0, 0) for _ in range(anzahl_LEDs)]
frame = [(0, 0, 0) for _ in range(anzahl_LEDs)]

### Einstellungen ###
brightness = 0.04
base_color = (0, 0, 100)  # Basisfarbe (für den Zeitteil)
text_farbe = (int(base_color[0]*brightness),
              int(base_color[1]*brightness),
              int(base_color[2]*brightness))
red_text = (0, int(255*brightness), 0)
upper_text_color = (int(255*brightness), 0, 0)  # Im oberen Bereich z. B. rot

# Farben für die Rose (Farbtausch)
rose_petals = (int(255*brightness), 0, 0)    # Rot
rose_leaves = (0, int(255*brightness), 0)     # Grün
smile_color = (int(255*brightness), 0, int(255*brightness))

def getoi():
    t = get_local_time()
    hour = t[3]
    print(hour)
    if 6 <= hour < 12:
        return "BOM DIA!"
    elif 12 <= hour < 18:
        return "BOA TARDE!"
    else:
        return "BOA NOITE"

### Nachrichten (für die Lauftextanzeige im unteren Bereich) ###
messages = [
    "ICH LIEBE DICH!",
    getoi,         # Funktion als Objekt übergeben
    "TE AMO!",
]

### Font-Definitionen ###
ziffern = {
    "0": [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
    "1": [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
    "2": [[1,1,1],[0,0,1],[1,1,1],[1,0,0],[1,1,1]],
    "3": [[1,1,1],[0,0,1],[0,1,1],[0,0,1],[1,1,1]],
    "4": [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
    "5": [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
    "6": [[1,1,1],[1,0,0],[1,1,1],[1,0,1],[1,1,1]],
    "7": [[1,1,1],[0,0,1],[0,1,0],[0,1,0],[0,1,0]],
    "8": [[1,1,1],[1,0,1],[1,1,1],[1,0,1],[1,1,1]],
    "9": [[1,1,1],[1,0,1],[1,1,1],[0,0,1],[1,1,1]],
    ":": [[0,0,0],[0,1,0],[0,0,0],[0,1,0],[0,0,0]],
    " ": [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]
}

letters = {
    "A": [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    "B": [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,1,0]],
    "C": [[0,1,1],[1,0,0],[1,0,0],[1,0,0],[0,1,1]],
    "D": [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
    "E": [[1,1,1],[1,0,0],[1,1,1],[1,0,0],[1,1,1]],
    "F": [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,0,0]],
    "G": [[0,1,1],[1,0,0],[1,0,1],[1,0,1],[0,1,1]],
    "H": [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    "I": [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
    "J": [[0,1,1],[0,0,1],[0,0,1],[1,0,1],[0,1,0]],
    "K": [[1,0,1],[1,1,0],[1,1,0],[1,0,1],[1,0,1]],
    "L": [[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
    "M": [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
    "N": [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    "O": [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
    "P": [[1,1,0],[1,0,1],[1,1,0],[1,0,0],[1,0,0]],
    "Q": [[0,1,0],[1,0,1],[1,0,1],[1,1,1],[0,1,1]],
    "R": [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
    "S": [[0,1,1],[1,0,0],[0,1,0],[0,0,1],[1,1,0]],
    "T": [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
    "U": [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
    "V": [[1,0,1],[1,0,1],[1,0,1],[0,1,0],[0,1,0]],
    "W": [[1,0,1],[1,0,1],[1,0,1],[1,1,1],[1,0,1]],
    "X": [[1,0,1],[0,1,0],[0,1,0],[0,1,0],[1,0,1]],
    "Y": [[1,0,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
    "Z": [[1,1,1],[0,0,1],[0,1,0],[1,0,0],[1,1,1]],
    "!": [[0,1,0],[0,1,0],[0,1,0],[0,0,0],[0,1,0]],
    " ": [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]
}

# Kombiniertes Font-Dictionary für den oberen Bereich
upper_font = {}
for key, matrix in letters.items():
    upper_font[key] = matrix
for key, matrix in ziffern.items():
    upper_font[key] = matrix
if "/" not in upper_font:
    upper_font["/"] = [
               [0,0,0],
               [0,0,1],
               [0,1,0],
               [1,0,0],
               [0,0,0]
    ]
upper_font["1"] = [
    [0,1],
    [1,1],
    [0,1],
    [0,1],
    [0,1]
]
upper_font[" "] = [
    [0],[0],[0],[0],[0]
]

# Obere Symbole
upper_symbols = {
    "smile": [
        [0,0,0,0,0,0,0],
        [0,0,1,0,1,0,0],
        [0,0,0,0,0,0,0],
        [1,0,0,1,0,0,1],
        [1,0,0,1,0,0,1],
        [0,1,0,0,0,1,0],
        [0,0,1,1,1,0,0]
    ],
    "smile2": [
        [0,1,1,1,1,1,0],
        [1,0,0,0,0,0,0],
        [1,0,0,0,0,0,1],
        [1,0,1,0,1,0,1],
        [1,0,0,1,0,0,1],
        [1,0,0,0,0,0,1],
        [0,1,1,1,1,1,0]
    ],
    "♥": [
        [0,1,0,0,0,1,0],
        [1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1],
        [0,1,1,1,1,1,0],
        [0,0,1,1,1,0,0],
        [0,0,0,1,0,0,0]
    ],
    "♥2": [
        [0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0],
        [0,0,1,0,1,0,0],
        [0,1,1,1,1,1,0],
        [0,1,1,1,1,1,0],
        [0,0,1,1,1,0,0],
        [0,0,0,1,0,0,0]
    ],
    "rose": [
        [0,0,1,1,1,0,0],
        [0,1,1,1,1,1,0],
        [1,1,1,1,1,1,1],
        [0,1,2,2,2,1,0],
        [0,0,2,2,2,0,0],
        [0,0,0,2,0,0,0],
        [0,0,0,2,0,0,0]
    ]
}
upper_symbols["cuckoo"] = [
    [0,0,1,1,1,0,0],
    [0,1,0,0,0,1,0],
    [1,0,0,1,0,0,1],
    [1,1,1,1,1,1,1],
    [1,0,1,1,1,0,1],
    [0,0,0,1,0,0,0],
    [0,0,0,1,0,0,0]
]

# Kuckuck-Symbol – 9 Pixel hoch und 16 Pixel breit
kuckuck = [
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [2, 2, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
]

# Globale Variablen für Animationen
heart_anim_x = 0
heart_anim_y_offset = 1
heart_anim_angle = 0
smile_anim_x = 0
smile_anim_y_offset = 1
smile_anim_angle = 0
rose_anim_x = 4
rose_anim_y_offset = 1

upper_anim_delay = 3000
next_upper_update = time.ticks_ms() + upper_anim_delay
current_upper_anim = None

# ---- Buffer/Zeichenroutinen ----
def xy_to_index(x, y):
    if y % 2 == 0:
        return y * 16 + (15 - x)
    else:
        return y * 16 + x

def set_pixel_frame(x, y, farbe):
    """Schnell: skaliert nur noch mit dem vorab berechneten Faktor."""
    if 0 <= x < 16 and 0 <= y < 16:
        index = xy_to_index(x, y)
        scale = current_brightness_scale  # kein time.gmtime() mehr hier!
        r, g, b = farbe
        farbe_dyn = (int(r*scale), int(g*scale), int(b*scale))
        global frame
        frame[index] = farbe_dyn
def clear_frame():
    global frame
    frame = led_state.copy()

def clear_region_frame(x0, y0, width, height):
    for y in range(y0, y0 + height):
        for x in range(x0, x0 + width):
            set_pixel_frame(x, y, (0, 0, 0))

def commit_frame():
    global led_state, frame
    changed = False
    for i in range(anzahl_LEDs):
        if led_state[i] != frame[i]:
            pixels.set_pixel(i, frame[i])
            led_state[i] = frame[i]
            changed = True
    if changed:
        pixels.show()

def create_text_matrix(text, font_dict, spacing=1, value=1):
    matrix = [[] for _ in range(5)]
    for i, ch in enumerate(text):
        char_matrix = font_dict.get(ch, font_dict[" "])
        for row in range(5):
            for pixel in char_matrix[row]:
                matrix[row].append(value if pixel == 1 else 0)
        if i != len(text) - 1:
            for row in range(5):
                matrix[row].extend([0] * spacing)
    return matrix

def combine_matrices(matrix1, matrix2, spacing=1):
    return [matrix1[row] + [0] * spacing + matrix2[row] for row in range(5)]

def display_text_window(text_matrix, window_x, y_offset, window_width):
    for row in range(5):
        for col in range(window_width):
            text_col = window_x + col
            if 0 <= text_col < len(text_matrix[row]):
                val = text_matrix[row][text_col]
                if val == 1:
                    set_pixel_frame(col, y_offset + row, text_farbe)
                elif val == 2:
                    set_pixel_frame(col, y_offset + row, red_text)
                else:
                    set_pixel_frame(col, y_offset + row, (0, 0, 0))
            else:
                set_pixel_frame(col, y_offset + row, (0, 0, 0))

def zeichne_symbol(symbol, start_x, start_y):
    for y in range(len(symbol)):
        for x in range(len(symbol[y])):
            if symbol[y][x] == 1:
                set_pixel_frame(start_x + x, start_y + y, text_farbe)
            else:
                set_pixel_frame(start_x + x, start_y + y, (0, 0, 0))

def display_upper_text_frame(text):
    text = text.upper()[:6]
    text_matrix = create_text_matrix(text, upper_font, spacing=1, value=1)
    text_width = len(text_matrix[0])
    start_x = max(0, (16 - text_width) // 2)
    y_offset = (9 - 5) // 2
    for row in range(5):
        for col in range(text_width):
            val = text_matrix[row][col]
            if val == 1:
                set_pixel_frame(start_x + col, y_offset + row, upper_text_color)
            else:
                set_pixel_frame(start_x + col, y_offset + row, (0, 0, 0))

def display_dynamic_upper_text_frame(text):
    y_offset = 2
    x_cursor = 0
    n = len(text)
    def char_width(ch):
        if ch == "1": return 2
        elif ch in "0123456789:": return 3
        elif ch == " ": return 1
        else: return len(upper_font.get(ch, upper_font[" "])[0])
    for i, ch in enumerate(text):
        if n == 5 and i in (3, 4): x_cursor += 1
        if n == 4 and i == 3:      x_cursor += 2
        if n == 6 and i == 5:      x_cursor += 1
        char_matrix = upper_font.get(ch, upper_font[" "])
        for row in range(5):
            for col in range(len(char_matrix[row])):
                if char_matrix[row][col] == 1:
                    set_pixel_frame(x_cursor + col, y_offset + row, upper_text_color)
        x_cursor += char_width(ch)

def rotate_matrix(matrix, angle):
    height = len(matrix); width = len(matrix[0])
    new_matrix = [[0 for _ in range(width)] for _ in range(height)]
    cx = (width - 1) / 2.0; cy = (height - 1) / 2.0
    rad = math.radians(angle)
    cos_val = math.cos(rad); sin_val = math.sin(rad)
    for y in range(height):
        for x in range(width):
            dx = x - cx; dy = y - cy
            src_x = dx * cos_val + dy * sin_val + cx
            src_y = -dx * sin_val + dy * cos_val + cy
            sx = int(round(src_x)); sy = int(round(src_y))
            new_matrix[y][x] = matrix[sy][sx] if 0 <= sx < width and 0 <= sy < height else 0
    return new_matrix

def display_upper_smile_anim_frame():
    smile = upper_symbols["smile"]
    rotated = rotate_matrix(smile, smile_anim_angle)
    clear_region_frame(0, smile_anim_y_offset, 16, 7)
    for y in range(7):
        for x in range(7):
            pos_x = smile_anim_x + x
            pos_y = smile_anim_y_offset + y
            if 0 <= pos_x < 16 and 0 <= pos_y < 9 and rotated[y][x] == 1:
                set_pixel_frame(pos_x, pos_y, smile_color)

def display_upper_heart1_anim_frame():
    heart = upper_symbols["♥"]
    rotated = rotate_matrix(heart, heart_anim_angle)
    heart_color = (0, int(255 * brightness), int(255 * brightness))
    clear_region_frame(0, heart_anim_y_offset, 16, 7)
    for y in range(7):
        for x in range(7):
            pos_x = heart_anim_x + x
            pos_y = heart_anim_y_offset + y
            if 0 <= pos_x < 16 and 0 <= pos_y < 9 and rotated[y][x] == 1:
                set_pixel_frame(pos_x, pos_y, heart_color)

def display_upper_heart2_anim_frame():
    heart = upper_symbols["♥2"]
    rotated = rotate_matrix(heart, heart_anim_angle)
    heart_color = (0, int(255 * brightness), 0)
    clear_region_frame(0, heart_anim_y_offset, 16, 7)
    for y in range(7):
        for x in range(7):
            pos_x = heart_anim_x + x
            pos_y = heart_anim_y_offset + y
            if 0 <= pos_x < 16 and 0 <= pos_y < 9 and rotated[y][x] == 1:
                set_pixel_frame(pos_x, pos_y, heart_color)

def display_upper_rose_anim_frame():
    rose = upper_symbols["rose"]
    clear_region_frame(0, rose_anim_y_offset, 16, 7)
    for y in range(7):
        for x in range(7):
            pos_x = rose_anim_x + x
            pos_y = rose_anim_y_offset + y
            if 0 <= pos_x < 16 and 0 <= pos_y < 9:
                if rose[y][x] == 1: set_pixel_frame(pos_x, pos_y, rose_leaves)
                elif rose[y][x] == 2: set_pixel_frame(pos_x, pos_y, rose_petals)

def display_upper_date_anim_frame():
    t = get_local_time()
    date_str = "{:02d}.{:02d}".format(t[2], t[1])
    day_part = date_str[:3]; month_part = date_str[3:]
    day_matrix = create_text_matrix(day_part, upper_font, spacing=1, value=1)
    month_matrix = create_text_matrix(month_part, upper_font, spacing=1, value=1)
    text_matrix = [day_matrix[row] + month_matrix[row] for row in range(5)]
    text_width = len(text_matrix[0])
    start_x = max(0, (16 - text_width) // 2)
    y_offset = (9 - 5) // 2
    for row in range(5):
        for col in range(text_width):
            if text_matrix[row][col] == 1:
                set_pixel_frame(start_x + col, y_offset + row, upper_text_color)
            else:
                set_pixel_frame(start_x + col, y_offset + row, (0, 0, 0))

def display_german_flag():
    # Farben im vorhandenen (GRB-)Schema:
    # Schwarz, Rot, Gold/Gelb
    black = (2, 2, 2)
    red   = (0, int(255*brightness), 0)
    gold  = (int(255*brightness), int(255*brightness), 0)

    height = 9
    width = 16
    stripe_h = height // 3  # 3 Pixel pro Streifen (9 Zeilen)

    for y in range(height):
        # oberes Drittel: schwarz
        if y < stripe_h:
            color = black
        # mittleres Drittel: rot
        elif y < 2 * stripe_h:
            color = red
        # unteres Drittel: gold
        else:
            color = gold

        for x in range(width):
            set_pixel_frame(x, y, color)


def display_brazil_flag():
    green  = (int(255*brightness), 0, 0)
    yellow = (int(255*brightness), int(255*brightness), 0)
    blue   = (0, 0, int(255*brightness))
    height = 9; width = 16
    center_x = width // 2; center_y = height // 2
    diamond_threshold = 6; circle_radius_sq = 2 * 2
    for y in range(height):
        for x in range(width):
            pixel_color = green
            if abs(x - center_x) + abs(y - center_y) <= diamond_threshold:
                pixel_color = yellow
            if (x - center_x) ** 2 + (y - center_y) ** 2 <= circle_radius_sq:
                pixel_color = blue
            set_pixel_frame(x, y, pixel_color)

def display_upper_cuckoo_frame():
    cuckoo = upper_symbols.get("cuckoo")
    if not cuckoo: return
    offset_x = (16 - 7) // 2; offset_y = (9 - 7) // 2
    clear_region_frame(0, 0, 16, 9)
    brown_color = (int(139 * brightness), int(69 * brightness), int(19 * brightness))
    for y in range(len(cuckoo)):
        for x in range(len(cuckoo[y])):
            if cuckoo[y][x] == 1:
                set_pixel_frame(offset_x + x, offset_y + y, brown_color)
    #commit_frame()

def display_upper_cuckoo_frame_big():
    clear_region_frame(0, 0, 16, 9)
    body_color = (int(69 * brightness), int(139 * brightness), int(19 * brightness))
    beak_color = (int(215 * brightness), int(255 * brightness), 0)
    eye_color  = (0, 0, 0)
    for y in range(9):
        for x in range(16):
            val = kuckuck[y][x]
            if val == 1: set_pixel_frame(x, y, body_color)
            elif val == 2: set_pixel_frame(x, y, beak_color)
            elif val == 3: set_pixel_frame(x, y, eye_color)
            else: set_pixel_frame(x, y, (0, 0, 0))
    #commit_frame()

# Vogelkopf-Symbol (9 Zeilen hoch, 16 Spalten breit)
vogelkopf = [
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
    [2, 2, 2, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
    [2, 2, 0, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [2, 2, 0, 0, 1, 1, 1, 1, 3, 1, 1, 1, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
]

def display_vogelkopf():
    clear_region_frame(0, 0, 16, 9)
    head_color = (int(69 * brightness), int(139 * brightness), int(19 * brightness))
    beak_color = (int(215 * brightness), int(255 * brightness), 0)
    eye_color  = (0, 0, 0)
    for y in range(9):
        for x in range(16):
            v = vogelkopf[y][x]
            if v == 1: set_pixel_frame(x, y, head_color)
            elif v == 2: set_pixel_frame(x, y, beak_color)
            elif v == 3: set_pixel_frame(x, y, eye_color)
            else: set_pixel_frame(x, y, (0, 0, 0))
    #commit_frame()

# ---- Audio ----
import array
def play_cuckoo_sound():
    pwm = machine.PWM(machine.Pin(3))
    pwm.freq(125000)
    pwm.duty_u16(0)
    with open("kuckuck.raw", "rb") as f:
        data = f.read()
    samples = array.array("B", data)
    for s in samples:
        centered = s - 128
        scaled   = centered << 8
        duty     = scaled + 32768
        pwm.duty_u16(duty)
        time.sleep_us(125)  # 8 kHz
    pwm.deinit()

# ---- Unterer Bereich ----
def display_lower_static_frame():
    t = get_local_time()
    stunde_str = "{:02d}".format(t[3])
    minute_str = "{:02d}".format(t[4])
    start_x = 1
    y_offset = 9 + ((8 - 5) // 2)
    x_offset = 0
    for ch in stunde_str:
        zeichne_symbol(ziffern[ch], start_x + x_offset - 1, y_offset)
        x_offset += 4
    x_offset -= 1
    for ch in minute_str:
        zeichne_symbol(ziffern[ch], start_x + x_offset + 1, y_offset)
        x_offset += 4

def display_lower_scrolling_frame():
    global scroll_offset, lower_combined_matrix, lower_scroll_max, lower_mode
    if lower_combined_matrix is not None:
        lower_y_offset = 9 + ((8 - 5) // 2)
        display_text_window(lower_combined_matrix, scroll_offset, lower_y_offset, 16)
        scroll_offset += 1
        if scroll_offset > lower_scroll_max:
            lower_mode = "static"

# ---- WLAN/AP ----
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Verbinde mit WLAN...")
        wlan.connect(ssid, password)
        timeout = 15
        while timeout:
            if wlan.isconnected(): break
            time.sleep(1); timeout -= 1
    if wlan.isconnected():
        print("WLAN verbunden:", wlan.ifconfig())
        return True
    else:
        print("WLAN-Verbindung fehlgeschlagen.")
        print("WLAN-Verbindung fehlgeschlagen. Starte Hotspot für WLAN-Konfiguration...")
        start_ap()
        serve_config_page()
        machine.reset()

def start_ap():
    wap = network.WLAN(network.AP_IF)
    wap.config(essid='PicoSetup', password='12345678')
    wap.active(True)
    print(wap.ifconfig())
    return wap

def serve_config_page():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket(); s.bind(addr); s.listen(1)
    print("Warte auf Konfigurationsanfrage unter", addr)
    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024).decode()
        if request:
            if "GET /set?" in request:
                try:
                    qs = request.split("GET /set?", 1)[1].split(" ", 1)[0]
                    params = qs.split("&")
                    ssid = ""; password = ""
                    for p in params:
                        k, v = p.split("=")
                        if k == "ssid": ssid = v
                        elif k == "password": password = v
                    ssid = ssid.replace('+', ' ')
                    password = password.replace('+', ' ')
                    with open("credentials.txt", "w") as f:
                        f.write(ssid + "\n" + password + "\n")
                    response = ("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                                "<html><body><h2>Credentials saved. Please restart the Pico.</h2></body></html>")
                    cl.send(response); cl.close()
                    print("Zugangsdaten gespeichert, bitte Pico neustarten.")
                    s.close()
                    break
                except Exception as e:
                    print("Fehler beim Verarbeiten:", e)
            else:
                html = """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE html>
<html>
<head>
    <title>WLAN Setup</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9;
               display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background-color: #fff; padding: 20px 40px; border-radius: 10px;
                     box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
                     max-width: 400px; width: 100%; }
        h2 { color: #4CAF50; margin-bottom: 20px; }
        form { display: flex; flex-direction: column; gap: 15px; }
        input[type="text"], input[type="password"] { padding: 10px; border: 1px solid #ccc;
                                                      border-radius: 5px; font-size: 14px; width: 100%; }
        input[type="submit"] { background-color: #4CAF50; color: white; border: none;
                               border-radius: 5px; padding: 10px; font-size: 16px; cursor: pointer;
                               transition: background-color 0.3s; }
        input[type="submit"]:hover { background-color: #45a049; }
    </style>
</head>
<body>
    <div class="container">
        <h2>WLAN-Zugangsdaten eingeben und anschliessend neu starten</h2>
        <form action="/set" method="get">
            SSID: <input type="text" name="ssid" required><br>
            Passwort: <input type="password" name="password" required><br>
            <input type="submit" value="Speichern">
        </form>
    </div>
</body>
</html>
"""
                cl.send(html); cl.close()
    return

# ---- Zeit/DST ----
def get_local_standard_time():
    return time.localtime(time.time() + 3600)

def last_sunday(year, month):
    day = 31
    t = [0,3,2,5,0,3,5,1,4,6,2,4]
    while (year + year//4 - year//100 + year//400 + t[month-1] + day) % 7 != 0:
        day -= 1
    return day

def is_dst(t):
    year, month, day, hour = t[0], t[1], t[2], t[3]
    if month < 3 or month > 10:
        return False
    elif 4 <= month <= 9:
        return True
    elif month == 3:
        dst_start_day = last_sunday(year, 3)
        return day > dst_start_day or (day == dst_start_day and hour >= 2)
    elif month == 10:
        dst_end_day = last_sunday(year, 10)
        return not (day < dst_end_day or (day == dst_end_day and hour < 3))

def get_local_time():
    if SIMULATE_TIME:
        return SIMULATED_TIME
    else:
        t_std = get_local_standard_time()
        if is_dst(t_std):
            return time.localtime(time.time() + 7200)
        else:
            return t_std

FRAME_DELAY_MS = 33
last_ntp_update_day = -1

def main():
    global lower_mode, last_minute, scroll_offset, lower_combined_matrix, lower_scroll_max
    global next_upper_update, current_upper_anim
    global heart_anim_x, heart_anim_y_offset, heart_anim_angle, rose_anim_x, rose_anim_y_offset
    global last_ntp_update_day, last_cuckoo_hour

    lower_mode = "static"
    last_minute = None
    scroll_offset = -16
    lower_combined_matrix = None
    lower_scroll_max = 0

    if "credentials.txt" in os.listdir():
        with open("credentials.txt", "r") as f:
            lines = f.readlines()
            ssid = lines[0].strip()
            password = lines[1].strip()
        print("Lade Zugangsdaten:", ssid, password)
        if connect_wifi(ssid, password):
            try:
                print("Hole Zeit vom NTP-Server...")
                ntptime.settime()
                print("Zeit gesetzt:", time.localtime())
                update_sun_times(49.444, 7.768)  # <— Koordinaten!
            except Exception as e:
                print("Fehler beim Einstellen der Zeit:", e)

            while True:
                clear_frame()
                clear_region_frame(0, 0, 16, 9)
                t = get_local_time()
                refresh_brightness_scale()

                # täglicher NTP-Sync um 03:00
                if t[3] == 3 and t[4] == 0 and t[2] != last_ntp_update_day:
                    try:
                        ntptime.settime()
                        print("NTP-Update um 3:00 Uhr durchgeführt.")
                        last_ntp_update_day = t[2]
                    except Exception as e:
                        print("Fehler beim NTP-Update:", e)

                # direkt danach Sonnenzeiten neu laden (03:01)
                if t[3] == 3 and t[4] == 1 and t[2] == last_ntp_update_day:
                    update_sun_times(49.444, 7.768)

                # Kuckuck zur vollen Stunde (Sek. 2..4)
                if t[4] == 0 and 2 <= t[5] <= 4:
                    if last_cuckoo_hour != t[3]:
                        last_cuckoo_hour = t[3]
                        hour_12 = t[3] % 12
                        if hour_12 == 0: hour_12 = 12
                        for _ in range(hour_12):
                            display_upper_cuckoo_frame()
                            # display_upper_cuckoo_frame_big()
                            # display_vogelkopf()
                            play_cuckoo_sound()
                            time.sleep(0.5)
                            clear_region_frame(0, 0, 16, 9)
                            commit_frame()

                # Oberer Bereich: Viertel-/Halb-/Dreiviertel-Anzeige oder Animation
                x = t[3] % 12
                current_minute = t[4]
                if current_minute in [15, 30, 45] and 0 <= x < 12:
                    if current_minute == 15:
                        dynamic_upper_text = "1:4 " + str(x+1)
                    elif current_minute == 30:
                        dynamic_upper_text = "1:2 " + str(x+1)
                    elif current_minute == 45:
                        dynamic_upper_text = "3:4" + str(x+1)
                    display_dynamic_upper_text_frame(dynamic_upper_text)
                else:
                    current = time.ticks_ms()
                    if time.ticks_diff(current, next_upper_update) >= 0:
                        current_upper_anim = random.choice(["heart1", "heart2", "rose", "smile", "date", "flag","flag_de"])
                        if current_upper_anim in ["heart1", "heart2", "smile"]:
                            heart_anim_x = (heart_anim_x + 1) % 10
                            heart_anim_y_offset += random.choice([-1, 0, 1])
                            heart_anim_y_offset = max(0, min(heart_anim_y_offset, 2))
                            heart_anim_angle = random.choice([0, 90, 180, -90])
                        elif current_upper_anim == "rose":
                            rose_anim_x += random.choice([-1, 0, 1])
                            rose_anim_y_offset += random.choice([-1, 0, 1])
                            rose_anim_x = max(0, min(rose_anim_x, 9))
                            rose_anim_y_offset = max(0, min(rose_anim_y_offset, 2))
                        next_upper_update = current + upper_anim_delay

                    if current_upper_anim == "heart1":
                        display_upper_heart1_anim_frame()
                    elif current_upper_anim == "heart2":
                        display_upper_heart2_anim_frame()
                    elif current_upper_anim == "rose":
                        display_upper_rose_anim_frame()
                    elif current_upper_anim == "smile":
                        display_upper_smile_anim_frame()
                    elif current_upper_anim == "date":
                        display_upper_date_anim_frame()
                    elif current_upper_anim == "flag":
                        display_brazil_flag()
                    elif current_upper_anim == "flag_de":
                        display_german_flag()

                # Unterer Bereich: Uhr + Lauftext (jede Minute neu)
                current_time = get_local_time()
                current_minute = current_time[4]
                if last_minute is None or current_minute != last_minute:
                    lower_mode = "scrolling"
                    scroll_offset = -16
                    time_str = "{:02d}:{:02d}".format(current_time[3], current_time[4])
                    time_matrix = create_text_matrix(time_str, ziffern, spacing=1, value=1)
                    msg = random.choice(messages)
                    if callable(msg): msg = msg()
                    appended_text = " " + msg
                    appended_matrix = create_text_matrix(appended_text, letters, spacing=1, value=2)
                    lower_combined_matrix = combine_matrices(time_matrix, appended_matrix, spacing=1)
                    lower_scroll_max = len(lower_combined_matrix[0])
                    last_minute = current_minute

                if lower_mode == "scrolling":
                    clear_region_frame(0, 9, 16, 5)
                    display_lower_scrolling_frame()
                else:
                    display_lower_static_frame()

                commit_frame()
                time.sleep(0.07)

                if lower_mode == "scrolling" and scroll_offset > lower_scroll_max:
                    lower_mode = "static"
        else:
            print("WLAN-Verbindung fehlgeschlagen.")
    else:
        print("credentials.txt nicht gefunden. Starte Hotspot für WLAN-Konfiguration...")
        start_ap()
        serve_config_page()
        machine.reset()

main()

