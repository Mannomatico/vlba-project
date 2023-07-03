import pprint
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
from queries import QUERIES
import json

app = Flask(__name__)

# SQLite DB Connection
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# BigQuery Connection
dataset_id = "vlba-maintenance-and-service.MwwMs_Data"
credentials = service_account.Credentials.from_service_account_file("credentials.json")
client = bigquery.Client(credentials=credentials)

# maps api key
with open('maps_key.json', 'r') as f:
  data = json.load(f)
maps_key = data['maps_key']

class Jobs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String(200), nullable=True)
    task_type = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.String(200), nullable=False)
    employee_id_1 = db.Column(db.String(200), nullable=True)
    employee_name_1 = db.Column(db.String(200), nullable=True)
    employee_id_2 = db.Column(db.String(200), nullable=True)
    employee_name_2 = db.Column(db.String(200), nullable=True)
    total_working_hours = db.Column(db.Double, nullable=True)


@app.route("/", methods=["GET", "POST"])
def start_page():
    # job creation
    if request.method == "POST":
        if request.form["action"] == "update":
            new_job = Jobs(
                task_type=request.form["task_type"],
                quantity=request.form["quantity"],
                client_id=request.form["client_id"],
                total_working_hours=3.3333333333
            )
            db.session.add(new_job)
            db.session.commit()

    # job deletion
    if request.method == "POST":
        if request.form["action"] == "delete":
            Jobs.query.filter(Jobs.id == request.form["id"]).delete()
            db.session.commit()

    # render map
    if request.method == "POST":
        if request.form["action"] == "map":
            return render_template(
                "map.html", location=get_location(request.form["client_id"]), maps_key = maps_key
            )

    # get all active jobs
    all_jobs = Jobs.query.order_by(Jobs.date_created).all()

    # return page
    return render_template("index.html", all_jobs=all_jobs)


# get a list of clients
def get_all_clients():
    table = client.query(QUERIES["get_all_clients"]).result()

    clients = []

    for row in table:
        clients.append(
            {
                "client_id": row.ClientId,
                "client_name": row.ClientName,
                "location": row.Location,
            }
        )
    return clients


# returns a location of a client_id in Format: 'POSTCODE,CITY,DE'
def get_location(client_id):
    clients = get_all_clients()
    return next(item for item in clients if item["client_id"] == client_id)["location"]


# returns the best team and expected total working hours of a specific task, client_id and quantity
def predict_best_team(task_type, client_id, quantity):
    table = client.query(QUERIES["predict_best_team"]).result()

    teams = []

    for row in table:
        teams.append(
            {
                "client_id": row.ClientId,
                "client_name": row.ClientName,
                "location": row.Location,
            }
        )
    return clients


# returns the team members of a team_id
def get_team_members(team_id):
    return 0


if __name__ == "__main__":
    app.run(debug=True)
