from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from Environment import *
import redis
from flask_migrate import Migrate
from data import gen_data, gen_image_data
from models import *
from verify import *
from utils import *
from flask_apscheduler import APScheduler


class Config(object):
    SECRET_KEY = os.urandom(24)
    BASEPATH = os.getcwd().replace('\\', r'\\')
    # 格式为mysql+pymysql://数据库用户名:密码@数据库地址:端口号/数据库的名字?数据库格式
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_name}'

    # 忽视警告
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def get_rank_data():
    with app.app_context():
        team_list = Team.query.all()
        data = {}
        for team in team_list:
            data[str(team.id)] = team.total_score
        rank_data = RankData(json.dumps(data))
        db.session.add(rank_data)
        db.session.commit()


class SchedulerConfig(object):
    JOBS = [
        {
            'id': 'get_rank_data_job',  # 任务id
            'func': get_rank_data,  # 任务执行程序
            'args': None,  # 执行程序参数
            'trigger': 'interval',  # 任务执行类型，定时器
            'seconds': 3600,  # 任务执行时间，单位秒
        }
    ]


app = Flask(__name__)
app.config.from_object(Config)
# 定时任务模块
app.config.from_object(SchedulerConfig)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# 数据库模块
db.init_app(app)
migrate = Migrate(app, db)
r = redis.Redis(host=redis_host, port=redis_port, password=redis_pass,
                decode_responses=True)

limiter = Limiter(
    app,
    key_func=get_remote_address,
)


@app.route('/api/problem', methods=['get'])
@limiter.limit("2000/day;30/minute;1/second", override_defaults=False)
def get_data():
    stuid = request.args.get('stuid')
    if stuid is None:
        return jsonify({'error': '学号不能为空'})
    challenge_data, redis_data = gen_data()
    data_id = challenge_data['uuid']
    redis_data['stuid'] = stuid
    r.set(data_id, json.dumps(redis_data), ex=3600)
    return jsonify(challenge_data)


@app.route('/api/answer', methods=['post'])
@limiter.limit("2000/day;30/minute;1/second", override_defaults=False)
def post_answer():
    problem_id = request.json.get('uuid')
    redis_data = r.get(problem_id)
    if redis_data is None:
        return jsonify({'error': 'uuid错误或者数据已失效'})
    # r.delete(problem_id)
    problem_data = json.loads(redis_data)
    answer_data = request.json.get('answer')
    return jsonify(verify_answer(problem_data, answer_data))


@app.route('/api/challenge/create', methods=['post'])
@limiter.limit("20/day;1/second")
def create_problem():
    # 验证身份
    teamid = request.json.get("teamid")
    token = request.json.get("token")
    team = Team.query.filter(Team.id == teamid, Team.token == token).first()
    if team is None:
        if not verify_team(teamid, token):
            return jsonify({'error': '队伍id或者token无效，请检查~'})
        team = Team(teamid, token)
        db.session.add(team)
        db.session.commit()

    if Problem.query.filter(Problem.author == teamid, Problem.create_at == date.today()).count() > 0:
        return jsonify({'error': '今日已经创建过题目，请检查~'})
    data = verify_problem_data(request.json.get("data"))
    if data is None:
        return jsonify({'error': '题目数据有问题，请检查~'})
    problem = Problem(teamid, data)
    db.session.add(problem)
    db.session.commit()
    return jsonify({
        "success": True,
        "message": "创建成功~",
        "uuid": problem.uuid
    })


@app.route('/api/challenge/list', methods=['get'])
@limiter.limit("2000/day;1/second")
def get_challenge_list():
    # problems = Problem.query.filter(Problem.create_at == date.today()).all()
    problems = Problem.query.filter().all()
    data = [problem.to_dict() for problem in problems]
    return jsonify(data)


@app.route('/api/challenge/record/<string:challenge_uuid>', methods=['get'])
@limiter.limit("2000/day;1/second")
def get_challenge_record(challenge_uuid):
    records = Record.query.filter(Record.problem_uuid == challenge_uuid, Record.status == 1).order_by(Record.step,
                                                                                                      Record.timeelapsed).all()
    for i in range(len(records)):
        records[i].rank = i + 1
    db.session.commit()
    data = [record.to_dict() for record in records]
    return jsonify(data)


@app.route('/api/challenge/start/<string:challenge_uuid>', methods=['post'])
def start_challenge(challenge_uuid):
    # 验证身份
    teamid = request.json.get("teamid")
    token = request.json.get("token")
    team = Team.query.filter(Team.id == teamid, Team.token == token).first()
    if team is None:
        return jsonify({'error': '队伍id或者token无效，请检查~'})

    if Problem.query.filter(Problem.author == team.id, Problem.create_at == date.today()).first() is None:
        return jsonify({'error': '你还没出题哦，请检查~'})
    chanceLeft = 60 - Record.query.filter(Record.owner == teamid, Record.create_at == date.today()).count() - 1
    if chanceLeft < 0:
        return jsonify({'error': '今日挑战机会已用完，请检查~'})
    problem = Problem.query.filter(Problem.uuid == challenge_uuid).first()
    if problem is None:
        return jsonify({'error': "uuid无效，请检查~"})
    if problem.create_at != date.today():
        return jsonify({'error': '这不是今天的题目哦~'})
    if problem.author == team.id:
        return jsonify({'error': '不可以挑战自己出的题哦~'})
    if r.exists(problem.uuid):
        data = json.loads(r.get(problem.uuid))
    else:
        expire = expire_date()
        data = {"success": True, 'data': gen_image_data(json.loads(problem.data))}
        r.set(problem.uuid, json.dumps(data), ex=expire)
    record = Record(problem.id, problem.uuid, teamid)
    data['chanceleft'] = chanceLeft
    data['uuid'] = record.uuid
    data['expire'] = expire_date()
    problem.challengers += 1
    db.session.add(record)
    db.session.commit()
    return jsonify(data)


@app.route('/api/challenge/submit', methods=['post'])
def submit_challenge():
    now = datetime.now()
    # 验证身份
    teamid = request.json.get("teamid")
    token = request.json.get("token")
    team = Team.query.filter(Team.id == teamid, Team.token == token).first()
    if team is None:
        if not verify_team(teamid, token):
            return jsonify({'error': '队伍id或者token无效，请检查~'})
        team = Team(teamid, token)
        db.session.add(team)
        db.session.commit()

    record = Record.query.filter(Record.create_at == date.today(), Record.owner == teamid,
                                 Record.uuid == request.json.get('uuid')).first()
    if record is None:
        return jsonify({'error': '未找到此题的记录，请检查uuid是否错误~'})
    if record.status != -1:
        return jsonify({'error': '此题已经回答完毕，请检查~'})
    problem = Problem.query.filter(Problem.uuid == record.problem_uuid).first()
    answer = request.json.get('answer')
    record.answer = json.dumps(answer)  # 备份答案
    record.submit_at = now
    record.timeelapsed = (now.timestamp() - record.start_at.timestamp()) * 1000  # ms

    # 验证答案
    ret = verify_submit(json.loads(problem.data), answer)
    if ret == -1:  # 未通过
        record.status = 0
        data = {'success': False}
    else:
        record.status = 1
        record.step = ret
        problem.records += 1
        # 计算排名和得分
        records = Record.query.filter(Record.problem_id == problem.id,
                                      Record.status == 1) \
            .order_by(Record.step, Record.timeelapsed).all()
        teams_list = []
        real_rank = 1
        for i in range(len(records)):
            records[i].rank = i + 1
            if records[i].owner in teams_list:  # 过滤掉多次答同一道题目的
                continue
            teams_list.append(records[i].owner)
            # 开始更新得分
            team = Team.query.filter(Team.id == records[i].owner).first()
            key = str(records[i].problem_id)
            score = json.loads(team.score)
            score[key] = rank2score(real_rank)
            team.score = json.dumps(score)
            team.total_score = sum(score.values())
            real_rank += 1
        data = {'success': True}
    db.session.commit()
    record = Record.query.filter(Record.id == record.id).first()
    data.update(record.to_dict())
    return jsonify(data)


@app.route('/api/teamdetail/<string:team_id>', methods=['get'])
@limiter.limit("2000/day;2/second")
def get_team_detail(team_id):
    team = Team.query.filter(Team.id == team_id).first()
    if team is None:
        return jsonify({'error': '你还没开始参与哦，先去试试创建题目把~'})
    records = Record.query.filter(Record.owner == team.id).all()
    team.rank = Team.query.filter(Team.total_score > team.total_score).count() + 1
    db.session.commit()
    return jsonify(team.to_dict(records))


@app.route('/api/team/problem/<string:team_id>', methods=['get'])
@limiter.limit("2000/day")
def get_team_problem(team_id):
    team = Team.query.filter(Team.id == team_id).first()
    if team is None:
        return jsonify({'error': '你还没开始参与哦，先去试试创建题目把~'})
    solved_problem_list = [record.problem_id for record in
                           Record.query.filter(Record.owner == team.id,
                                               Record.create_at == date.today(),
                                               Record.status == 1).all()]

    problems = Problem.query.filter(Problem.create_at == date.today(),
                                    Problem.id.notin_(solved_problem_list),
                                    Problem.author != team_id).all()

    return jsonify([problem.to_dict() for problem in problems])


@app.route('/api/rank', methods=['get'])
@limiter.limit("2000/day;1/second")
def get_rank():
    teams = Team.query.order_by(Team.total_score.desc()).all()
    data = []
    for i in range(len(teams)):
        teams[i].rank = i + 1
        data.append({
            "rank": teams[i].rank,
            "teamid": teams[i].id,
            "score": teams[i].total_score,
        })
    db.session.commit()
    return jsonify(data)


@app.route('/rank', methods=['get'])
@limiter.limit("2000/day;1/second")
def view_rank():
    if r.exists("rank_data"):
        redis_data = json.loads(r.get("rank_data"))
        data_list = redis_data["data_list"]
        date_list = redis_data["date_list"]
        team_list = redis_data["legend"]
    else:
        team_list = [str(team.id) for team in Team.query.with_entities(Team.id).all()]
        date_list = []
        data_dict = {}
        for team in team_list:
            data_dict[team] = []
        for rank_data in RankData.query.all():
            date_list.append(rank_data.create_at.strftime("%d-%H:00"))
            data = json.loads(rank_data.data)
            for team in team_list:
                data_dict[team].append(data.get(team) or 0)
        data_list = [
            {
                'name': team,
                'type': 'line',
                'data': data_dict[team]
            }
            for team in team_list
        ]
        r.set("rank_data", json.dumps({"data_list": data_list, "date_list": date_list, "legend": team_list}), ex=3600)
    return render_template('rank.html', date=date_list, datas=data_list,
                           legend=team_list)


if __name__ == '__main__':
    app.run(host=app_host, port=app_port, debug=debug_model)
