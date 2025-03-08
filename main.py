import network, ntptime, socket, os, time, machine, math, random
from neopixel import Neopixel

# ----------------------- Neopixel Setup -----------------------------
anzahl_LEDs = 256         # 16×16 LED-Matrix
pin = 1                   # z.B. GP2 des Pico W
pixels = Neopixel(anzahl_LEDs, 1, pin)

# ----------------------- Double Buffering -----------------------------
led_state = [(0, 0, 0) for _ in range(anzahl_LEDs)]
frame = [(0, 0, 0) for _ in range(anzahl_LEDs)]

# ----------------------- Einstellungen -----------------------------
brightness = 0.05
base_color = (0, 0, 100)  # Basisfarbe (für den Zeitteil)
text_farbe = ( int(base_color[0]*brightness),
               int(base_color[1]*brightness),
               int(base_color[2]*brightness) )
red_text = (0, int(255*brightness), 0)

# Obere Animation: Wähle, ob Rose oder Herz angezeigt wird.
show_rose = True   # (Diese Variable wird am Ende jedes Zyklus umgeschaltet.)

# Farben für die Rose (Farbtausch):
# Pixel mit Wert 1 (ursprünglich "Petals") werden grün (Blätter)
# Pixel mit Wert 2 (ursprünglich "Leaves") werden rot (Blüten)
rose_petals = (int(255*brightness), 0, 0)   # Rot
rose_leaves = (0, int(255*brightness), 0)    # Grün

# ----------------------- Font-Definitionen -----------------------------
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
    " ": [[0,0],[0,0],[0,0],[0,0],[0,0]]
}

letters = {
    "I": [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
    "C": [[1,1,1],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
    "H": [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    "L": [[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
    "E": [[1,1,1],[1,0,0],[1,1,1],[1,0,0],[1,1,1]],
    "B": [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,1,0]],
    "D": [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
    "!": [[1],[1],[1],[0],[1]],
    " ": [[0],[0],[0],[0],[0]]
}

# Obere Symbole (Herz und Rose)
upper_symbols = {
    "♥": [
        [0,1,0,0,0,1,0],
        [1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1],
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

# ----------------------- Globale Variablen für Animation -----------------------------
# Für das Herz (animiert)
heart_anim_x = 0
heart_anim_y_offset = 1
heart_anim_angle = 0
last_heart_update = time.time()

# Für die Rose (ohne Rotation, nur Farbtausch und zufällige Bewegung)
rose_anim_x = 4
rose_anim_y_offset = 1

# Unterer Bereich:
# use_scrolling_lower: True -> Laufschrift, False -> statische Anzeige
use_scrolling_lower = False  
lower_mode = "static"   # "static" oder "scrolling"
last_minute = None      # Zur Erkennung von Minutenwechsel
scroll_offset = -16     # Startwert für die Laufschrift
lower_combined_matrix = None  # Kombinierte Matrix (Zeit + Zusatztext)
lower_scroll_max = 0           # Breite der kombinierten Matrix

# ----------------------- Hilfsfunktionen für Double Buffering -----------------------------
def xy_to_index(x, y):
    if y % 2 == 0:
        return y * 16 + (15 - x)
    else:
        return y * 16 + x

def set_pixel_frame(x, y, farbe):
    if 0 <= x < 16 and 0 <= y < 16:
        index = xy_to_index(x, y)
        global frame
        frame[index] = farbe

def clear_frame():
    global frame
    # Wir löschen nicht den gesamten Frame, sondern arbeiten gezielt im oberen Bereich.
    # Für den unteren Bereich (statisch) wird nur bei Minutenwechsel neu gezeichnet.
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

# ----------------------- Hilfsfunktionen für Text -----------------------------
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
    combined = []
    for row in range(5):
        combined.append(matrix1[row] + [0] * spacing + matrix2[row])
    return combined

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

# ----------------------- Herz-Animation -----------------------------
def rotate_matrix(matrix, angle):
    height = len(matrix)
    width = len(matrix[0])
    new_matrix = [[0 for _ in range(width)] for _ in range(height)]
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    rad = math.radians(angle)
    cos_val = math.cos(rad)
    sin_val = math.sin(rad)
    for y in range(height):
        for x in range(width):
            dx = x - cx
            dy = y - cy
            src_x = dx * cos_val + dy * sin_val + cx
            src_y = -dx * sin_val + dy * cos_val + cy
            src_x_round = int(round(src_x))
            src_y_round = int(round(src_y))
            if 0 <= src_x_round < width and 0 <= src_y_round < height:
                new_matrix[y][x] = matrix[src_y_round][src_x_round]
            else:
                new_matrix[y][x] = 0
    return new_matrix

def display_upper_heart_anim_frame():
    global heart_anim_x, heart_anim_y_offset, heart_anim_angle, last_heart_update
    current = time.time()
    if current - last_heart_update >= 0.5:
        heart_anim_x = (heart_anim_x + 4) % 10
        heart_anim_y_offset += random.choice([-1, 0, 1])
        heart_anim_y_offset = max(0, min(heart_anim_y_offset, 2))
        heart_anim_angle = (heart_anim_angle + 45) % 360
        last_heart_update = current
    heart = upper_symbols["♥"]
    rotated = rotate_matrix(heart, heart_anim_angle)
    heart_color = (0, int(255 * brightness), 0)
    clear_region_frame(0, heart_anim_y_offset, 16, 7)
    for y in range(7):
        for x in range(7):
            pos_x = heart_anim_x + x
            pos_y = heart_anim_y_offset + y
            if 0 <= pos_x < 16 and 0 <= pos_y < 9:
                if rotated[y][x] == 1:
                    set_pixel_frame(pos_x, pos_y, heart_color)

# ----------------------- Rose-Animation (ohne Rotation, nur Farbtausch) -----------------------------
def display_upper_rose_anim_frame():
    global rose_anim_x, rose_anim_y_offset, last_heart_update
    current = time.time()
    if current - last_heart_update >= 0.5:
        rose_anim_x += random.choice([-1, 0, 1])
        rose_anim_y_offset += random.choice([-1, 0, 1])
        rose_anim_x = max(0, min(rose_anim_x, 9))
        rose_anim_y_offset = max(0, min(rose_anim_y_offset, 2))
        last_heart_update = current
    rose = upper_symbols["rose"]
    clear_region_frame(0, rose_anim_y_offset, 16, 7)
    for y in range(7):
        for x in range(7):
            pos_x = rose_anim_x + x
            pos_y = rose_anim_y_offset + y
            if 0 <= pos_x < 16 and 0 <= pos_y < 9:
                if rose[y][x] == 1:
                    set_pixel_frame(pos_x, pos_y, rose_leaves)
                elif rose[y][x] == 2:
                    set_pixel_frame(pos_x, pos_y, rose_petals)

# ----------------------- Unterer Bereich: Zeitanzeige / Laufschrift -----------------------------
def display_lower_static_frame():
    # Zeichnet die statische Uhrzeitanzeige in den Zeilen 9–13
    t = get_local_time()
    stunde = t[3] if t[3] != 0 else 12
    if stunde > 12:
        stunde -= 12
    stunde_str = "{:02d}".format(stunde)
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

def update_lower_matrix():
    global lower_combined_matrix, lower_scroll_max, scroll_offset
    t = get_local_time()
    stunde = t[3] if t[3] != 0 else 12
    if stunde > 12:
        stunde -= 12
    time_str = "{:02d}:{:02d}".format(stunde, t[4])
    time_matrix = create_text_matrix(time_str, ziffern, spacing=1, value=1)
    appended_text = " ICH LIEBE DICH !"
    appended_matrix = create_text_matrix(appended_text, letters, spacing=1, value=2)
    lower_combined_matrix = combine_matrices(time_matrix, appended_matrix, spacing=1)
    lower_scroll_max = len(lower_combined_matrix[0])
    scroll_offset = -16

# ----------------------- WLAN-Funktionen -----------------------------
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Verbinde mit WLAN...")
        wlan.connect(ssid, password)
        timeout = 15
        while timeout:
            if wlan.isconnected():
                break
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        print("WLAN verbunden:", wlan.ifconfig())
        return True
    else:
        print("WLAN-Verbindung fehlgeschlagen.")
        return False

def start_ap():
    wap = network.WLAN(network.AP_IF)
    wap.config(essid='PicoSetup', password='12345678')
    wap.active(True)
    print(wap.ifconfig())
    return wap

def serve_config_page():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
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
                    ssid = ""
                    password = ""
                    for p in params:
                        k, v = p.split("=")
                        if k == "ssid":
                            ssid = v
                        elif k == "password":
                            password = v
                    ssid = ssid.replace('+', ' ')
                    password = password.replace('+', ' ')
                    with open("credentials.txt", "w") as f:
                        f.write(ssid + "\n" + password + "\n")
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"\
                               "<html><body><h2>Credentials saved. Please restart the Pico.</h2></body></html>"
                    cl.send(response)
                    cl.close()
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
                cl.send(html)
                cl.close()
    return

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
    t_std = get_local_standard_time()
    if is_dst(t_std):
        return time.localtime(time.time() + 7200)
    else:
        return t_std

# ----------------------- Hauptschleife mit fester Frame-Rate -----------------------------
FRAME_DELAY_MS = 33  # ca. 30 FPS

def main():
    global last_heart_update, show_rose, scroll_offset, lower_mode, last_minute, lower_combined_matrix, lower_scroll_max
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
            except Exception as e:
                print("Fehler beim Einstellen der Zeit:", e)
            last_heart_update = time.time()
            # Beim Minutenwechsel: aktualisiere den unteren Bereich und starte die Laufschrift
            while True:
                clear_frame()
                # Aktualisiere nur den oberen Bereich (Zeilen 0–8)
                clear_region_frame(0, 0, 16, 9)
                if show_rose:
                    display_upper_rose_anim_frame()
                else:
                    display_upper_heart_anim_frame()
                # Prüfe, ob sich die Minute geändert hat:
                t = get_local_time()
                current_minute = t[4]
                if last_minute is None or current_minute != last_minute:
                    lower_mode = "scrolling"
                    scroll_offset = -16
                    # Erstelle die kombinierte Matrix für die Laufschrift
                    time_str = "{:02d}:{:02d}".format(t[3] if t[3]!=0 else 12, t[4])
                    time_matrix = create_text_matrix(time_str, ziffern, spacing=1, value=1)
                    appended_text = " ICH LIEBE DICH !"
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
                time.sleep(0.033)  # ca. 30 FPS
                if lower_mode == "scrolling" and scroll_offset > lower_scroll_max:
                    lower_mode = "static"
                # Optional: Obere Animation umschalten, falls gewünscht:
                # show_rose = not(show_rose)
        else:
            print("WLAN-Verbindung fehlgeschlagen.")
    else:
        print("credentials.txt nicht gefunden. Starte Hotspot für WLAN-Konfiguration...")
        start_ap()
        serve_config_page()
        machine.reset()

main()
