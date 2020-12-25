import json
import requests
import os

import time


def num2pos(num):
    return int(num / 3), int(num % 3)


def verify_team(teamid, token):
    url = f"https://seonline.littlefisher.me/api/group/{teamid}/verifytoken/"

    payload = {"token": token}
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    return json.loads(response.content).get('success') is True  # None, False -> False


def verify_problem_data(data):
    if data is None:
        return None
    letter = data.get('letter')
    exclude = data.get('exclude')
    challenge = data.get('challenge')
    swap = data.get('swap')
    step = data.get('step')
    _challenge = []
    if letter is None or exclude is None or challenge is None or swap is None or step is None:
        return None
    for i in range(len(challenge)):
        for j in range(len(challenge[i])):
            if challenge[i][j] == exclude:
                return None
            _challenge.append(challenge[i][j] - 1)
    if letter in [filename[0] for filename in os.listdir('./pictures')] \
            and 1 <= exclude <= 9 \
            and len(set(_challenge)) == len(_challenge) \
            and len(_challenge) == 9 and all([-1 <= _challenge[i] < 9 for i in range(9)]) \
            and len(swap) == 2 and 1 <= swap[0] <= 9 and 1 <= swap[1] <= 9 \
            and 0 <= step <= 20:
        img_path = ""
        for filename in os.listdir('./pictures'):
            if filename.startswith(letter):
                img_path = './pictures/' + filename
        return json.dumps({
            'letter': letter,
            'exclude': exclude,
            'challenge': challenge,
            'swap': swap,
            'step': step,
            'img_path': img_path
        })
    return None


def verify_hrd(hrd):
    positions = [hrd[i][j] for i in range(3) for j in range(3) if hrd[i][j] != -1]
    cnt = 0
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            if positions[i] > positions[j]:
                cnt += 1
    return cnt % 2 == 0


def verify_answer(problem, answer):
    try:
        # problem
        swap_step = problem['challenge_data']['step']
        swap = problem['challenge_data']['swap']
        position = problem['position']
        correct_answer = problem['answer']

        # answer
        flash = answer.get('swap')
        operations = answer.get('operations')

        # verify
        zx, zy = 0, 0
        for i in range(len(position)):
            if position[i] == -1:
                zx, zy = num2pos(i)
                break
        hrd = [position[0:3], position[3:6], position[6:9]]
        move_action = {'w': [-1, 0], 's': [1, 0], 'a': [0, -1], 'd': [0, 1]}
        operations += " "
        for i in range(len(operations)):
            if i == swap_step:  # 强制交换
                x1, y1 = num2pos(swap[0] - 1)
                x2, y2 = num2pos(swap[1] - 1)
                if (x1, y1) == (zx, zy):
                    (zx, zy) = (x2, y2)
                elif (x2, y2) == (zx, zy):
                    (zx, zy) = (x1, y1)
                hrd[x1][y1], hrd[x2][y2] = hrd[x2][y2], hrd[x1][y1]
                if not verify_hrd(hrd) and flash is not None and len(flash) == 2:  # 无解后闪现
                    x1, y1 = num2pos(flash[0] - 1)
                    x2, y2 = num2pos(flash[1] - 1)
                    if (x1, y1) == (zx, zy):
                        (zx, zy) = (x2, y2)
                    elif (x2, y2) == (zx, zy):
                        (zx, zy) = (x1, y1)
                    hrd[x1][y1], hrd[x2][y2] = hrd[x2][y2], hrd[x1][y1]
                # 交换完特判下是否达到目标
                if all([x == y for x, y in zip([hrd[a][b] for a in range(3) for b in range(3)], correct_answer)]):
                    return {
                        'score': True,
                        'time': time.time() - problem['time'],
                        'answer': problem['image_name']
                    }
            move = str(operations[i])
            if move in move_action.keys():  # 防止其他KeyError
                nx, ny = zx + move_action[move][0], zy + move_action[move][1]
                if 0 <= nx <= 2 and 0 <= ny <= 2:
                    hrd[zx][zy], hrd[nx][ny] = hrd[nx][ny], hrd[zx][zy]
                    zx, zy = nx, ny
                else:
                    return {
                        'score': False,
                        'time': time.time() - problem['time'],
                        'answer': problem['image_name']
                    }
            # 每一步都判断下是否达到目标
            if all([x == y for x, y in
                    zip([hrd[a][b] for a in range(3) for b in range(3)], correct_answer)]):
                return {
                    'score': True,
                    'time': time.time() - problem['time'],
                    'answer': problem['image_name']
                }
        result_position = [hrd[i][j] for i in range(3) for j in range(3)]
        return {
            'score': all([x == y for x, y in zip(result_position, correct_answer)]),
            'time': time.time() - problem['time'],
            'answer': problem['image_name']
        }
    except Exception as e:
        return {
            "error": e.args,
            "post_message": answer
        }


def verify_submit(data, answer):
    # problem
    swap = data['swap']
    swap_step = data['step']
    exclude = data['exclude']
    hrd = data['challenge']
    position = []
    for i in range(len(hrd)):
        for j in range(len(hrd[i])):
            hrd[i][j] -= 1
            position.append(hrd[i][j])
    correct_answer = [i for i in range(9)]
    correct_answer[exclude - 1] = -1

    # answer
    flash = answer.get('swap')
    operations = answer.get('operations')

    # verify
    zx, zy = 0, 0
    for i in range(len(position)):
        if position[i] == -1:
            zx, zy = num2pos(i)
            break
    move_action = {'w': [-1, 0], 's': [1, 0], 'a': [0, -1], 'd': [0, 1]}
    operations += " "
    for i in range(len(operations)):
        if i == swap_step:  # 强制交换
            x1, y1 = num2pos(swap[0] - 1)
            x2, y2 = num2pos(swap[1] - 1)
            if (x1, y1) == (zx, zy):
                (zx, zy) = (x2, y2)
            elif (x2, y2) == (zx, zy):
                (zx, zy) = (x1, y1)
            hrd[x1][y1], hrd[x2][y2] = hrd[x2][y2], hrd[x1][y1]
            if not verify_hrd(hrd) and flash is not None and len(flash) == 2:  # 无解后闪现
                x1, y1 = num2pos(flash[0] - 1)
                x2, y2 = num2pos(flash[1] - 1)
                if (x1, y1) == (zx, zy):
                    (zx, zy) = (x2, y2)
                elif (x2, y2) == (zx, zy):
                    (zx, zy) = (x1, y1)
                hrd[x1][y1], hrd[x2][y2] = hrd[x2][y2], hrd[x1][y1]
            # 交换完特判下是否达到目标
            if all([x == y for x, y in
                    zip([hrd[a][b] for a in range(3) for b in range(3)], correct_answer)]):
                return i
        move = str(operations[i])
        if move in move_action.keys():  # 防止其他KeyError
            nx, ny = zx + move_action[move][0], zy + move_action[move][1]
            if 0 <= nx <= 2 and 0 <= ny <= 2:
                hrd[zx][zy], hrd[nx][ny] = hrd[nx][ny], hrd[zx][zy]
                zx, zy = nx, ny
            else:
                return -1
        # 每一步都判断一下
        if all([x == y for x, y in
                zip([hrd[a][b] for a in range(3) for b in range(3)], correct_answer)]):
            break
    operations = operations[:len(operations) - 1]
    result_position = [hrd[i][j] for i in range(3) for j in range(3)]
    return len(operations) if all([x == y for x, y in zip(result_position, correct_answer)]) else -1


if __name__ == '__main__':
    _problem = {
        'challenge_data': {
            "swap": [7, 6], "step": 18
        },
        "position": [
            8,
            7,
            1,
            5,
            0,
            -1,
            4,
            3,
            2
        ],
        "answer": [
            0,
            1,
            2,
            3,
            4,
            5,
            -1,
            7,
            8
        ],
        'time': 0,
        'image_name': 'g'
    }
    _answer = {
        'swap': [1, 9],
        'operations': 'asawddsawwdssawdwsd'

    }
    print(verify_answer(_problem, _answer))
    # verify_team(5, "312")
    # _problem = {"letter": "z", "exclude": 9, "challenge": [[3, 7, 5], [8, 1, 6], [4, 2, 0]], "swap": [6, 9], "step": 20,
    #             "img_path": "./pictures/z_ (2).jpg"}
    # _answer = {"operations": "wwaasddwasdsawwassdds", "swap": [2, 8]}
    # print(verify_submit(_problem, _answer))
