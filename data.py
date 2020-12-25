import numpy
import cv2
import base64
import uuid
import random
import os
import time

SPLIT_V = 3
SPLIT_H = 3


def load_game_image(filename):
    image = cv2.imread(filename)
    image_slice = []
    for i in range(SPLIT_V):
        for j in range(SPLIT_H):
            image_slice.append(
                numpy.vsplit(numpy.hsplit(image, SPLIT_H)[j], SPLIT_V)[i]
            )
    return image_slice


def concat_image_slice(image_slices):
    slice_list_v = []
    for i in range(SPLIT_V):
        slice_list_h = []
        for j in range(SPLIT_H):
            slice_list_h.append(
                image_slices[j + SPLIT_H * i]
            )
        slice_list_v.append(
            numpy.concatenate(slice_list_h, axis=1)
        )

    image = numpy.concatenate(slice_list_v, axis=0)

    return image


def generate_challenge_image(image_slices):
    size1, size2 = len(image_slices[0]), len(image_slices[0][0])
    white_slice = numpy.ones((size1, size2, 3), numpy.uint8) * 255

    new_image_slice_ref = [i for i in range(len(image_slices))]
    random.shuffle(new_image_slice_ref)
    random_image_slices = [image_slices[i] for i in new_image_slice_ref]
    white_image_id = random.randint(0, len(image_slices) - 1)
    random_image_slices[white_image_id] = white_slice
    white_id = new_image_slice_ref[white_image_id]
    new_image_slice_ref[white_image_id] = -1
    image = concat_image_slice(random_image_slices)

    return image, new_image_slice_ref, white_id


def gen_data():
    pictures = './pictures/'
    image_path = random.choice(os.listdir(pictures))
    image_slices = load_game_image(pictures + image_path)
    challenge_image, refs, white_image_id = generate_challenge_image(image_slices)

    ret, encoded_img = cv2.imencode('.png', challenge_image)
    answer = [i for i in range(9)]
    answer[white_image_id] = -1

    challenge_data = {
        'uuid': uuid.uuid4().hex,
        'img': base64.b64encode(encoded_img.tobytes()).decode(),
        'swap': [random.randint(1, 9), random.randint(1, 9)],
        'step': random.randint(0, 20)
    }
    redis_data = {
        'challenge_data': challenge_data,
        'image_name': image_path[0],
        'position': refs,
        'answer': answer,
        'time': time.time()
    }
    return challenge_data, redis_data


def gen_image_data(data):
    image_path = data['img_path']
    swap = data['swap']
    step = data['step']
    exclude = data['exclude']
    challenge = data['challenge']

    image_slices = load_game_image(image_path)
    size1, size2 = len(image_slices[0]), len(image_slices[0][0])
    white_slice = numpy.ones((size1, size2, 3), numpy.uint8) * 255
    new_image_slices = [image_slices[challenge[i][j]-1] if challenge[i][j] > 0 else white_slice
                        for i in range(len(challenge))
                        for j in range(len(challenge[i]))]
    # new_image_slices[exclude - 1] = white_slice
    challenge_image = concat_image_slice(new_image_slices)
    ret, encoded_img = cv2.imencode('.png', challenge_image)
    return {
        'img': base64.b64encode(encoded_img.tobytes()).decode(),
        'swap': swap,
        'step': step
    }


if __name__ == '__main__':
    image_slices = load_game_image('./pictures/a_.jpg')
    challenge_image, refs, white_image_id = generate_challenge_image(image_slices)

    ret, encoded_img = cv2.imencode('.png', challenge_image)

    challenge_data = {
        'img': {
            'position': refs,
            'data': base64.b64encode(encoded_img.tobytes()).decode()
        }

    }

    print()
    # print(challenge_data)
    # open('data.json', 'w').write(
    #     json.dumps(challenge_data)
    # )
