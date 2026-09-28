"""互動式二維不可壓縮流體模擬。

本程式用 Pygame 顯示、NumPy 計算 Navier–Stokes 方程的數值近似。
每個固定時間步先讓速度場沿自身流動方向平流，再計算黏性擴散；
最後解壓力並扣除壓力梯度，使速度場的散度接近零。
染料隨流體移動並緩慢淡出，只用來觀察流動，不會反過來改變速度。
染料模式會保留每次下筆時的顏色；筆刷色相隨時間緩慢循環。
初始流場可選泰勒–格林渦流加微小擾動，或週期式柏林噪聲渦流。

畫面與操作：
    流體顯示區固定 768×768 像素，右側是 320 像素的資訊面板。
    [ / ]：切換 32、64、128、192 的方形模擬網格；視窗大小不變，
           切換時重新建立流場。DEFAULT_RESOLUTION 設定起始解析度。
    C：循環切換顏色代表的速度大小、相對壓力、渦度、染料濃度。
    X：循環切換箭頭代表的速度、壓力力 -∇p、染料濃度梯度或不顯示。
    I：切換兩種初始流場並重設；R：重設目前選擇的初始流場。
    滑鼠左鍵拖曳：注入動量與染料；右鍵點擊／拖曳：只注入染料。
    小船會隨當地流速漂移；W／上前進、S／下倒退，
    A／左與 D／右轉向，按鍵期間持續注入染料。
    +／-：調整船速。
    空白鍵：暫停／繼續；Esc：離開。

主要可調參數：
    INITIAL_FLOW_SPEED：初始渦流速度。
    INITIAL_PERTURBATION：第一種流場的微擾強度（相對於初始速度）。
    PERLIN_CELLS、PERLIN_OCTAVES、PERLIN_SEED：第二種流場的噪聲尺度與種子。
    VISCOSITY：黏性；越大，小尺度渦流消散越快。程式會依解析度
               平方縮放，讓不同網格呈現相近的物理效果。
    MOUSE_FORCE：左鍵拖曳施加動量的強度；MAX_SPEED：速度上限。
    BRUSH_RADIUS：筆刷範圍；DYE_STRENGTH：每次注入的染料量。
    DYE_FADE_RATE：染料淡出速度，不是流體黏性。
    DYE_COLOR_PERIOD：筆刷顏色變化一輪所需秒數。
    DIVERGENCE_FPS：右側散度 RMS 數值每秒重新計算的次數。
    BOAT_SPEEDS：小船可選駕駛速度，單位是畫面像素／秒。
    BOAT_TURN_SPEED：小船每秒轉向的弧度數。
    BOAT_START：小船啟動與重設的位置。
    SIM_DT：每次物理計算的固定時間間隔。

這是週期邊界：流出一側會從另一側回來；不是有牆壁或自由液面的水槽。
模型沒有表面張力或獨立的密度參數。壓力只定義到一個任意常數，
所以顯示的是相對壓力。速度、壓力、渦度色階會依當前影格縮放；
染料色階固定為 0～1。
"""

import math

import numpy as np
import pygame


# 可調參數：解析度、視窗與流體／滑鼠互動
RESOLUTIONS = (32, 64, 128, 192)
DEFAULT_RESOLUTION = 128
DEFAULT_INITIAL_STATE = 0
VIEW_PIXELS = 768
PANEL_PIXELS = 320
SIM_DT = 1.0 / 60.0
INITIAL_FLOW_SPEED = 44.0
INITIAL_PERTURBATION = 0.02
PERLIN_CELLS = 4
PERLIN_OCTAVES = 3
PERLIN_SEED = hash("Navier-Stokes interactive fluid simulator")
VISCOSITY = 0.4  # grid-cell squared per second at the default resolution
MOUSE_FORCE = 3.0
MAX_SPEED = 70.0
BRUSH_RADIUS = 2.5
DYE_STRENGTH = 0.50
DYE_FADE_RATE = 0.06
DYE_COLOR_PERIOD = 4.0
DIVERGENCE_FPS = 6.0
BOAT_SPEEDS = (120.0, 180.0, 270.0, 400.0, 600.0, 900.0, 1350.0, 2000.0)
BOAT_TURN_SPEED = math.pi
BOAT_START = (VIEW_PIXELS * 0.35, VIEW_PIXELS * 0.5)

WINDOW_SIZE = (VIEW_PIXELS + PANEL_PIXELS, VIEW_PIXELS)

COLOR_MODES = ("速度大小", "相對壓力", "渦度", "染料濃度")
ARROW_MODES = ("速度方向", "壓力力方向", "染料梯度", "關閉")
INITIAL_STATES = ("泰勒–格林 + 微擾", "柏林噪聲渦流")


def palette(values, colors):
    """Map values in [0, 1] through a short RGB color ramp."""
    stops = np.asarray(colors, dtype=np.float64)
    scaled = np.clip(values, 0.0, 1.0) * (len(stops) - 1)
    index = np.minimum(scaled.astype(np.int32), len(stops) - 2)
    fraction = (scaled - index)[..., None]
    return (stops[index] * (1.0 - fraction) + stops[index + 1] * fraction).astype(
        np.uint8
    )


def current_brush_hue():
    phase = 2.0 * math.pi * pygame.time.get_ticks() / (1000.0 * DYE_COLOR_PERIOD)
    return 0.5 + 0.5 * math.sin(phase)


def periodic_perlin(n, cells, seed):
    """Tileable 2-D gradient noise using Perlin's smooth fade curve."""
    rng = np.random.default_rng(seed % (1 << 64))  # hash() can be negative.
    angles = rng.uniform(0.0, 2.0 * math.pi, (cells, cells))
    gradient_x = np.cos(angles)
    gradient_y = np.sin(angles)
    y, x = np.indices((n, n), dtype=np.float64)
    grid_x = x * cells / n
    grid_y = y * cells / n
    floor_x = np.floor(grid_x)
    floor_y = np.floor(grid_y)
    local_x = grid_x - floor_x
    local_y = grid_y - floor_y
    x0 = floor_x.astype(np.int32) % cells
    y0 = floor_y.astype(np.int32) % cells
    x1 = (x0 + 1) % cells
    y1 = (y0 + 1) % cells

    def corner(ix, iy, dx, dy):
        return gradient_x[iy, ix] * dx + gradient_y[iy, ix] * dy

    lower_left = corner(x0, y0, local_x, local_y)
    lower_right = corner(x1, y0, local_x - 1.0, local_y)
    upper_left = corner(x0, y1, local_x, local_y - 1.0)
    upper_right = corner(x1, y1, local_x - 1.0, local_y - 1.0)
    fade_x = local_x ** 3 * (local_x * (local_x * 6.0 - 15.0) + 10.0)
    fade_y = local_y ** 3 * (local_y * (local_y * 6.0 - 15.0) + 10.0)
    lower = lower_left + fade_x * (lower_right - lower_left)
    upper = upper_left + fade_x * (upper_right - upper_left)
    return lower + fade_y * (upper - lower)


def perlin_stream(n, seed):
    """Combine periodic Perlin octaves into a smooth streamfunction."""
    stream = np.zeros((n, n), dtype=np.float64)
    for octave in range(PERLIN_OCTAVES):
        stream += (0.5 ** octave) * periodic_perlin(
            n, PERLIN_CELLS * (2 ** octave), seed + octave
        )
    return stream


class Fluid:
    """Cell-centered velocity with periodic spectral diffusion and projection."""

    def __init__(self, resolution=DEFAULT_RESOLUTION,
                 initial_state=DEFAULT_INITIAL_STATE):
        self.n = resolution
        self.scale = resolution / DEFAULT_RESOLUTION
        self.initial_state = initial_state
        self.y, self.x = np.indices((self.n, self.n), dtype=np.float64)
        frequency = 2.0 * math.pi * np.fft.fftfreq(self.n)
        diffusion_kx, diffusion_ky = np.meshgrid(frequency, frequency)
        self.k2 = diffusion_kx * diffusion_kx + diffusion_ky * diffusion_ky
        derivative_frequency = frequency.copy()
        derivative_frequency[self.n // 2] = 0.0  # Real-grid Nyquist derivative.
        self.kx, self.ky = np.meshgrid(derivative_frequency, derivative_frequency)
        projection_k2 = self.kx * self.kx + self.ky * self.ky
        self.zero_mode = projection_k2 == 0.0
        self.safe_k2 = np.where(self.zero_mode, 1.0, projection_k2)
        self.reset()

    def _noise_velocity(self, seed):
        """Take the curl of Perlin noise so the velocity starts divergence-free."""
        stream_hat = np.fft.fft2(perlin_stream(self.n, seed))
        u = np.fft.ifft2(1j * self.ky * stream_hat).real
        v = np.fft.ifft2(-1j * self.kx * stream_hat).real
        rms = float(np.sqrt(np.mean(u * u + v * v)))
        return u / rms, v / rms

    def reset(self):
        """Build the selected initial flow and two visible dye clouds."""
        speed = INITIAL_FLOW_SPEED * self.scale
        if self.initial_state == 0:
            angle_x = 2.0 * math.pi * self.x / self.n
            angle_y = 2.0 * math.pi * self.y / self.n
            noise_u, noise_v = self._noise_velocity(PERLIN_SEED + hash("Why U looking at me???"))
            self.u = (speed * np.sin(angle_x) * np.cos(angle_y)
                      + speed * INITIAL_PERTURBATION * noise_u)
            self.v = (-speed * np.cos(angle_x) * np.sin(angle_y)
                      + speed * INITIAL_PERTURBATION * noise_v)
        else:
            noise_u, noise_v = self._noise_velocity(PERLIN_SEED)
            self.u = speed / math.sqrt(2.0) * noise_u
            self.v = speed / math.sqrt(2.0) * noise_v
        self.dye = np.clip(
            self._spot(20.0 * self.scale, 24.0 * self.scale, 7.0 * self.scale)
            + self._spot(44.0 * self.scale, 40.0 * self.scale, 7.0 * self.scale),
            0.0,
            1.0,
        )
        self.dye_hue_mass = 0.5 * self.dye
        self.pressure = np.zeros((self.n, self.n), dtype=np.float64)
        self.divergence_rms = 0.0

    def _spot(self, cx, cy, radius):
        """Periodic Gaussian brush, so sources wrap just like the flow."""
        dx = (self.x - cx + self.n / 2.0) % self.n - self.n / 2.0
        dy = (self.y - cy + self.n / 2.0) % self.n - self.n / 2.0
        return np.exp(-(dx * dx + dy * dy) / (2.0 * radius * radius))

    def inject(self, x, y, drag_x, drag_y, push, brush_hue):
        """Paint time-colored dye; optionally add mouse-drag momentum."""
        brush = self._spot(x, y, BRUSH_RADIUS * self.scale)
        if push:
            self.u += MOUSE_FORCE * drag_x * brush
            self.v += MOUSE_FORCE * drag_y * brush
            np.clip(self.u, -MAX_SPEED * self.scale, MAX_SPEED * self.scale, out=self.u)
            np.clip(self.v, -MAX_SPEED * self.scale, MAX_SPEED * self.scale, out=self.v)
        amount = DYE_STRENGTH * brush
        total = self.dye + amount
        hue = (self.dye_hue_mass + amount * brush_hue) / np.maximum(total, 1e-12)
        self.dye = np.minimum(total, 1.0)
        self.dye_hue_mass = hue * self.dye

    def _sample(self, field, sample_x, sample_y):
        """Bilinear interpolation on the periodic simulation grid."""
        sample_x = sample_x % self.n
        sample_y = sample_y % self.n
        floor_x = np.floor(sample_x)
        floor_y = np.floor(sample_y)
        x0 = floor_x.astype(np.int32) % self.n
        y0 = floor_y.astype(np.int32) % self.n
        x1 = (x0 + 1) % self.n
        y1 = (y0 + 1) % self.n
        wx = sample_x - floor_x
        wy = sample_y - floor_y
        return (
            field[y0, x0] * (1.0 - wx) * (1.0 - wy)
            + field[y0, x1] * wx * (1.0 - wy)
            + field[y1, x0] * (1.0 - wx) * wy
            + field[y1, x1] * wx * wy
        )

    def _advect(self, field, u, v, dt):
        return self._sample(field, self.x - dt * u, self.y - dt * v)

    def step(self, dt):
        """Advect, diffuse, then enforce incompressibility with pressure."""
        transported_u = self._advect(self.u, self.u, self.v, dt)
        transported_v = self._advect(self.v, self.u, self.v, dt)

        viscous_decay = np.exp(-VISCOSITY * self.scale * self.scale * self.k2 * dt)
        u_hat = np.fft.fft2(transported_u) * viscous_decay
        v_hat = np.fft.fft2(transported_v) * viscous_decay

        # div(u*) / dt = laplacian(p); subtract dt * grad(p) from u*.
        divergence_hat = 1j * (self.kx * u_hat + self.ky * v_hat)
        pressure_hat = -divergence_hat / (dt * self.safe_k2)
        pressure_hat[self.zero_mode] = 0.0
        u_hat -= dt * 1j * self.kx * pressure_hat
        v_hat -= dt * 1j * self.ky * pressure_hat

        self.u = np.fft.ifft2(u_hat).real
        self.v = np.fft.ifft2(v_hat).real
        self.pressure = np.fft.ifft2(pressure_hat).real
        decay = math.exp(-DYE_FADE_RATE * dt)
        self.dye_hue_mass = self._advect(self.dye_hue_mass, self.u, self.v, dt) * decay
        self.dye = self._advect(self.dye, self.u, self.v, dt) * decay

    def update_divergence_rms(self):
        """Refresh the display diagnostic without slowing every physics step."""
        residual_hat = 1j * (
            self.kx * np.fft.fft2(self.u) + self.ky * np.fft.fft2(self.v)
        )
        residual = np.fft.ifft2(residual_hat).real
        self.divergence_rms = float(np.sqrt(np.mean(residual * residual)))

    def vorticity(self):
        dv_dx = (np.roll(self.v, -1, axis=1) - np.roll(self.v, 1, axis=1)) / 2.0
        du_dy = (np.roll(self.u, -1, axis=0) - np.roll(self.u, 1, axis=0)) / 2.0
        return dv_dx - du_dy

    def colors(self, mode):
        """Return display RGB plus the scale printed next to the controls."""
        if mode == 0:
            speed = np.hypot(self.u, self.v)
            scale = max(float(np.percentile(speed, 98)), 1.0)
            ramp = ((0, 0, 0), (177, 186, 200), (161, 187, 221),
                    (160, 214, 219), (239, 191, 205))
            return palette(speed / scale, ramp), f"0 ~ {scale:.1f} 格/秒"
        if mode == 1:
            scale = max(float(np.percentile(np.abs(self.pressure), 98)), 0.1)
            ramp = ((153, 179, 225), (175, 189, 215), (0, 0, 0),
                    (219, 179, 190), (242, 166, 180))
            return palette(0.5 + 0.5 * self.pressure / scale, ramp), f"±{scale:.2f}"
        if mode == 2:
            curl = self.vorticity()
            scale = max(float(np.percentile(np.abs(curl), 98)), 0.05)
            ramp = ((158, 211, 219), (176, 202, 211), (0, 0, 0),
                    (207, 177, 206), (228, 165, 207))
            return palette(0.5 + 0.5 * curl / scale, ramp), f"±{scale:.2f} /秒"
        hue = np.divide(self.dye_hue_mass, self.dye,
                        out=np.full_like(self.dye, 0.5), where=self.dye > 1e-8)
        ramp = ((239, 172, 202), (248, 196, 169), (246, 224, 166),
                (172, 223, 198), (190, 189, 240))
        pigment = palette(hue, ramp)
        opacity = np.clip(self.dye * 1.8, 0.0, 1.0)
        rgb = opacity[..., None] * pigment
        return rgb.astype(np.uint8), "0 ~ 1"

    def arrow_field(self, mode):
        if mode == 0:
            return self.u, self.v
        if mode == 1:
            px = (np.roll(self.pressure, -1, axis=1)
                  - np.roll(self.pressure, 1, axis=1)) / 2.0
            py = (np.roll(self.pressure, -1, axis=0)
                  - np.roll(self.pressure, 1, axis=0)) / 2.0
            return -px, -py
        dx = (np.roll(self.dye, -1, axis=1)
              - np.roll(self.dye, 1, axis=1)) / 2.0
        dy = (np.roll(self.dye, -1, axis=0)
              - np.roll(self.dye, 1, axis=0)) / 2.0
        return dx, dy


def draw_arrows(screen, fluid, mode):
    if mode == 3:
        return
    ax, ay = fluid.arrow_field(mode)
    stride = fluid.n // 16
    offset = stride // 2
    cell_pixels = VIEW_PIXELS / fluid.n
    sampled = np.hypot(ax[offset::stride, offset::stride],
                       ay[offset::stride, offset::stride])
    reference = max(float(np.percentile(sampled, 95)), 1e-9)
    for y in range(offset, fluid.n, stride):
        for x in range(offset, fluid.n, stride):
            vx = float(ax[y, x])
            vy = float(ay[y, x])
            magnitude = math.hypot(vx, vy)
            if magnitude < 0.06 * reference:
                continue
            length = min(22.0, 20.0 * magnitude / reference)
            direction_x = vx / magnitude
            direction_y = vy / magnitude
            center_x = (x + 0.5) * cell_pixels
            center_y = (y + 0.5) * cell_pixels
            start = (center_x - 0.5 * length * direction_x,
                     center_y - 0.5 * length * direction_y)
            end = (center_x + 0.5 * length * direction_x,
                   center_y + 0.5 * length * direction_y)
            wing_1 = (end[0] - 5 * direction_x - 3 * direction_y,
                      end[1] - 5 * direction_y + 3 * direction_x)
            wing_2 = (end[0] - 5 * direction_x + 3 * direction_y,
                      end[1] - 5 * direction_y - 3 * direction_x)
            start = (round(start[0]), round(start[1]))
            end = (round(end[0]), round(end[1]))
            wing_1 = (round(wing_1[0]), round(wing_1[1]))
            wing_2 = (round(wing_2[0]), round(wing_2[1]))
            pygame.draw.line(screen, (235, 240, 250), start, end, 1)
            pygame.draw.line(screen, (235, 240, 250), end, wing_1, 1)
            pygame.draw.line(screen, (235, 240, 250), end, wing_2, 1)


def draw_boat(screen, x, y, heading_x, heading_y):
    """Draw the boat pointing in its last movement direction."""
    points = (
        (round(x + 24 * heading_x), round(y + 24 * heading_y)),
        (round(x - 16 * heading_x - 11 * heading_y),
         round(y - 16 * heading_y + 11 * heading_x)),
        (round(x - 16 * heading_x + 11 * heading_y),
         round(y - 16 * heading_y - 11 * heading_x)),
    )
    pygame.draw.polygon(screen, (255, 250, 225), points)
    pygame.draw.polygon(screen, (24, 42, 60), points, 2)
    pygame.draw.circle(screen, (24, 42, 60), (round(x), round(y)), 5)


def draw_panel(screen, font, small_font, fluid, color_mode, arrow_mode,
               color_scale, boat_speed, paused, fps):
    panel_x = VIEW_PIXELS
    pygame.draw.rect(screen, (0, 0, 0),
                     (panel_x, 0, PANEL_PIXELS, VIEW_PIXELS))
    lines = (
        (f"{fluid.n} × {fluid.n} 流體模擬", font, (240, 246, 255), 22),
        ("2D Navier–Stokes / 週期邊界", small_font, (151, 162, 185), 59),
        (f"初始：{INITIAL_STATES[fluid.initial_state]}", small_font,
         (170, 205, 230), 85),
        ("顏色 [C]", font, (142, 220, 255), 115),
        (COLOR_MODES[color_mode], font, (255, 255, 255), 151),
        (color_scale, small_font, (165, 173, 192), 184),
        ("箭頭 [X]", font, (142, 220, 255), 240),
        (ARROW_MODES[arrow_mode], font, (255, 255, 255), 276),
        ("壓力箭頭 = -∇p", small_font, (172, 184, 205), 309),
        ("壓力顏色為相對值", small_font, (172, 184, 205), 333),
        ("W/S 前後，A/D 轉向", small_font, (215, 221, 233), 362),
        (f"船速 [+/-]：{boat_speed:.0f} px/s", small_font,
         (215, 221, 233), 394),
        ("方向鍵相同；放開隨流漂移", small_font, (215, 221, 233), 422),
        ("按鍵染色；前後推動", small_font, (215, 221, 233), 446),
        ("左鍵拖曳：推動 + 染色", small_font, (215, 221, 233), 470),
        ("右鍵拖曳：只染色", small_font, (215, 221, 233), 494),
        ("[ / ]：解析度 (切換會重設)", small_font, (215, 221, 233), 522),
        ("I：切換初始狀態", small_font, (215, 221, 233), 546),
        ("R：重設 / 空白鍵：暫停", small_font, (215, 221, 233), 570),
        ("Esc：離開", small_font, (215, 221, 233), 594),
        (f"散度 RMS {fluid.divergence_rms:.2e}", small_font,
         (152, 230, 190), 648),
        (f"{fps:.0f} FPS  |  {'暫停' if paused else '運行'}", small_font,
         (152, 230, 190), 680),
    )
    for label, label_font, color, y in lines:
        screen.blit(label_font.render(label, True, color), (panel_x + 20, y))


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Navier–Stokes 流體模擬")
    font = pygame.font.SysFont("Microsoft JhengHei", 24)
    small_font = pygame.font.SysFont("Microsoft JhengHei", 18)
    clock = pygame.time.Clock()
    resolution_index = RESOLUTIONS.index(DEFAULT_RESOLUTION)
    initial_state = DEFAULT_INITIAL_STATE
    fluid = Fluid(RESOLUTIONS[resolution_index], initial_state)
    color_mode = 0
    arrow_mode = 0
    paused = False
    boat_x, boat_y = BOAT_START
    boat_heading_x, boat_heading_y = 0.0, -1.0
    boat_speed_index = 1
    elapsed = 0.0
    last_divergence_update = pygame.time.get_ticks()
    running = True

    while running:
        frame_seconds = min(clock.tick(60) / 1000.0, 0.25)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_c:
                    color_mode = (color_mode + 1) % len(COLOR_MODES)
                elif event.key == pygame.K_x:
                    arrow_mode = (arrow_mode + 1) % len(ARROW_MODES)
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS,
                                   pygame.K_KP_PLUS):
                    boat_speed_index = min(boat_speed_index + 1,
                                           len(BOAT_SPEEDS) - 1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    boat_speed_index = max(boat_speed_index - 1, 0)
                elif event.key == pygame.K_r:
                    fluid.reset()
                    boat_x, boat_y = BOAT_START
                    boat_heading_x, boat_heading_y = 0.0, -1.0
                    elapsed = 0.0
                    last_divergence_update = pygame.time.get_ticks()
                elif event.key == pygame.K_i:
                    initial_state = (initial_state + 1) % len(INITIAL_STATES)
                    fluid = Fluid(RESOLUTIONS[resolution_index], initial_state)
                    boat_x, boat_y = BOAT_START
                    boat_heading_x, boat_heading_y = 0.0, -1.0
                    elapsed = 0.0
                    last_divergence_update = pygame.time.get_ticks()
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    change = -1 if event.key == pygame.K_LEFTBRACKET else 1
                    new_index = max(0, min(resolution_index + change,
                                           len(RESOLUTIONS) - 1))
                    if new_index != resolution_index:
                        resolution_index = new_index
                        fluid = Fluid(RESOLUTIONS[resolution_index], initial_state)
                        boat_x, boat_y = BOAT_START
                        boat_heading_x, boat_heading_y = 0.0, -1.0
                        elapsed = 0.0
                        last_divergence_update = pygame.time.get_ticks()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 3) and event.pos[0] < VIEW_PIXELS:
                    fluid.inject(event.pos[0] * fluid.n / VIEW_PIXELS,
                                 event.pos[1] * fluid.n / VIEW_PIXELS,
                                 0.0, 0.0, False, current_brush_hue())
            elif event.type == pygame.MOUSEMOTION:
                if event.pos[0] < VIEW_PIXELS and (event.buttons[0] or event.buttons[2]):
                    fluid.inject(event.pos[0] * fluid.n / VIEW_PIXELS,
                                 event.pos[1] * fluid.n / VIEW_PIXELS,
                                 event.rel[0] * fluid.n / VIEW_PIXELS,
                                 event.rel[1] * fluid.n / VIEW_PIXELS,
                                 bool(event.buttons[0]), current_brush_hue())

        if not paused:
            keys = pygame.key.get_pressed()
            forward = keys[pygame.K_w] or keys[pygame.K_UP]
            backward = keys[pygame.K_s] or keys[pygame.K_DOWN]
            turn_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
            turn_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            throttle = int(forward) - int(backward)
            turn = int(turn_right) - int(turn_left)
            if turn:
                angle = turn * BOAT_TURN_SPEED * frame_seconds
                cosine, sine = math.cos(angle), math.sin(angle)
                boat_heading_x, boat_heading_y = (
                    boat_heading_x * cosine - boat_heading_y * sine,
                    boat_heading_x * sine + boat_heading_y * cosine,
                )
            grid_x = boat_x * fluid.n / VIEW_PIXELS
            grid_y = boat_y * fluid.n / VIEW_PIXELS
            flow_x = float(fluid._sample(fluid.u, grid_x, grid_y))
            flow_y = float(fluid._sample(fluid.v, grid_x, grid_y))
            control_x = throttle * boat_heading_x * BOAT_SPEEDS[boat_speed_index] * frame_seconds
            control_y = throttle * boat_heading_y * BOAT_SPEEDS[boat_speed_index] * frame_seconds
            move_x = flow_x * VIEW_PIXELS / fluid.n * frame_seconds + control_x
            move_y = flow_y * VIEW_PIXELS / fluid.n * frame_seconds + control_y
            if forward or backward or turn_left or turn_right:
                brush_pixels = BRUSH_RADIUS * VIEW_PIXELS / DEFAULT_RESOLUTION
                segments = max(1, math.ceil(math.hypot(move_x, move_y) / brush_pixels))
                drag_x = control_x * fluid.n / (VIEW_PIXELS * segments)
                drag_y = control_y * fluid.n / (VIEW_PIXELS * segments)
                hue = current_brush_hue()
                for segment in range(1, segments + 1):
                    fraction = segment / segments
                    x = (boat_x + move_x * fraction) % VIEW_PIXELS
                    y = (boat_y + move_y * fraction) % VIEW_PIXELS
                    fluid.inject(x * fluid.n / VIEW_PIXELS,
                                 y * fluid.n / VIEW_PIXELS,
                                 drag_x, drag_y, True, hue)
            boat_x = (boat_x + move_x) % VIEW_PIXELS
            boat_y = (boat_y + move_y) % VIEW_PIXELS
            elapsed += frame_seconds
            for _ in range(5):
                if elapsed < SIM_DT:
                    break
                fluid.step(SIM_DT)
                elapsed -= SIM_DT
            elapsed = min(elapsed, SIM_DT)
            now = pygame.time.get_ticks()
            divergence_interval = 1000.0 / DIVERGENCE_FPS
            if now - last_divergence_update >= divergence_interval:
                fluid.update_divergence_rms()
                last_divergence_update += divergence_interval * int(
                    (now - last_divergence_update) // divergence_interval
                )

        rgb, color_scale = fluid.colors(color_mode)
        pixels = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
        screen.blit(pygame.transform.scale(pixels, (VIEW_PIXELS, VIEW_PIXELS)),
                    (0, 0))
        draw_arrows(screen, fluid, arrow_mode)
        draw_boat(screen, boat_x, boat_y, boat_heading_x, boat_heading_y)
        draw_panel(screen, font, small_font, fluid, color_mode, arrow_mode,
                   color_scale, BOAT_SPEEDS[boat_speed_index], paused,
                   clock.get_fps())
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
