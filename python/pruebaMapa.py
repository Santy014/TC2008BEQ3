class Boundary:
    def __init__(self, boundary_type="wall"):
        self.type = boundary_type

class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.boundaries = {}

    def _get_edge_key(self, pos1, pos2):
        return tuple(sorted((pos1, pos2)))

    def add_boundary(self, pos1, pos2, boundary_type="wall"):
        key = self._get_edge_key(pos1, pos2)
        self.boundaries[key] = Boundary(boundary_type)

def setup_user_map(board):
    # ---MUROS EXTERIORES ---
    for x in range(1, 9):
        if x != 6: board.add_boundary((x, 1), (x, 0), "wall") # Superior (Hueco en x=6)
        if x != 3: board.add_boundary((x, 6), (x, 7), "wall") # Inferior (Hueco en x=3)
    for y in range(1, 7):
        if y != 3: board.add_boundary((1, y), (0, y), "wall") # Izquierdo (Hueco en y=3)
        if y != 4: board.add_boundary((8, y), (9, y), "wall") # Derecho (Hueco en y=4)
        
    # ---MUROS INTERNOS ---
    # Horizontales internos
    for x in [3, 4, 5, 6, 7]:
        board.add_boundary((x, 2), (x, 3), "wall") 
    board.add_boundary((8, 3), (8, 2), "door") 
    
    for x in [1, 2, 3, 5, 6, 7, 8]:
        board.add_boundary((x, 4), (x, 5), "wall") 
    board.add_boundary((4, 4), (4, 5), "door") 
    
    # Verticales internos
    board.add_boundary((3, 1), (4, 1), "door") 
    board.add_boundary((3, 2), (4, 2), "wall") 
    board.add_boundary((5, 1), (6, 1), "wall") 
    board.add_boundary((5, 2), (6, 2), "door") 
    board.add_boundary((2, 3), (3, 3), "door") 
    board.add_boundary((2, 4), (3, 4), "wall") 
    board.add_boundary((6, 3), (7, 3), "wall") 
    board.add_boundary((6, 4), (7, 4), "door") 
    board.add_boundary((5, 5), (6, 5), "wall")
    board.add_boundary((5, 6), (6, 6), "door")
    board.add_boundary((7, 5), (8, 5), "wall") 
    board.add_boundary((7, 6), (8, 6), "door") 

def render_board(board):
    """Transforma las coordenadas lógicas en un dibujo ASCII con espaciado estricto"""
    canvas_w = board.width * 2 + 1
    canvas_h = board.height * 2 + 1
    
    # 1. Inicializar lienzo con estructura base
    canvas = []
    for y in range(canvas_h):
        row = []
        for x in range(canvas_w):
            if x % 2 == 0 and y % 2 == 0:
                row.append("+")       # Esquinas/Pilares
            elif x % 2 != 0 and y % 2 == 0:
                row.append("   ")     # Espacio para muro horizontal
            elif x % 2 == 0 and y % 2 != 0:
                row.append(" ")       # Espacio para muro vertical
            else:
                row.append(" . ")     # Interior de la celda
        canvas.append(row)

    # 2. Mapear los boundaries al canvas
    for (pos1, pos2), boundary in board.boundaries.items():
        # Es un muro HORIZONTAL (Misma X, diferente Y)
        if pos1[0] == pos2[0]:
            min_y = min(pos1[1], pos2[1])
            cx = pos1[0] * 2 - 1
            cy = min_y * 2
            if boundary.type == "wall":
                canvas[cy][cx] = "---"
            elif boundary.type == "door":
                canvas[cy][cx] = " D "
                
        # Es un muro VERTICAL (Misma Y, diferente X)
        elif pos1[1] == pos2[1]:
            min_x = min(pos1[0], pos2[0])
            cx = min_x * 2
            cy = pos1[1] * 2 - 1
            if boundary.type == "wall":
                canvas[cy][cx] = "|"
            elif boundary.type == "door":
                canvas[cy][cx] = "d"

    # 3. Imprimir resultado con etiquetas alineadas
    print("\n    1   2   3   4   5   6   7   8 (X)")
    for i, row in enumerate(canvas):
        row_str = "".join(row)
        if i % 2 != 0:
            print(f"{i//2 + 1} {row_str}") # Fila de celdas
        else:
            print(f"  {row_str}")        # Fila de muros horizontales
    print(" (Y)\n")

if __name__ == "__main__":
    print("Generando mapa de prueba...")
    b = Board(8, 6)
    setup_user_map(b)
    render_board(b)