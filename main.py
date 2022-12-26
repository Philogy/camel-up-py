import re
import sys
from collections import defaultdict
from enum import Enum
from board import apply_move, Move, Camel, Jump, JumpField, copy_board, get_rankings
from game import OwnedAction, apply_action, Place, print_game, init_game, Game
from itertools import product, permutations, starmap
from typing import Optional


class ParseError(Exception):
    pass


class CmdAction(Enum):
    Undo = 'UNDO'
    Save = 'SAVE'
    Revert = 'REVERT'
    Reset = 'RESET'


def validate_args(cmd_name, args, amount):
    if len(args) != amount:
        s = '' if amount == 1 else 's'
        args_as_str = ', '.join(f'{arg!r}' for arg in args)
        raise ParseError(
            f'{cmd_name} requires {amount} argument{s}, found {len(args)} ({args_as_str})'
        )


def parse_camel(camel_char: str) -> Camel:
    try:
        return Camel(camel_char.upper())
    except ValueError:
        raise ParseError(f'Invalid camel {camel_char!r}')


def parse_move(game: Game, inp: str) -> Move:
    if len(inp) != 2:
        raise ParseError(
            f'Raw move must have 2 charaters not {inp!r} ({len(inp)})')
    raw_steps, camel_char = sorted(inp)
    if not raw_steps.isdigit() or (steps := int(raw_steps)) not in (1, 2, 3):
        raise ParseError(f'Invalid steps {raw_steps!r}')
    camel = parse_camel(camel_char)
    if camel not in game.camels_left:
        raise ParseError(f'{camel.name} already moved')
    return Move(camel, steps)


def parse_place(game: Game, inp: str) -> Place:
    if not (m := re.match(r'(?:([+-])(\d{1,2})|(\d{1,2})([+-]))', inp)):
        raise ParseError(
            f'Place input {inp!r} does not match +XX, -XX, XX-, XX+'
        )
    sign1, pos1, pos2, sign2 = m.groups()
    sign = sign1 or sign2
    pos = int(pos1 or pos2) - 1
    if pos == 0:
        raise ParseError('Cannot place jump on position #1')
    if pos not in range(0, 16):
        raise ParseError(f'Nonexistent position #{pos + 1}')

    if game.board.fields[pos] is not None:
        raise ParseError(f'Destination position#{pos + 1} not empty')
    if isinstance(game.board.fields[pos-1], JumpField)\
            or (pos != 15 and isinstance(game.board.fields[pos + 1], JumpField)):
        raise ParseError(f'Cannot place new jump next to adjacent jumps')

    return Place(pos, Jump(int(sign + '1')))


def parse_bet(game: Game, camel_char: str):
    camel = parse_camel(camel_char)
    if not game.bets[camel]:
        raise ParseError(f'No {camel} bets remain')
    return camel


def simulate_probs(game: Game):
    fst_p = defaultdict(float)
    snd_p = defaultdict(float)
    winners = defaultdict(float)
    losers = defaultdict(float)
    shifts = defaultdict(float)
    total_paths = 1
    for i in range(1, len(game.camels_left) + 1):
        total_paths *= 3 * i
    for camel_order in permutations(game.camels_left):
        for move_steps in product(*[range(1, 4) for _ in range(len(game.camels_left))]):
            sub_board = copy_board(game.board)
            for move in starmap(Move, zip(camel_order, move_steps)):
                sub_board, shifter, winner_stack = apply_move(sub_board, move)
                if shifter is not None:
                    shifts[shifter] += 1/total_paths
                if winner_stack is not None:
                    break
            fst_camel, snd_camel, _, _, lst_camel = get_rankings(
                sub_board,
                winner_stack
            )
            if winner_stack is not None:
                winners[fst_camel] += 1 / total_paths
                losers[lst_camel] += 1 / total_paths
            fst_p[fst_camel] += 1 / total_paths
            snd_p[snd_camel] += 1 / total_paths
    return fst_p, snd_p, winners, losers, shifts


def show_evs(game: Game):
    fst_p, snd_p, *_ = simulate_probs(game)
    for camel in sorted(Camel, key=lambda c: fst_p[c], reverse=True):
        cfst_p = fst_p[camel]
        csnd_p = snd_p[camel]
        if game.bets[camel]:
            lose_p = 1 - (cfst_p + csnd_p)
            ev = game.bets[camel][-1].value * cfst_p + 1 * csnd_p - 1 * lose_p
            ev_as_str = f'{ev:5.2f}'
        else:
            ev_as_str = 'None'
        print(f'{camel.name:6} ({cfst_p:5.1%} | {csnd_p:5.1%}): {ev_as_str}')
    for name, player in game.players.items():
        total_ev = sum(
            bet_size.value * fst_p[camel] + 1 * snd_p[camel] -
            1 * (1 - fst_p[camel] - snd_p[camel])
            for bet_size, camel in player.owned_bets
        )
        print(f'{name}: {total_ev:5.2f}')


def parse_action(game: Game, inp: str) -> Optional[OwnedAction | CmdAction]:
    inp = inp.strip()

    split_res = inp.split()
    if len(split_res) == 0:
        raise ParseError(
            f'Input {inp!r} must have at least 1 component, found none'
        )
    cmd, *args = split_res

    if set(game.board.index) == set(Camel):
        if cmd in ('move', 'place', 'bet'):
            owner, *args = args
            if owner not in game.players:
                raise ParseError(f'{owner!r} is not a valid owner')

            if cmd == 'move':
                validate_args('Move', args, 1)
                action = parse_move(game, *args)
            elif cmd == 'place':
                validate_args('Place', args, 1)
                action = parse_place(game, *args)
                if any(
                    isinstance(field, JumpField) and field.owner == owner
                    for field in game.board.fields
                ):
                    raise ParseError(
                        f'Owner {owner!r} has already placed a jump')
            else:
                validate_args('Bet', args, 1)
                action = parse_bet(game, *args)
            return OwnedAction(owner, action)
        elif cmd == 'sim':
            validate_args('Simulate EV', args, 0)
            show_evs(game)
    if cmd == 'print':
        print()
        print_game(game)
        print()
    elif cmd == 'rank':
        ranked = get_rankings(game.board, None)
        for i, camel in enumerate(ranked, start=1):
            print(f'#{i} {camel.name}')
    elif cmd == 'undo':
        return CmdAction.Undo
    elif cmd == 'save':
        return CmdAction.Save
    elif cmd == 'revert':
        return CmdAction.Revert
    elif cmd == 'reset':
        return CmdAction.Reset
    elif cmd == 'clear':
        print('\n'*50)
    elif set(game.board.index) != set(Camel):
        move = parse_move(game, inp)
        return OwnedAction(None, move)
    else:
        raise ParseError(f'Unrecognized command {cmd!r}')


def main():
    players = sys.argv[1:]
    game = init_game(*players)
    history_stack = []
    save_stack = []
    while (inp := input('> ')) != 'exit':
        try:
            action = parse_action(game, inp)
        except ParseError as err:
            print(f'ParseError: {err}')
            continue
        if action is None:
            continue
        if isinstance(action, CmdAction):
            if action == CmdAction.Undo:
                if history_stack:
                    game = history_stack.pop()
                else:
                    print('Error: No history to undo.')
            elif action == CmdAction.Save:
                save_stack.append(game)
                print('Checkpoint saved.')
            elif action == CmdAction.Revert:
                if save_stack:
                    history_stack.append(game)
                    game = save_stack.pop()
                    print('Reverted to previous checkpoint.')
                else:
                    print('Error: No checkpoints to revert to.')
            elif action == CmdAction.Reset:
                history_stack.append(game)
                game = init_game(*players)
            continue

        history_stack.append(game)
        game, _ = apply_action(game, action)


if __name__ == '__main__':
    main()
