# Input.py

import pygame


class Input:
    """
    Sistema de entrada do MegaComp.

    Controles internos:
        UP
        DOWN
        LEFT
        RIGHT
        A
        B
        C
        START
        SELECT
    """

    def __init__(self):
        pygame.init()
        pygame.joystick.init()

        self.joystick = None

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

        self.keys = set()
        self.buttons = set()

        self.running = True

    def update(self):
        """
        Processa todos os eventos de entrada.
        """

        self.keys.clear()
        self.buttons.clear()

        for event in pygame.event.get():

            # Fechar pela janela / ALT+F4
            if event.type == pygame.QUIT:
                self.running = False

            # Teclado
            elif event.type == pygame.KEYDOWN:
                self.keys.add(event.key)

            elif event.type == pygame.KEYUP:
                self.keys.discard(event.key)

            # Controle
            elif event.type == pygame.JOYBUTTONDOWN:
                self.buttons.add(event.button)

            elif event.type == pygame.JOYBUTTONUP:
                self.buttons.discard(event.button)

        # START + SELECT = fechar
        if self.start_pressed() and self.select_pressed():
            self.running = False

    # ---------------------------------------------------------
    # TECLADO
    # ---------------------------------------------------------

    def keyboard_pressed(self, *keys):
        return any(key in self.keys for key in keys)

    # ---------------------------------------------------------
    # DIREÇÕES
    # ---------------------------------------------------------

    def up_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_UP, pygame.K_w)
            or self._dpad(0, -1)
        )

    def down_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_DOWN, pygame.K_s)
            or self._dpad(0, 1)
        )

    def left_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_LEFT, pygame.K_a)
            or self._dpad(-1, 0)
        )

    def right_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_RIGHT, pygame.K_d)
            or self._dpad(1, 0)
        )

    # ---------------------------------------------------------
    # BOTÕES MEGA DRIVE
    # ---------------------------------------------------------

    def a_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_z)
            or self._controller_button("A")
        )

    def b_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_x)
            or self._controller_button("B")
        )

    def c_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_c)
            or self._controller_button("C")
        )

    def start_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_RETURN)
            or self._controller_button("START")
        )

    def select_pressed(self):
        return (
            self.keyboard_pressed(pygame.K_RSHIFT)
            or self._controller_button("SELECT")
        )

    # ---------------------------------------------------------
    # CONTROLE
    # ---------------------------------------------------------

    def _dpad(self, x, y):
        """
        Lê o D-pad usando o Hat padrão de controles.

        x:
            -1 = esquerda
             0 = neutro
             1 = direita

        y:
            -1 = cima
             0 = neutro
             1 = baixo
        """

        if self.joystick is None:
            return False

        if self.joystick.get_numhats() == 0:
            return False

        hat_x, hat_y = self.joystick.get_hat(0)

        return hat_x == x and hat_y == y

    def _controller_button(self, name):
        """
        Mapeamento padrão para controles.

        A ideia é manter a função lógica separada
        da posição física do botão.
        """

        if self.joystick is None:
            return False

        # Layout padrão semelhante ao Xbox / XInput
        mapping = {
            "A": 0,
            "B": 1,
            "C": 2,
            "START": 7,
            "SELECT": 6,
        }

        button = mapping.get(name)

        if button is None:
            return False

        if button >= self.joystick.get_numbuttons():
            return False

        return self.joystick.get_button(button)

    # ---------------------------------------------------------
    # ESTADO
    # ---------------------------------------------------------

    def is_running(self):
        return self.running

    def quit(self):
        self.running = False