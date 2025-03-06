import network, ntptime, socket, os, time, machine
from neopixel import Neopixel

# ----------------------- Neopixel Setup -----------------------------
anzahl_LEDs = 256         # 16×16 LED-Matrix
pin = 1                   # z.B. GP2 des Pico W
pixels = Neopixel(anzahl_LEDs, 1, pin)

# Helligkeit: 10%
brightness = 0.1
base_color = (0, 0, 100)  # (g, r, b) – Basisfarbe für den Zeitteil
text_farbe = (
    int(base_color[0] * brightness),
    int(base_color[1] * brightness),
    int(base_color[2] * brightness)
)
# Für den angehängten Text in Rot (im GRB-Format: hier (0,255,0))
red_text = (0, int(255 * brightness), 0)

# ----------------------- Font-Definitionen -----------------------------
# Zahlen (3×5 Format) für den Zeitteil
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

# Buchstaben (3×5 Format) für den angehängten Text
letters = {
    "I": [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
    "C": [[1,1,1],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
    "H": [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    "L": [[1,0,0],[1,0,0],[1,0,0],[1,0,0],[1,1,1]],
    "E": [[1,1,1],[1,0,0],[1,1,1],[1,0,0],[1,1,1]],
    "B": [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,1,0]],
    "D": [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
    "!": [[0,1,0],[0,1,0],[0,1,0],[0,0,0],[0,1,0]],
    " ": [[0],[0],[0],[0],[0]]
}

# Für den oberen Bereich: Ein Herz im 7×7 Format
upper_symbols = {
    "♥": [
        [0,1,0,0,0,1,0],
        [1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1],
        [0,1,1,1,1,1,0],
        [0,0,1,1,1,0,0],
        [0,0,0,1,0,0,0]
    ]
}

# ----------------------- Mapping-Funktion -----------------------------
def set_pixel(x, y, farbe):
    # Serpentine-Mapping: In geraden Zeilen (y % 2 == 0) läuft die Reihe von rechts nach links.
    if y % 2 == 0:
        index = y * 16 + (15 - x)
    else:
        index = y * 16 + x
    pixels.set_pixel(index, farbe)

# ----------------------- Hilfsfunktionen für Text ------------------------
def create_text_matrix(text, font_dict, spacing=1, value=1):
    """Erzeugt eine 5-zeilige Matrix aus Text, wobei jedes 'an'-Pixel den Wert 'value' erhält."""
    matrix = [[] for _ in range(5)]
    for i, ch in enumerate(text):
        char_matrix = font_dict.get(ch, font_dict[" "])
        for row in range(5):
            for pixel in char_matrix[row]:
                matrix[row].append(value if pixel==1 else 0)
        if i != len(text) - 1:
            for row in range(5):
                matrix[row].extend([0]*spacing)
    return matrix

def combine_matrices(matrix1, matrix2, spacing=1):
    """Hängt zwei Matrizen zeilenweise mit einem Spaltenabstand zusammen."""
    combined = []
    for row in range(5):
        combined.append(matrix1[row] + [0]*spacing + matrix2[row])
    return combined

def display_text_window(text_matrix, window_x, y_offset, window_width):
    """Zeigt ein Fenster der Textmatrix an, wobei 1 in Standardfarbe und 2 in Rot gezeichnet wird."""
    for row in range(5):
        for col in range(window_width):
            text_col = window_x + col
            if 0 <= text_col < len(text_matrix[row]):
                val = text_matrix[row][text_col]
                if val == 1:
                    set_pixel(col, y_offset + row, text_farbe)
                elif val == 2:
                    set_pixel(col, y_offset + row, red_text)
                else:
                    set_pixel(col, y_offset + row, (0,0,0))
            else:
                set_pixel(col, y_offset + row, (0,0,0))
    pixels.show()

def zeichne_symbol(symbol, start_x, start_y):
    """Zeichnet ein einzelnes Symbol in der Standardfarbe."""
    for y in range(len(symbol)):
        for x in range(len(symbol[y])):
            if symbol[y][x] == 1:
                set_pixel(start_x + x, start_y + y, text_farbe)
            else:
                set_pixel(start_x + x, start_y + y, (0,0,0))
    pixels.show()

# ----------------------- Anzeige im oberen Bereich (Herz) -----------------------
def display_upper_heart():
    """Zeigt ein zentriertes Herz (7×7) in der oberen Hälfte an."""
    heart = upper_symbols["♥"]
    heart_color = (0, int(255 * brightness), 0)  # Reines Rot (GRB: (0,255,0))
    start_x = (16 - 7) // 2  # 4
    start_y = 1              # leicht nach unten
    for y in range(7):
        for x in range(7):
            if heart[y][x] == 1:
                set_pixel(start_x + x, start_y + y, heart_color)
            else:
                set_pixel(start_x + x, start_y + y, (0,0,0))
    pixels.show()

# ----------------------- Anzeige im unteren Bereich (statisch) -----------------------
def display_lower_static():
    """Zeigt die Uhrzeit statisch im Format 'HHMM' an (Stunden links, Minuten rechts)."""
    t = time.localtime()
    stunde = t[3] if t[3] != 0 else 12
    if stunde > 12:
        stunde -= 12
    stunde_str = "{:02d}".format(stunde)
    minute_str = "{:02d}".format(t[4])
    start_x = 1
    y_offset = 8 + ((8 - 5) // 2)  # z.B. Zeile 9
    x_offset = 0
    for ch in stunde_str:
        zeichne_symbol(ziffern[ch], start_x + x_offset - 1, y_offset)
        x_offset += 4
    x_offset -= 1
    for ch in minute_str:
        zeichne_symbol(ziffern[ch], start_x + x_offset + 1, y_offset)
        x_offset += 4

# ----------------------- Anzeige im unteren Bereich (einmaliger Scroll-Durchlauf) -----------------------
def display_lower_scrolling_once():
    """
    Führt einen einmaligen kompletten Laufschriftdurchlauf durch,
    bestehend aus der Uhrzeit im Format "HH:MM" (Wert 1)
    und dem Text " ICH LIEBE DICH <3" (Wert 2).
    """
    t = time.localtime()
    stunde = t[3] if t[3] != 0 else 12
    if stunde > 12:
        stunde -= 12
    time_str = "{:02d}:{:02d}".format(stunde, t[4])
    time_matrix = create_text_matrix(time_str, ziffern, spacing=1, value=1)
    appended_text = " ICH LIEBE DICH <3"
    appended_matrix = create_text_matrix(appended_text, letters, spacing=1, value=2)
    combined_matrix = combine_matrices(time_matrix, appended_matrix, spacing=1)
    text_width = len(combined_matrix[0])
    y_offset = 8 + ((8 - 5) // 2)
    # Scroll von rechts (offset = -16) bis der Text komplett links verschwunden ist
    for offset in range(-16, text_width + 1):
        display_text_window(combined_matrix, offset, y_offset, 16)
        time.sleep(0.1)

# ----------------------- WLAN-Funktionen -----------------------------
def connect_wifi(ssid, password):
    """Verbindet den PicoW im STA-Modus mit dem WLAN."""
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
    """Startet einen Hotspot (AP-Modus) für die Konfiguration."""
    # WAP-Betrieb
    wap = network.WLAN(network.AP_IF)

    # WAP-Konfiguration
    wap.config(essid='PicoSetup', password='12345678')

    # WLAN-Interface aktivieren
    wap.active(True)

    # Ausgabe der Netzwerk-Konfiguration
    print(wap.ifconfig())
    return wap

def serve_config_page():
    """Startet einen einfachen Webserver, der ein Formular zur Eingabe von SSID und Passwort bereitstellt."""
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
            # Einfache Auswertung des GET-Requests:
            if "GET /set?" in request:
                try:
                    qs = request.split("GET /set?", 1)[1].split(" ", 1)[0]
                    params = qs.split("&")
                    ssid = ""
                    password = ""
                    for p in params:
                        k,v = p.split("=")
                        if k=="ssid":
                            ssid = v
                        elif k=="password":
                            password = v
                    ssid = ssid.replace('+', ' ')
                    password = password.replace('+', ' ')
                    # Speichere die Zugangsdaten:
                    with open("credentials.txt", "w") as f:
                        f.write(ssid + "\n" + password + "\n")
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" \
                               "<html><body><h2>Credentials saved. Please restart the Pico.</h2></body></html>"
                    cl.send(response)
                    cl.close()
                    print("Zugangsdaten gespeichert, bitte Pico neustarten.")
                    s.close()
                    break
                except Exception as e:
                    print("Fehler beim Verarbeiten:", e)
            else:
                # Sende Konfigurationsseite:
                html = """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE html>
<html>
<head>
    <title>WLAN Setup</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background-color: #fff;
            padding: 20px 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        h2 {
            color: #4CAF50;
            margin-bottom: 20px;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        input[type="text"],
        input[type="password"] {
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 14px;
            width: 100%;
        }
        input[type="submit"] {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        input[type="submit"]:hover {
            background-color: #45a049;
        }
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

# ----------------------- Main -----------------------------
def main():
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
            # Nun starte den Uhr-Display-Modus
            last_minute = None
            while True:
                t = time.localtime()
                current_minute = t[4]
                display_upper_heart()
                if current_minute != last_minute:
                    display_lower_scrolling_once()
                    last_minute = current_minute
                else:
                    display_lower_static()
                time.sleep(0.1)
        else:
            print("WLAN-Verbindung fehlgeschlagen.")
    else:
        print("credentials.txt nicht gefunden. Starte Hotspot für WLAN-Konfiguration...")
        start_ap()
        serve_config_page()
        # Nach erfolgreicher Konfiguration muss der Pico neu gestartet werden.
        machine.reset()

main()

