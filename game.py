from typing import Dict, Any, TypeAlias, Optional
from collections import namedtuple
from enum import Enum
from board import (Camel, Board, Move, Jump, copy_board, create_empty_board,
                   print_board, apply_move, JumpField, get_rankings)


class BetSize(Enum):
    Low = 2
    Med = 3
    High = 5


Bets: TypeAlias = Dict[Camel, list[BetSize]]
Bet = namedtuple('Bet', ['size', 'camel'])
Player = namedtuple('Player', ['balance', 'owned_bets'])
Players: TypeAlias = dict[Any, Player]
Game = namedtuple('Game', ['board', 'players', 'bets', 'camels_left'])

# action = [Roll (Move), Place, Bet (Camel)]
Place: type[tuple[int, Jump]] = namedtuple('Place', ['position', 'jump'])
OwnedAction = namedtuple('OwnedAction', ['owner', 'action'])


def reset_bets() -> Bets:
    return {
        camel: list(BetSize)
        for camel in Camel
    }


def copy_player(player: Player) -> Player:
    return Player(
        player.balance,
        player.owned_bets.copy()
    )


def copy_players(players: Players) -> Players:
    return {
        name: copy_player(player)
        for name, player in players.items()
    }


def copy_bets(bets: Bets) -> Bets:
    return {
        camel: bets.copy()
        for camel, bets in bets.items()
    }


def copy_game(game: Game) -> Game:
    return Game(
        copy_board(game.board),
        copy_players(game.players),
        copy_bets(game.bets),
        game.camels_left.copy()
    )


def init_game(*players) -> Game:
    return Game(
        create_empty_board(),
        {
            name: Player(3, set())
            for name in players
        },
        reset_bets(),
        set(Camel)
    )


def bet_to_str(bet: list[BetSize]) -> str:
    if len(bet) == 0:
        return '-'
    return str(bet[-1].value)


def players_to_strings(players: Players):
    for name, player in sorted(players.items(), key=lambda p: (p[1].balance, p[0])):
        if player.owned_bets:
            owned_bets = ' '.join([
                f'{camel.value}{bet.value}'
                for bet, camel in player.owned_bets
            ])
            yield f'{name}[{player.balance} ({owned_bets})]'
        else:
            yield f'{name}[{player.balance}]'


def print_game(game: Game):
    balances = ', '.join([
        player_as_str
        for player_as_str in players_to_strings(game.players)
    ])
    print('Balances:', balances)
    bets = ', '.join([
        f'{camel.name}[{bet_to_str(game.bets[camel])}]'
        for camel in Camel
    ])
    print('Bets:', bets)
    camels = ', '.join(
        camel.name
        for camel in sorted(game.camels_left, key=lambda c: c.name)
    )
    print('Camels:', camels)
    print('Board:')
    print_board(game.board)


def change_balance(players: Players, name, delta):
    players[name] = Player(
        max(players[name].balance + delta, 0),
        players[name].owned_bets
    )


def evaluate_bets(game: Game, board: Board) -> Game:
    fst, snd, *_ = get_rankings(board, None)

    for name, player in game.players.items():
        net_win = 0
        for bet_size, camel in player.owned_bets:
            if fst == camel:
                net_win += bet_size.value
            elif snd == camel:
                net_win += 1
            else:
                net_win -= 1
        change_balance(game.players, name, net_win)
    for i, field in enumerate(board.fields):
        if isinstance(field, JumpField):
            board.fields[i] = None
    return Game(
        board,
        {
            name: Player(balance, set())
            for name, (balance, _) in game.players.items()
        },
        reset_bets(),
        set(Camel)
    )


def apply_action(game: Game, action: OwnedAction) -> tuple[Game, Optional[Any]]:
    game = copy_game(game)
    owner = action.owner
    action = action.action
    if isinstance(action, Move):
        if not (owner is None and action.camel in game.camels_left):
            # award make move stipend
            change_balance(game.players, owner, 1)

        board, shifter, winner = apply_move(game.board, action)
        if shifter is not None:
            change_balance(game.players, shifter, 1)
        camels_left = game.camels_left - {action.camel}
        if camels_left:
            return Game(
                board,
                game.players,
                game.bets,
                camels_left
            ), winner
        else:
            return evaluate_bets(game, board), winner
    if isinstance(action, Place):
        game.board.fields[action.position] = JumpField(action.jump, owner)
    else:
        assert isinstance(action, Camel),\
            f'Action must be Move, Bet(Camel) or Place instead got {action}'
        game.players[owner].owned_bets.add(
            Bet(game.bets[action].pop(), action)
        )
    return game, None


if __name__ == '__main__':
    game = init_game('bob', 'joe')
    for camel in Camel:
        game, _ = apply_action(
            game, OwnedAction(None, Move(camel, 1))
        )
    game, _ = apply_action(
        game, OwnedAction('joe', Camel.White)
    )
    game, _ = apply_action(
        game, OwnedAction('joe', Camel.White)
    )
    game, _ = apply_action(
        game, OwnedAction('joe', Camel.Green)
    )
    game, _ = apply_action(
        game, OwnedAction('joe', Camel.Yellow)
    )
    for move in (
        Move(Camel.Blue, 1),
        Move(Camel.White, 3),
        Move(Camel.Yellow, 2),
        Move(Camel.Green, 2),
        Move(Camel.Orange, 1)
    ):
        action = OwnedAction('joe', move)
        game, _ = apply_action(game, action)
        print(action)
        print_game(game)
        print()
    # game, _ = apply_action(
    #     game, OwnedAction('joe', Move(Camel.White, 1))
    # )
    print_game(game)
