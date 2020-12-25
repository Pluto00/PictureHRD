from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import uuid
import json

db = SQLAlchemy()


class Problem(db.Model):
    __tablename__ = 'problem'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_at = db.Column(db.Date, default=date.today)

    submit_at = db.Column(db.DateTime, default=datetime.now)
    uuid = db.Column(db.String(128), nullable=False)
    data = db.Column(db.String(256), nullable=False)
    author = db.Column(db.Integer, nullable=False)

    challengers = db.Column(db.Integer, default=0)
    records = db.Column(db.Integer, default=0)

    def __init__(self, author, data):
        self.author = author
        self.data = data
        self.uuid = uuid.uuid4().__str__()

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "challengercount": self.challengers,
            "pubtimestamp": self.submit_at.timestamp(),
            "author": self.author,
            "records": self.records
        }

    def get_data(self):
        return self.data


class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_at = db.Column(db.Date, default=date.today)

    start_at = db.Column(db.DateTime)  # 开始时间
    submit_at = db.Column(db.DateTime)  # 提交时间
    problem_id = db.Column(db.Integer, nullable=False)
    problem_uuid = db.Column(db.String(128), nullable=False)
    owner = db.Column(db.Integer, nullable=False)
    uuid = db.Column(db.String(128), nullable=False)

    status = db.Column(db.Integer, default=-1)  # -1 未答题, 0 未通过, 1 通过
    answer = db.Column(db.String(256))
    rank = db.Column(db.Integer, default=-1)
    step = db.Column(db.Integer, default=-1)
    timeelapsed = db.Column(db.Integer, default=0)

    def __init__(self, problem_id, problem_uuid, owner):
        self.problem_id = problem_id
        self.problem_uuid = problem_uuid
        self.owner = owner
        self.start_at = datetime.now()
        self.uuid = uuid.uuid4().__str__()

    def to_dict(self):
        return {
            "rank": self.rank,
            "owner": self.owner,
            "step": self.step,
            "timeelapsed": self.timeelapsed
        }


class Team(db.Model):
    __tablename__ = "team"
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    token = db.Column(db.String(128), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer, default=1)
    score = db.Column(db.Text)

    def __init__(self, teamid, token):
        self.id = teamid
        self.token = token
        self.score = json.dumps({})

    def to_dict(self, records=None):
        if records is None:
            records = Record.query.filter(Record.owner == self.id).all()
        success = []
        fail = []
        unsolved = []
        for record in records:
            if record.status == 1:
                success.append({
                    "problemid": record.problem_id,
                    "challengeid": record.uuid,
                    "rank": record.rank
                })
            elif record.status == 0:
                fail.append({
                    "problemid": record.problem_id,
                    "challengeid": record.uuid,
                })
            else:
                unsolved.append({
                    "problemid": record.problem_id,
                    "challengeid": record.uuid,
                })
        return {
            "rank": self.rank,
            "score": self.total_score,
            "success": success,
            "fail": fail,
            "unsolved": unsolved
        }


class RankData(db.Model):
    __tablenam__ = "rankdata"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    create_at = db.Column(db.DateTime, default=datetime.now)
    data = db.Column(db.Text)

    def __init__(self, data):
        self.data = data
