from datetime import datetime, timedelta


def expire_date():
    """
    :return: 返回距离今天23:59:59还有多少秒
    """
    # 获取当前时间
    now = datetime.now()
    # 获取今天零点
    zeroToday = now - timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,
                                microseconds=now.microsecond)
    # 获取23:59:59
    lastToday = zeroToday + timedelta(hours=23, minutes=59, seconds=59)

    return (lastToday - now).seconds


def rank2score(rank):
    if rank == 1:
        return 10
    elif rank == 2:
        return 8
    elif rank == 3:
        return 6
    elif 4 <= rank <= 10:
        return 4
    elif 11 <= rank <= 20:
        return 2
    else:
        return 1
