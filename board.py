from collections import namedtuple
from enum import Enum
from typing import TypeAlias, cast, Dict, Optional, Any


class Camel(Enum):
    Yellow = 'Y'
    White = 'W'
    Blue = 'B'
    Orange = 'O'
    Green = 'G'


class Jump(Enum):
    Forward = 1
    Backwards = -1


Move: type[tuple[Camel, int]] = namedtuple('Move', ['camel', 'steps'])

JumpField: type[tuple[Jump, Any]] = namedtuple(
    'JumpField',
    ['jtype', 'owner']
)
EmptyField: TypeAlias = type[None]
CamelStack: TypeAlias = list[Camel]
BoardField: TypeAlias = CamelStack | EmptyField | JumpField
CamelIndex: TypeAlias = Dict[Camel, int]
Board = namedtuple('Board', ['fields', 'index'])
BOARD_SIZE = 16


def create_empty_board() -> Board:
    return Board([None for _ in range(BOARD_SIZE)], dict())


def field_to_str(field: BoardField, height: int) -> str:
    assert height in range(0, 5)
    if field is None:
        return ' '
    if isinstance(field, list):
        if height < len(field):
            return field[height].value
        return ' '
    assert isinstance(field, JumpField)
    if height != 0:
        return ' '
    jtype = cast(JumpField, field).jtype
    return '+' if jtype == Jump.Forward else '-'


def validate_board(board: Board):
    for camel, pos in board.index.items():
        if pos >= BOARD_SIZE:
            continue
        assert isinstance(board.fields[pos], list),\
            f'Board position {pos + 1} is not a camel stack'
        assert camel in board.fields[pos], f'Camel \'{camel.name}\' not on position {pos + 1}'


def validates_board(ret_pos: Optional[int]):
    def decorator(f):
        def wrapped_f(*args, **kwargs):
            res = f(*args, **kwargs)
            if ret_pos is None:
                board = res
            else:
                board = res[ret_pos]
            validate_board(board)
            return res
        return wrapped_f
    return decorator


def copy_board(board: Board) -> Board:
    fields = [
        field.copy() if isinstance(field, list) else field
        for field in board.fields
    ]
    return Board(fields, board.index.copy())


def print_board(board: Board) -> None:
    for h in range(4, -1, -1):
        row_els = [
            field_to_str(board.fields[i], h)
            for i in range(BOARD_SIZE)
        ]
        row = '  ' + '  '.join(row_els)
        print(row.rstrip())
    print('', *[f'{x:02}' for x in range(1, BOARD_SIZE + 1)])
    validate_board(board)


def get_rankings(board: Board, winners: Optional[list[Camel]]) -> list[Camel]:
    unsorted_camels = [
        (camel, (index, (board.fields[index] if index <
         BOARD_SIZE else winners).index(camel)))
        for camel, index in board.index.items()
    ]
    indexed_camels = sorted(unsorted_camels, key=lambda v: v[1], reverse=True)
    return [indexed_camel[0] for indexed_camel in indexed_camels]


@validates_board(0)
def apply_move(board: Board, move: Move) -> tuple[Board, Optional[Any], Optional[list[Camel]]]:
    board = copy_board(board)

    if move.camel not in board.index:
        pos = move.steps - 1
        board.index[move.camel] = pos
        field = board.fields[pos]
        assert not isinstance(field, JumpField), 'Jump at start'
        if isinstance(field, list):
            field.append(move.camel)
        else:
            board.fields[pos] = [move.camel]
        return board, None, None

    start_pos = board.index[move.camel]
    height = board.fields[start_pos].index(move.camel)
    move_stack = board.fields[start_pos][height:]
    sliced_stack = board.fields[start_pos][:height]
    board.fields[start_pos] = sliced_stack or None
    for camel in move_stack:
        board.index[camel] += move.steps
    end_pos = start_pos + move.steps
    if end_pos >= BOARD_SIZE:
        return board, None, move_stack
    dest_field = board.fields[end_pos]
    owner = None
    if isinstance(dest_field, JumpField):
        owner = dest_field.owner
        shift = dest_field.jtype.value
        end_pos += shift
        for camel in move_stack:
            board.index[camel] += shift
        if end_pos >= BOARD_SIZE:
            return board, owner, move_stack
        if shift == -1:
            if board.fields[end_pos] is None:
                board.fields[end_pos] = move_stack
            else:
                board.fields[end_pos] = move_stack + board.fields[end_pos]
            return board, owner, None

    if board.fields[end_pos] is None:
        board.fields[end_pos] = move_stack
    else:
        board.fields[end_pos] += move_stack
    return board, owner, None


if __name__ == '__main__':
    moves = list(range(5))
    board = create_empty_board()
    # start moves
    board, _, _ = apply_move(board, Move(Camel.Yellow, 1))
    board, _, _ = apply_move(board, Move(Camel.White, 1))
    board, _, _ = apply_move(board, Move(Camel.Blue, 2))
    board, _, _ = apply_move(board, Move(Camel.Orange, 1))
    board, _, _ = apply_move(board, Move(Camel.Green, 1))

    board.fields[2] = JumpField(Jump.Backwards, 'test')

    print_board(board)
    move = Move(Camel.White, 2)
    board, owner, _ = apply_move(board, move)
    print()
    print(f'owner: {owner}')
    print_board(board)
